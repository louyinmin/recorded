"""Persistence, tenant isolation, and validation for the Court Deck API."""

import base64
import hashlib
import hmac
import io
import json
import mimetypes
import os
import re
import sqlite3
import struct
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from flask import current_app, g

TOKEN_TTL_SECONDS = 7200
IDEMPOTENCY_TTL_HOURS = 24
MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024
MAX_SNAPSHOT_DEPTH = 32
DEFAULT_LOGIN_RATE_LIMIT = 20
DEFAULT_LOGIN_RATE_WINDOW_SECONDS = 60
VALID_PHASES = {'menu', 'reveal', 'season', 'playin', 'playoff', 'results'}
VALID_POSITIONS = {'PG', 'SG', 'SF', 'PF', 'C'}
VALID_ATTRS = {'three', 'mid', 'pass', 'rebound', 'athletic', 'clutch'}
FORBIDDEN_IDENTITY_FIELDS = {'userId', 'user_id', 'appId', 'app_id', 'applicationId', 'application_id', 'openid'}
VALID_TEAMS = {
    'ATL', 'BOS', 'BKN', 'CHA', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW',
    'HOU', 'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NOP', 'NYK',
    'OKC', 'ORL', 'PHI', 'PHX', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS',
}
ASSET_NAME_PATTERN = re.compile(r'^[a-z0-9][a-z0-9-]*$')
AUTO_DISCOVER_EXTENSIONS = {'.jpeg': 1, '.jpg': 2, '.png': 3}


class ValidationError(ValueError):
    pass


def utcnow():
    return datetime.utcnow().replace(microsecond=0)


def iso(value=None):
    return (value or utcnow()).isoformat() + 'Z'


def connect_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def get_nbagame_db():
    if 'nbagame_db' not in g:
        g.nbagame_db = connect_db(current_app.config['NBAGAME_DB_PATH'])
    return g.nbagame_db


def close_nbagame_db(exc=None):
    db = g.pop('nbagame_db', None)
    if db:
        db.close()


