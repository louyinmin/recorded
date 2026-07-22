"""Persistence, tenant isolation, and validation for the Court Deck API."""

import base64
import hashlib
import hmac
import json
import mimetypes
import os
import shutil
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
ASSET_SPECS = {
    'home': [
        ('broadcast-home-v6', 'images/broadcast-home-v6.png'),
        ('broadcast-arena-bg', 'images/broadcast-arena-bg.jpg'),
    ],
    'screen-shells': [
        ('battle-shell-v9', 'images/battle-shell-v9.jpg'),
        ('season-summary-leaderboard-v1', 'images/season-summary-leaderboard-v1.jpg'),
        ('leaderboard-shell-v1', 'images/leaderboard-shell-v1.jpg'),
        ('season-hub-shell-v1', 'images/season-hub-shell-v1.jpg'),
        ('playoff-hub-shell-v1', 'images/playoff-hub-shell-v1.jpg'),
        ('broadcast-position', 'images/broadcast-position.jpg'),
        ('broadcast-build-v2', 'images/broadcast-build-v2.jpg'),
        ('broadcast-reveal-v2', 'images/broadcast-reveal-v2.jpg'),
        ('broadcast-profile', 'images/broadcast-profile.jpg'),
        ('broadcast-hub', 'images/broadcast-hub.jpg'),
    ],
    'screen-modals': [
        ('season-modal-manual-v1', 'images/season-modal-manual-v1.jpg'),
        ('season-modal-standings-v1', 'images/season-modal-standings-v1.jpg'),
        ('season-modal-stats-v1', 'images/season-modal-stats-v1.jpg'),
    ],
    'player-art': [
        ('my-core-star-card-anime-v1', 'images/my-core-star-card-anime-v1.jpg'),
        ('battle-die-body-v2', 'images/battle-die-body-v2.png'),
    ],
    'headshot-sprites': [('players-{}'.format(i), 'subpackages/headshots/images/players-{}.png'.format(i)) for i in range(15)],
}


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


def image_dimensions(path):
    with open(path, 'rb') as handle:
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


def copy_asset_atomically(source_path, destination_path):
    temporary_path = destination_path.with_name(
        '{}.{}.tmp'.format(destination_path.name, uuid.uuid4().hex)
    )
    try:
        shutil.copyfile(source_path, temporary_path)
        os.replace(temporary_path, destination_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def restore_published_group(conn, app_id, version, group, specs, source_root, published_root):
    """Restore missing or corrupted files only from bytes matching the immutable DB digest."""
    rows = {
        row['asset_key']: row
        for row in conn.execute(
            '''SELECT * FROM nbagame_asset_files
               WHERE application_id=? AND version=? AND asset_group=?''',
            (app_id, version, group),
        )
    }
    if set(rows) != {asset_key for asset_key, _ in specs}:
        raise RuntimeError('published nbagame manifest is incomplete: {}'.format(group))
    for asset_key, relative_path in specs:
        row = rows[asset_key]
        source_path = (source_root / relative_path).resolve()
        destination_path = (published_root / row['storage_path']).resolve()
        if source_root not in source_path.parents or published_root not in destination_path.parents:
            raise RuntimeError('invalid nbagame asset path: {}'.format(asset_key))
        if destination_path.is_file() and hashlib.sha256(destination_path.read_bytes()).hexdigest() == row['sha256']:
            continue
        if not source_path.is_file() or hashlib.sha256(source_path.read_bytes()).hexdigest() != row['sha256']:
            raise RuntimeError('cannot restore immutable nbagame asset: {}'.format(asset_key))
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        copy_asset_atomically(source_path, destination_path)


def publish_local_assets(app):
    """Publish a fixed runtime whitelist; published versions are never overwritten."""
    with app.app_context():
        conn = connect_db(app.config['NBAGAME_DB_PATH'])
        try:
            app_id, version = configured_app_id(), app.config['NBAGAME_ASSET_MANIFEST_VERSION']
            ensure_application(conn, app_id)
            root = Path(app.config['NBAGAME_ASSETS_DIR']).resolve()
            published_root = Path(app.config['NBAGAME_PUBLISHED_ASSETS_DIR']).resolve()
            for group, specs in ASSET_SPECS.items():
                if conn.execute('SELECT 1 FROM nbagame_asset_manifests WHERE application_id=? AND asset_group=? AND version=?', (app_id, group, version)).fetchone():
                    restore_published_group(conn, app_id, version, group, specs, root, published_root)
                    continue
                entries = []
                for asset_key, relative_path in specs:
                    file_path = (root / relative_path).resolve()
                    if root not in file_path.parents or not file_path.is_file():
                        raise RuntimeError('missing required nbagame asset: {}'.format(relative_path))
                    digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
                    extension = file_path.suffix.lower().lstrip('.')
                    width, height = image_dimensions(file_path)
                    published_path = published_root / app_id / version / group / '{}.{}'.format(asset_key, extension)
                    published_path.parent.mkdir(parents=True, exist_ok=True)
                    if published_path.exists():
                        published_digest = hashlib.sha256(published_path.read_bytes()).hexdigest()
                        if published_digest != digest:
                            raise RuntimeError('published nbagame asset version is immutable: {}'.format(asset_key))
                    else:
                        copy_asset_atomically(file_path, published_path)
                    storage_path = str(published_path.relative_to(published_root))
                    entries.append((asset_key, extension, storage_path, digest, mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream', file_path.stat().st_size, width, height))
                etag = '"assets-{}-{}-{}-{}"'.format(app_id, version, group, hashlib.sha256(''.join(item[3] for item in entries).encode()).hexdigest()[:16])
                conn.execute('INSERT INTO nbagame_asset_manifests (application_id, asset_group, version, etag, published_at) VALUES (?, ?, ?, ?, ?)', (app_id, group, version, etag, iso()))
                for entry in entries:
                    conn.execute('''INSERT INTO nbagame_asset_files
                        (application_id, version, asset_group, asset_key, extension, storage_path, sha256, content_type, bytes, width, height)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (app_id, version, group) + entry)
            conn.commit()
        finally:
            conn.close()