def init_nbagame_db(db_path):
    conn = connect_db(db_path)
    try:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS nbagame_applications (
                app_id TEXT PRIMARY KEY, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS nbagame_application_users (
                id TEXT PRIMARY KEY, application_id TEXT NOT NULL, openid_hash TEXT NOT NULL,
                nickname TEXT, avatar_url TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_login_at TEXT NOT NULL,
                UNIQUE(application_id, openid_hash),
                FOREIGN KEY(application_id) REFERENCES nbagame_applications(app_id)
            );
            CREATE TABLE IF NOT EXISTS nbagame_careers (
                application_id TEXT NOT NULL, user_id TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0, snapshot_json TEXT NOT NULL,
                client_revision INTEGER NOT NULL DEFAULT 0, snapshot_sha256 TEXT NOT NULL DEFAULT '',
                season_number INTEGER, career_team TEXT, phase TEXT, wins INTEGER, losses INTEGER, is_champion INTEGER NOT NULL DEFAULT 0,
                playoff_result TEXT, updated_at TEXT NOT NULL, PRIMARY KEY(application_id, user_id),
                FOREIGN KEY(user_id) REFERENCES nbagame_application_users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS nbagame_idempotency_records (
                application_id TEXT NOT NULL, user_id TEXT NOT NULL, route TEXT NOT NULL, idempotency_key TEXT NOT NULL,
                response_json TEXT NOT NULL, expires_at TEXT NOT NULL, created_at TEXT NOT NULL,
                PRIMARY KEY(application_id, user_id, route, idempotency_key)
            );
            CREATE TABLE IF NOT EXISTS nbagame_season_start_events (
                application_id TEXT NOT NULL, user_id TEXT NOT NULL, event_id TEXT NOT NULL, team TEXT NOT NULL,
                season_number INTEGER NOT NULL, occurred_at TEXT NOT NULL, created_at TEXT NOT NULL,
                career_revision INTEGER, result_json TEXT NOT NULL DEFAULT '',
                PRIMARY KEY(application_id, user_id, event_id)
            );
            CREATE TABLE IF NOT EXISTS nbagame_season_start_aggregates (
                application_id TEXT NOT NULL, user_id TEXT NOT NULL, team TEXT NOT NULL, starts INTEGER NOT NULL,
                first_reached_at TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(application_id, user_id, team)
            );
            CREATE INDEX IF NOT EXISTS idx_nbagame_global_leaderboard
                ON nbagame_season_start_aggregates(application_id, starts DESC, first_reached_at, user_id);
            CREATE TABLE IF NOT EXISTS nbagame_asset_manifests (
                application_id TEXT NOT NULL, asset_group TEXT NOT NULL, version TEXT NOT NULL, etag TEXT NOT NULL,
                published_at TEXT NOT NULL, PRIMARY KEY(application_id, asset_group, version)
            );
            CREATE TABLE IF NOT EXISTS nbagame_asset_files (
                application_id TEXT NOT NULL, version TEXT NOT NULL, asset_group TEXT NOT NULL, asset_key TEXT NOT NULL,
                extension TEXT NOT NULL, storage_path TEXT NOT NULL, sha256 TEXT NOT NULL, content_type TEXT NOT NULL,
                bytes INTEGER NOT NULL, width INTEGER, height INTEGER, PRIMARY KEY(application_id, version, asset_key)
            );
            CREATE TABLE IF NOT EXISTS nbagame_asset_manifest_items (
                application_id TEXT NOT NULL, manifest_version TEXT NOT NULL, asset_group TEXT NOT NULL,
                asset_key TEXT NOT NULL, asset_version TEXT NOT NULL,
                PRIMARY KEY(application_id, manifest_version, asset_group, asset_key)
            );
            CREATE TABLE IF NOT EXISTS nbagame_rate_limits (
                application_id TEXT NOT NULL, scope_key TEXT NOT NULL, window_start INTEGER NOT NULL,
                request_count INTEGER NOT NULL, PRIMARY KEY(application_id, scope_key)
            );
        ''')
        migrate_nbagame_db(conn)
        conn.commit()
    finally:
        conn.close()


def has_column(conn, table_name, column_name):
    rows = conn.execute('PRAGMA table_info({})'.format(table_name)).fetchall()
    return any(row['name'] == column_name for row in rows)


def migrate_nbagame_db(conn):
    career_columns = {
        'client_revision': 'INTEGER NOT NULL DEFAULT 0',
        'snapshot_sha256': "TEXT NOT NULL DEFAULT ''",
    }
    event_columns = {
        'career_revision': 'INTEGER',
        'result_json': "TEXT NOT NULL DEFAULT ''",
    }
    for column_name, definition in career_columns.items():
        if not has_column(conn, 'nbagame_careers', column_name):
            conn.execute('ALTER TABLE nbagame_careers ADD COLUMN {} {}'.format(column_name, definition))
    for column_name, definition in event_columns.items():
        if not has_column(conn, 'nbagame_season_start_events', column_name):
            conn.execute('ALTER TABLE nbagame_season_start_events ADD COLUMN {} {}'.format(column_name, definition))
    conn.executescript('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_nbagame_event_career_revision
        ON nbagame_season_start_events(application_id, user_id, career_revision)
        WHERE career_revision IS NOT NULL;
        CREATE TABLE IF NOT EXISTS nbagame_rate_limits (
            application_id TEXT NOT NULL, scope_key TEXT NOT NULL, window_start INTEGER NOT NULL,
            request_count INTEGER NOT NULL, PRIMARY KEY(application_id, scope_key)
        );
        CREATE TABLE IF NOT EXISTS nbagame_asset_manifest_items (
            application_id TEXT NOT NULL, manifest_version TEXT NOT NULL, asset_group TEXT NOT NULL,
            asset_key TEXT NOT NULL, asset_version TEXT NOT NULL,
            PRIMARY KEY(application_id, manifest_version, asset_group, asset_key)
        );
    ''')


def configured_app_id():
    return current_app.config['NBAGAME_APP_ID']


def app_is_active(app_id):
    return app_id == configured_app_id() and current_app.config['NBAGAME_APP_STATUS'] == 'active'


def ensure_application(conn, app_id):
    now = iso()
    conn.execute('''INSERT INTO nbagame_applications (app_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)
                    ON CONFLICT(app_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at''',
                 (app_id, current_app.config['NBAGAME_APP_STATUS'], now, now))


def fingerprint_openid(openid):
    secret = current_app.config['NBAGAME_TOKEN_SECRET']
    if not secret:
        raise RuntimeError('NBAGAME_TOKEN_SECRET is not configured')
    return hmac.new(secret.encode(), openid.encode(), hashlib.sha256).hexdigest()


def find_or_create_user(conn, app_id, openid):
    row = conn.execute('SELECT * FROM nbagame_application_users WHERE application_id=? AND openid_hash=?',
                       (app_id, fingerprint_openid(openid))).fetchone()
    now, is_new = iso(), row is None
    if is_new:
        user_id = 'usrapp_' + uuid.uuid4().hex[:24]
        conn.execute('''INSERT INTO nbagame_application_users
                        (id, application_id, openid_hash, created_at, updated_at, last_login_at) VALUES (?, ?, ?, ?, ?, ?)''',
                     (user_id, app_id, fingerprint_openid(openid), now, now, now))
        row = conn.execute('SELECT * FROM nbagame_application_users WHERE id=? AND application_id=?', (user_id, app_id)).fetchone()
    else:
        conn.execute('UPDATE nbagame_application_users SET last_login_at=?, updated_at=? WHERE id=? AND application_id=?',
                     (now, now, row['id'], app_id))
    conn.commit()
    return dict(row), is_new


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _unb64(data):
    return base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))


def create_access_token(user_id, app_id, opaque_openid):
    secret = current_app.config['NBAGAME_TOKEN_SECRET']
    if not secret:
        raise RuntimeError('NBAGAME_TOKEN_SECRET is not configured')
    payload = {
        'sub': user_id,
        'app_id': app_id,
        # The HMAC fingerprint is stable for tenant lookup but reveals no raw openid.
        'openid': opaque_openid,
        'exp': int((utcnow() + timedelta(seconds=TOKEN_TTL_SECONDS)).timestamp()),
    }
    encoded = _b64(json.dumps(payload, separators=(',', ':'), sort_keys=True).encode())
    return encoded + '.' + _b64(hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).digest())


def verify_access_token(token):
    try:
        encoded, signature = str(token or '').split('.', 1)
        secret = current_app.config['NBAGAME_TOKEN_SECRET']
        expected = _b64(hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).digest())
        claims = json.loads(_unb64(encoded))
        if not secret or not hmac.compare_digest(signature, expected) or int(claims['exp']) <= int(utcnow().timestamp()):
            return None
        return claims if app_is_active(claims.get('app_id')) else None
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def get_user(conn, app_id, user_id):
    return conn.execute('SELECT * FROM nbagame_application_users WHERE id=? AND application_id=?', (user_id, app_id)).fetchone()


def idempotent_response(conn, app_id, user_id, route, key):
    row = conn.execute('''SELECT response_json FROM nbagame_idempotency_records
                          WHERE application_id=? AND user_id=? AND route=? AND idempotency_key=? AND expires_at>?''',
                       (app_id, user_id, route, key, iso())).fetchone()
    return json.loads(row['response_json']) if row else None


def save_idempotent_response(conn, app_id, user_id, route, key, data):
    now = utcnow()
    conn.execute('''INSERT INTO nbagame_idempotency_records
                    (application_id, user_id, route, idempotency_key, response_json, expires_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (app_id, user_id, route, key, json.dumps(data, ensure_ascii=False), iso(now + timedelta(hours=IDEMPOTENCY_TTL_HOURS)), iso(now)))


def consume_rate_limit(conn, app_id, scope_key, limit, window_seconds):
    now = int(time.time())
    window_start = now - (now % window_seconds)
    conn.execute(
        '''INSERT INTO nbagame_rate_limits (application_id, scope_key, window_start, request_count)
           VALUES (?, ?, ?, 1)
           ON CONFLICT(application_id, scope_key) DO UPDATE SET
               request_count=CASE
                   WHEN nbagame_rate_limits.window_start=excluded.window_start
                   THEN nbagame_rate_limits.request_count + 1 ELSE 1 END,
               window_start=excluded.window_start''',
        (app_id, scope_key, window_start),
    )
    row = conn.execute(
        'SELECT request_count FROM nbagame_rate_limits WHERE application_id=? AND scope_key=?',
        (app_id, scope_key),
    ).fetchone()
    conn.commit()
    return row['request_count'] <= limit, max(1, window_start + window_seconds - now)


def json_depth(value):
    if not isinstance(value, (dict, list)):
        return 0
    return 1 + max((json_depth(item) for item in (value.values() if isinstance(value, dict) else value)), default=0)


def sanitize_snapshot(value):
    if isinstance(value, dict):
        if FORBIDDEN_IDENTITY_FIELDS.intersection(value):
            raise ValidationError('identity fields are not accepted')
        return {
            key: sanitize_snapshot(item)
            for key, item in value.items()
            if key != 'rank'
        }
    if isinstance(value, list):
        return [sanitize_snapshot(item) for item in value]
    return value


def validate_snapshot(payload):
    if payload.get('schemaVersion') != 1 or not isinstance(payload.get('snapshot'), dict):
        raise ValidationError('schemaVersion must be 1 and snapshot must be an object')
    if FORBIDDEN_IDENTITY_FIELDS.intersection(payload):
        raise ValidationError('identity fields are not accepted')
    if not isinstance(payload.get('clientRevision'), int) or payload['clientRevision'] < 0:
        raise ValidationError('clientRevision must be a non-negative integer')
    snapshot = sanitize_snapshot(payload['snapshot'])
    if snapshot.get('phase') not in VALID_PHASES or snapshot.get('position') not in VALID_POSITIONS or snapshot.get('careerTeam') not in VALID_TEAMS:
        raise ValidationError('invalid career state')
    attrs = snapshot.get('attrs')
    if not isinstance(attrs, dict) or set(attrs) != VALID_ATTRS or any(not isinstance(v, int) or not 0 <= v <= 100 for v in attrs.values()):
        raise ValidationError('invalid attrs')
    progression, season = snapshot.get('progression'), snapshot.get('season')
    if not isinstance(progression, dict) or not isinstance(season, dict) or progression.get('seasonNumber') != season.get('seasonNumber') or not isinstance(season.get('seasonNumber'), int):
        raise ValidationError('season numbers must match')
    if any(not isinstance(season.get(key), int) or season[key] < 0 for key in ('wins', 'losses')) or season['wins'] + season['losses'] > 82:
        raise ValidationError('invalid regular season record')
    if snapshot.get('battle') is not None or ('processedDays' in season and not isinstance(season['processedDays'], list)):
        raise ValidationError('battle must be null and processedDays must be an array')
    encoded = json.dumps(snapshot, ensure_ascii=False, separators=(',', ':')).encode()
    if len(encoded) > MAX_SNAPSHOT_BYTES or json_depth(snapshot) > MAX_SNAPSHOT_DEPTH:
        raise ValidationError('snapshot exceeds limits')
    return snapshot


def image_dimensions(content):
    with io.BytesIO(content) as handle:
        data = handle.read(24)
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            return struct.unpack('>II', data[16:24])
        if data[:2] != b'\xff\xd8':
            return None, None
        handle.seek(2)
        while True:
            marker = handle.read(1)
            while marker == b'\xff':
                marker = handle.read(1)
            if not marker:
                return None, None
            length = handle.read(2)
            if len(length) != 2:
                return None, None
            segment_size = struct.unpack('>H', length)[0] - 2
            if 0xC0 <= marker[0] <= 0xC3:
                segment = handle.read(5)
                return struct.unpack('>HH', segment[1:5])[::-1]
            handle.seek(segment_size, 1)


def write_asset_atomically(content, destination_path):
    temporary_path = destination_path.with_name(
        '{}.{}.tmp'.format(destination_path.name, uuid.uuid4().hex)
    )
    try:
        with open(temporary_path, 'xb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, destination_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def load_asset_specs(config_path, source_root):
    def reject_duplicate_keys(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise RuntimeError('duplicate nbagame asset config key: {}'.format(key))
            value[key] = item
        return value

    try:
        with open(config_path, encoding='utf-8') as handle:
            raw_specs = json.load(handle, object_pairs_hook=reject_duplicate_keys)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            'unable to load nbagame asset config {}: {}'.format(config_path, error)
        ) from error
    if not isinstance(raw_specs, dict) or not raw_specs:
        raise RuntimeError('nbagame asset config must be a non-empty object')

    auto_discover = raw_specs.pop('autoDiscover', {
        'images': ['home', 'screen-shells', 'screen-modals', 'player-art'],
    })
    if not isinstance(auto_discover, dict):
        raise RuntimeError('nbagame autoDiscover config must be an object')

    source_root = Path(source_root).resolve()
    specs, configured_paths, configured_source_paths = {}, {}, set()
    for group, assets in raw_specs.items():
        if not isinstance(group, str) or not ASSET_NAME_PATTERN.fullmatch(group):
            raise RuntimeError('invalid nbagame asset group: {!r}'.format(group))
        if not isinstance(assets, dict) or not assets:
            raise RuntimeError('nbagame asset group must be a non-empty object: {}'.format(group))
        entries = []
        for asset_key, relative_path in assets.items():
            if not isinstance(asset_key, str) or not ASSET_NAME_PATTERN.fullmatch(asset_key):
                raise RuntimeError('invalid nbagame asset key: {!r}'.format(asset_key))
            if asset_key in configured_paths:
                raise RuntimeError('duplicate nbagame asset key: {}'.format(asset_key))
            if (
                not isinstance(relative_path, str)
                or not relative_path
                or '\\' in relative_path
                or Path(relative_path).is_absolute()
                or '..' in Path(relative_path).parts
            ):
                raise RuntimeError(
                    'invalid nbagame asset path for {}: {!r}'.format(asset_key, relative_path)
                )
            configured_paths[asset_key] = relative_path
            configured_source_paths.add((source_root / relative_path).resolve())
            entries.append((asset_key, relative_path))
        specs[group] = entries

    for relative_directory, configured_groups in auto_discover.items():
        if (
            not isinstance(relative_directory, str)
            or not relative_directory
            or '\\' in relative_directory
            or Path(relative_directory).is_absolute()
            or '..' in Path(relative_directory).parts
        ):
            raise RuntimeError(
                'invalid nbagame autoDiscover directory: {!r}'.format(relative_directory)
            )
        if isinstance(configured_groups, str):
            configured_groups = [configured_groups]
        if not isinstance(configured_groups, list) or not configured_groups:
            raise RuntimeError('nbagame autoDiscover groups must be a non-empty list')
        groups = []
        for group in configured_groups:
            if not isinstance(group, str) or not ASSET_NAME_PATTERN.fullmatch(group):
                raise RuntimeError('invalid nbagame autoDiscover group: {!r}'.format(group))
            if group not in groups:
                groups.append(group)
        directory = (source_root / relative_directory).resolve()
        if source_root not in directory.parents or not directory.is_dir():
            raise RuntimeError(
                'missing nbagame autoDiscover directory: {}'.format(relative_directory)
            )

        discovered = {}
        for source_path in sorted(directory.iterdir()):
            extension = source_path.suffix.lower()
            if not source_path.is_file() or extension not in AUTO_DISCOVER_EXTENSIONS:
                continue
            asset_key = source_path.stem
            if not ASSET_NAME_PATTERN.fullmatch(asset_key):
                continue
            if asset_key in configured_paths or source_path.resolve() in configured_source_paths:
                continue
            previous = discovered.get(asset_key)
            if (
                previous is None
                or AUTO_DISCOVER_EXTENSIONS[extension]
                > AUTO_DISCOVER_EXTENSIONS[previous.suffix.lower()]
            ):
                discovered[asset_key] = source_path
        discovered_entries = [
            (asset_key, source_path.relative_to(source_root).as_posix())
            for asset_key, source_path in sorted(discovered.items())
        ]
        for group in groups:
            specs.setdefault(group, []).extend(discovered_entries)
        configured_paths.update(discovered_entries)
    if not specs:
        raise RuntimeError('nbagame asset config did not produce any assets')
    return specs


def snapshot_local_assets(source_root, asset_specs):
    """Read one consistent source snapshot before publishing any database state."""
    groups, manifest_items, seen_keys, asset_cache = {}, [], {}, {}
    for group, specs in sorted(asset_specs.items()):
        entries = []
        for asset_key, relative_path in sorted(specs):
            if asset_key in seen_keys and seen_keys[asset_key] != relative_path:
                raise RuntimeError('duplicate nbagame asset key: {}'.format(asset_key))
            seen_keys[asset_key] = relative_path
            source_path = (source_root / relative_path).resolve()
            if source_root not in source_path.parents or not source_path.is_file():
                raise RuntimeError('missing required nbagame asset: {}'.format(relative_path))
            cache_key = (asset_key, relative_path)
            entry = asset_cache.get(cache_key)
            if entry is None:
                content = source_path.read_bytes()
                digest = hashlib.sha256(content).hexdigest()
                extension = source_path.suffix.lower().lstrip('.')
                asset_version = 'asset-' + hashlib.sha256(
                    extension.encode() + b'\0' + content
                ).hexdigest()
                width, height = image_dimensions(content)
                entry = {
                    'asset_key': asset_key,
                    'asset_version': asset_version,
                    'content': content,
                    'content_type': mimetypes.guess_type(str(source_path))[0] or 'application/octet-stream',
                    'digest': digest,
                    'extension': extension,
                    'height': height,
                    'width': width,
                }
                asset_cache[cache_key] = entry
            entries.append(entry)
            manifest_items.append({
                'assetGroup': group,
                'assetKey': asset_key,
                'assetVersion': entry['asset_version'],
                'extension': entry['extension'],
            })
        groups[group] = entries
    manifest_digest = hashlib.sha256(json.dumps(
        manifest_items, separators=(',', ':'), sort_keys=True,
    ).encode()).hexdigest()
    return 'content-' + manifest_digest, groups


def ensure_content_asset(conn, app_id, group, entry, published_root):
    asset_key, asset_version = entry['asset_key'], entry['asset_version']
    published_path = (
        published_root / app_id / 'objects' / asset_version /
        '{}.{}'.format(asset_key, entry['extension'])
    ).resolve()
    if published_root not in published_path.parents:
        raise RuntimeError('invalid nbagame published asset path: {}'.format(asset_key))
    published_path.parent.mkdir(parents=True, exist_ok=True)
    if not published_path.is_file() or hashlib.sha256(published_path.read_bytes()).hexdigest() != entry['digest']:
        write_asset_atomically(entry['content'], published_path)
    storage_path = str(published_path.relative_to(published_root))
    existing = conn.execute(
        '''SELECT * FROM nbagame_asset_files
           WHERE application_id=? AND version=? AND asset_key=?''',
        (app_id, asset_version, asset_key),
    ).fetchone()
    expected = (
        entry['extension'], storage_path, entry['digest'], entry['content_type'],
        len(entry['content']), entry['width'], entry['height'],
    )
    if existing:
        actual = (
            existing['extension'], existing['storage_path'], existing['sha256'],
            existing['content_type'], existing['bytes'], existing['width'], existing['height'],
        )
        if actual != expected:
            raise RuntimeError('content-addressed nbagame asset metadata differs: {}'.format(asset_key))
        return
    conn.execute(
        '''INSERT INTO nbagame_asset_files
           (application_id, version, asset_group, asset_key, extension, storage_path,
            sha256, content_type, bytes, width, height)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (app_id, asset_version, group, asset_key) + expected,
    )


def publish_local_assets(app):
    """Publish immutable assets using versions derived only from source content."""
    with app.app_context():
        root = Path(app.config['NBAGAME_ASSETS_DIR']).resolve()
        published_root = Path(app.config['NBAGAME_PUBLISHED_ASSETS_DIR']).resolve()
        asset_specs = load_asset_specs(app.config['NBAGAME_ASSET_SPECS_FILE'], root)
        version, groups = snapshot_local_assets(root, asset_specs)
        conn = connect_db(app.config['NBAGAME_DB_PATH'])
        try:
            app_id = configured_app_id()
            conn.execute('BEGIN IMMEDIATE')
            ensure_application(conn, app_id)
            for group, entries in groups.items():
                etag = '"assets-{}-{}-{}"'.format(app_id, version, group)
                conn.execute(
                    '''INSERT OR IGNORE INTO nbagame_asset_manifests
                       (application_id, asset_group, version, etag, published_at)
                       VALUES (?, ?, ?, ?, ?)''',
                    (app_id, group, version, etag, iso()),
                )
                for entry in entries:
                    ensure_content_asset(conn, app_id, group, entry, published_root)
                    conn.execute(
                        '''INSERT OR IGNORE INTO nbagame_asset_manifest_items
                           (application_id, manifest_version, asset_group, asset_key, asset_version)
                           VALUES (?, ?, ?, ?, ?)''',
                        (app_id, version, group, entry['asset_key'], entry['asset_version']),
                    )
            conn.commit()
            app.config['NBAGAME_ASSET_MANIFEST_VERSION'] = version
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
