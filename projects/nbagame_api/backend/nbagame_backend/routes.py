"""HTTP routes for the isolated Court Deck WeChat mini-game."""

import base64
import binascii
import functools
import hashlib
import ipaddress
import json
from pathlib import Path
import sqlite3
import uuid
from datetime import datetime

from flask import Blueprint, current_app, g, jsonify, make_response, request, send_file
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from .service import (
    MAX_SNAPSHOT_BYTES, TOKEN_TTL_SECONDS, VALID_TEAMS, ValidationError, app_is_active,
    consume_rate_limit, create_access_token, find_or_create_user, get_nbagame_db, get_user,
    idempotent_response, iso, save_idempotent_response, validate_snapshot, verify_access_token,
)

nbagame_bp = Blueprint('nbagame', __name__, url_prefix='/nbagame/v1')


@nbagame_bp.before_request
def validate_write_request():
    if request.method not in {'POST', 'PUT', 'PATCH'}:
        return None
    request.max_content_length = current_app.config['NBAGAME_MAX_REQUEST_BYTES']
    if request.content_length and request.content_length > request.max_content_length:
        return failure('PAYLOAD_TOO_LARGE', 'request body exceeds the configured limit', 413)
    if not request.is_json:
        return failure('UNSUPPORTED_MEDIA_TYPE', 'Content-Type must be application/json', 415)
    try:
        body = request.get_json(silent=False)
    except BadRequest:
        return failure('VALIDATION_ERROR', 'request body must contain valid JSON', 400)
    if not isinstance(body, dict):
        return failure('VALIDATION_ERROR', 'request body must be a JSON object', 400)
    g.nbagame_payload = body
    return None


@nbagame_bp.errorhandler(RequestEntityTooLarge)
def request_too_large(error):
    return failure('PAYLOAD_TOO_LARGE', 'request body exceeds the configured limit', 413)


def request_id():
    return 'req_' + uuid.uuid4().hex[:16]


def success(data, status=200):
    return jsonify({'requestId': request_id(), 'data': data}), status


def failure(code, message, status, details=None):
    return jsonify({'requestId': request_id(), 'error': {'code': code, 'message': message, 'details': details or {}}}), status


def payload():
    return getattr(g, 'nbagame_payload', {})


def client_ip_address():
    remote_address = str(request.remote_addr or '')
    if remote_address in {'127.0.0.1', '::1'}:
        forwarded_address = str(request.headers.get('X-Real-IP') or '').strip()
        try:
            return str(ipaddress.ip_address(forwarded_address))
        except ValueError:
            pass
    try:
        return str(ipaddress.ip_address(remote_address))
    except ValueError:
        return 'unknown'


def require_public_app():
    app_id = str(request.headers.get('X-App-Id') or '').strip()
    if not app_id or not app_is_active(app_id):
        return None, failure('APP_FORBIDDEN', 'application is unavailable', 403)
    return app_id, None


def require_auth(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        raw = request.headers.get('Authorization', '')
        claims = verify_access_token(raw[7:] if raw.startswith('Bearer ') else '')
        if not claims:
            return failure('UNAUTHORIZED', 'access token is invalid or expired', 401)
        user = get_user(get_nbagame_db(), claims['app_id'], claims['sub'])
        if not user:
            return failure('UNAUTHORIZED', 'user session is unavailable', 401)
        g.nbagame_app_id, g.nbagame_user = claims['app_id'], user
        return view(*args, **kwargs)
    return wrapped


def require_idempotency_key():
    key = str(request.headers.get('Idempotency-Key') or '').strip()
    try:
        normalized_key = str(uuid.UUID(key))
    except ValueError:
        return None, failure('VALIDATION_ERROR', 'Idempotency-Key must be a UUID', 400)
    return normalized_key, None


def public_user(user, is_new=False):
    return {'id': user['id'], 'nickname': user['nickname'], 'avatarUrl': user['avatar_url'], 'isNew': bool(is_new)}


def exchange_wechat_code(appid, secret, code):
    """Keep code2Session and identity storage independent from NBA/Timing."""
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    url = 'https://api.weixin.qq.com/sns/jscode2session?' + urlencode({
        'appid': appid, 'secret': secret, 'js_code': code, 'grant_type': 'authorization_code',
    })
    try:
        with urlopen(Request(url, headers={'User-Agent': 'court-deck/1.0'}), timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
    except Exception as exc:
        raise RuntimeError('wechat upstream unavailable') from exc
    if result.get('errcode') or not result.get('openid'):
        raise ValidationError('wechat code is invalid')
    return result


@nbagame_bp.route('/auth/wechat/login', methods=['POST'])
def wechat_login():
    app_id, error = require_public_app()
    if error:
        return error
    is_allowed, retry_after = consume_rate_limit(
        get_nbagame_db(),
        app_id,
        'wechat-login:' + client_ip_address(),
        current_app.config['NBAGAME_LOGIN_RATE_LIMIT'],
        current_app.config['NBAGAME_LOGIN_RATE_WINDOW_SECONDS'],
    )
    if not is_allowed:
        response, status = failure('RATE_LIMITED', 'too many login attempts', 429)
        response.headers['Retry-After'] = str(retry_after)
        return response, status
    code = str(payload().get('code') or '').strip()
    if not code:
        return failure('VALIDATION_ERROR', 'code is required', 400)
    appid = current_app.config['NBAGAME_WECHAT_APPID']
    secret = current_app.config['NBAGAME_WECHAT_SECRET']
    if not appid or not secret or not current_app.config['NBAGAME_TOKEN_SECRET']:
        return failure('SERVICE_UNAVAILABLE', 'nbagame credentials are not configured', 503)
    try:
        session = exchange_wechat_code(appid, secret, code)
        user, is_new = find_or_create_user(get_nbagame_db(), app_id, str(session['openid']))
        token = create_access_token(user['id'], app_id, user['openid_hash'])
    except ValidationError:
        return failure('UNAUTHORIZED', 'wechat code exchange failed', 401)
    except RuntimeError:
        return failure('SERVICE_UNAVAILABLE', 'wechat service is unavailable', 503)
    return success({'accessToken': token, 'expiresIn': TOKEN_TTL_SECONDS, 'user': public_user(user, is_new)})


@nbagame_bp.route('/bootstrap', methods=['GET'])
@require_auth
def bootstrap():
    conn, user = get_nbagame_db(), g.nbagame_user
    career = conn.execute('SELECT revision, updated_at FROM nbagame_careers WHERE application_id=? AND user_id=?',
                          (g.nbagame_app_id, user['id'])).fetchone()
    response, status = success({
        'profile': public_user(user),
        'career': {'exists': bool(career), 'revision': career['revision'] if career else 0, 'updatedAt': career['updated_at'] if career else None},
        'assets': {'manifestVersion': current_app.config['NBAGAME_ASSET_MANIFEST_VERSION']},
    })
    response.headers['Cache-Control'] = 'private, no-store'
    return response, status


@nbagame_bp.route('/profile', methods=['PUT'])
@require_auth
def sync_profile():
    key, error = require_idempotency_key()
    if error:
        return error
    conn, user = get_nbagame_db(), g.nbagame_user
    saved = idempotent_response(conn, g.nbagame_app_id, user['id'], request.path, key)
    if saved:
        return success(saved)
    body = payload()
    nickname, avatar_url = body.get('nickname'), body.get('avatarUrl')
    if nickname is not None and (not isinstance(nickname, str) or len(nickname.strip()) > 64):
        return failure('VALIDATION_ERROR', 'nickname must be at most 64 characters', 400)
    if avatar_url is not None and (not isinstance(avatar_url, str) or len(avatar_url) > 2048 or (avatar_url and not avatar_url.startswith('https://'))):
        return failure('VALIDATION_ERROR', 'avatarUrl must be an https URL', 400)
    conn.execute('BEGIN IMMEDIATE')
    saved = idempotent_response(conn, g.nbagame_app_id, user['id'], request.path, key)
    if saved:
        conn.rollback()
        return success(saved)
    current_user = get_user(conn, g.nbagame_app_id, user['id'])
    conn.execute('''UPDATE nbagame_application_users SET nickname=?, avatar_url=?, updated_at=?
                    WHERE id=? AND application_id=?''',
                 (nickname.strip() if isinstance(nickname, str) else current_user['nickname'], avatar_url if avatar_url is not None else current_user['avatar_url'], iso(), user['id'], g.nbagame_app_id))
    data = {'user': public_user(get_user(conn, g.nbagame_app_id, user['id']))}
    save_idempotent_response(conn, g.nbagame_app_id, user['id'], request.path, key, data)
    conn.commit()
    return success(data)


def asset_payload(row):
    public_base_url = current_app.config['NBAGAME_PUBLIC_BASE_URL']
    return {
        'key': row['asset_key'],
        'url': '{}/nbagame/v1/assets/files/{}/{}.{}'.format(public_base_url, row['version'], row['asset_key'], row['extension']),
        'contentType': row['content_type'], 'bytes': row['bytes'], 'sha256': row['sha256'],
        'width': row['width'], 'height': row['height'], 'version': row['version'],
    }


@nbagame_bp.route('/assets/manifest', methods=['GET'])
def asset_manifest():
    app_id, error = require_public_app()
    if error:
        return error
    group, conn = str(request.args.get('group') or '').strip(), get_nbagame_db()
    version = current_app.config['NBAGAME_ASSET_MANIFEST_VERSION']
    if not current_app.config['NBAGAME_PUBLIC_BASE_URL'].startswith('https://'):
        return failure('SERVICE_UNAVAILABLE', 'nbagame public base URL is not configured', 503)
    groups = [group] if group else [row['asset_group'] for row in conn.execute(
        'SELECT asset_group FROM nbagame_asset_manifests WHERE application_id=? AND version=? ORDER BY asset_group', (app_id, version)
    )]
    manifests = []
    for item_group in groups:
        manifest = conn.execute('''SELECT * FROM nbagame_asset_manifests
                                   WHERE application_id=? AND asset_group=? AND version=?''', (app_id, item_group, version)).fetchone()
        if not manifest:
            return failure('ASSET_NOT_FOUND', 'asset group was not found', 404)
        manifests.append(manifest)
    etag = manifests[0]['etag'] if group else '"assets-all-{}"'.format(hashlib.sha256(''.join(row['etag'] for row in manifests).encode()).hexdigest()[:16])
    if request.headers.get('If-None-Match') == etag:
        response = make_response('', 304)
    else:
        assets = []
        for item_group in groups:
            rows = conn.execute('''SELECT * FROM nbagame_asset_files
                                   WHERE application_id=? AND version=? AND asset_group=? ORDER BY asset_key''', (app_id, version, item_group))
            assets.extend(asset_payload(row) for row in rows)
        response, _ = success({'appId': app_id, 'group': group or None, 'manifestVersion': version, 'assets': assets})
    response.headers['Cache-Control'] = 'public, max-age=300, stale-while-revalidate=60'
    response.headers['ETag'] = etag
    response.headers['Vary'] = 'X-App-Id'
    return response


@nbagame_bp.route('/assets/files/<version>/<asset_key>.<extension>', methods=['GET'])
def asset_file(version, asset_key, extension):
    app_id, error = require_public_app()
    if error:
        return error
    row = get_nbagame_db().execute('''SELECT * FROM nbagame_asset_files
        WHERE application_id=? AND version=? AND asset_key=? AND extension=?''',
        (app_id, version, asset_key, extension.lower())).fetchone()
    if not row:
        return failure('ASSET_NOT_FOUND', 'asset was not found', 404)
    published_root = Path(current_app.config['NBAGAME_PUBLISHED_ASSETS_DIR']).resolve()
    path = (published_root / row['storage_path']).resolve()
    if published_root not in path.parents or not path.is_file():
        return failure('ASSET_NOT_FOUND', 'asset was not found', 404)
    response = make_response(send_file(path, mimetype=row['content_type'], conditional=True))
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    response.headers['ETag'] = '"{}"'.format(row['sha256'])
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Vary'] = 'X-App-Id'
    return response


@nbagame_bp.route('/career', methods=['GET'])
@require_auth
def read_career():
    row = get_nbagame_db().execute('SELECT * FROM nbagame_careers WHERE application_id=? AND user_id=?',
                                   (g.nbagame_app_id, g.nbagame_user['id'])).fetchone()
    data = {'revision': row['revision'], 'updatedAt': row['updated_at'], 'snapshot': json.loads(row['snapshot_json'])} if row else {'revision': 0, 'updatedAt': None, 'snapshot': None}
    response, status = success(data)
    response.headers['Cache-Control'] = 'private, no-store'
    return response, status


def career_conflict(row):
    current = {'revision': row['revision'], 'updatedAt': row['updated_at'], 'snapshot': json.loads(row['snapshot_json'])} if row else {'revision': 0, 'updatedAt': None, 'snapshot': None}
    return failure('CAREER_CONFLICT', 'career revision does not match', 409, current)


def career_write_result(row):
    return {
        'revision': row['revision'],
        'etag': 'career-{}'.format(row['revision']),
        'updatedAt': row['updated_at'],
    }


@nbagame_bp.route('/career', methods=['PUT'])
@require_auth
def write_career():
    key, error = require_idempotency_key()
    if error:
        return error
    if request.content_length and request.content_length > MAX_SNAPSHOT_BYTES:
        return failure('VALIDATION_ERROR', 'snapshot exceeds 2 MB', 400)
    conn, user, body = get_nbagame_db(), g.nbagame_user, payload()
    saved = idempotent_response(conn, g.nbagame_app_id, user['id'], request.path, key)
    if saved:
        return success(saved)
    try:
        snapshot = validate_snapshot(body)
    except ValidationError as exc:
        return failure('VALIDATION_ERROR', str(exc), 400)
    snapshot_document = {'schemaVersion': body['schemaVersion'], 'state': snapshot}
    snapshot_json = json.dumps(snapshot_document, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    snapshot_sha256 = hashlib.sha256(snapshot_json.encode()).hexdigest()
    season, progression, now = snapshot['season'], snapshot['progression'], iso()
    try:
        conn.execute('BEGIN IMMEDIATE')
        saved = idempotent_response(conn, g.nbagame_app_id, user['id'], request.path, key)
        if saved:
            conn.rollback()
            return success(saved)
        row = conn.execute(
            'SELECT * FROM nbagame_careers WHERE application_id=? AND user_id=?',
            (g.nbagame_app_id, user['id']),
        ).fetchone()
        if row:
            existing_sha256 = row['snapshot_sha256'] or hashlib.sha256(
                json.dumps(json.loads(row['snapshot_json']), ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode()
            ).hexdigest()
            if existing_sha256 == snapshot_sha256:
                data = career_write_result(row)
                save_idempotent_response(conn, g.nbagame_app_id, user['id'], request.path, key, data)
                conn.commit()
                return success(data)
            if body['clientRevision'] <= row['client_revision']:
                conn.rollback()
                return career_conflict(row)
        expected_revision = row['revision'] if row else 0
        if request.headers.get('If-Match') != '"career-{}"'.format(expected_revision):
            conn.rollback()
            return career_conflict(row)
        revision = expected_revision + 1
        values = (
            revision, snapshot_json, body['clientRevision'], snapshot_sha256,
            progression['seasonNumber'], snapshot['careerTeam'], snapshot['phase'],
            season['wins'], season['losses'], int(bool(season.get('isChampion'))),
            season.get('playoffResult'), now,
        )
        if row:
            updated = conn.execute(
                '''UPDATE nbagame_careers SET
                   revision=?, snapshot_json=?, client_revision=?, snapshot_sha256=?, season_number=?,
                   career_team=?, phase=?, wins=?, losses=?, is_champion=?, playoff_result=?, updated_at=?
                   WHERE application_id=? AND user_id=? AND revision=?''',
                values + (g.nbagame_app_id, user['id'], expected_revision),
            ).rowcount
            if updated != 1:
                current = conn.execute(
                    'SELECT * FROM nbagame_careers WHERE application_id=? AND user_id=?',
                    (g.nbagame_app_id, user['id']),
                ).fetchone()
                conn.rollback()
                return career_conflict(current)
        else:
            conn.execute(
                '''INSERT INTO nbagame_careers
                   (application_id, user_id, revision, snapshot_json, client_revision, snapshot_sha256,
                    season_number, career_team, phase, wins, losses, is_champion, playoff_result, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (g.nbagame_app_id, user['id']) + values,
            )
        data = {'revision': revision, 'etag': 'career-{}'.format(revision), 'updatedAt': now}
        save_idempotent_response(conn, g.nbagame_app_id, user['id'], request.path, key, data)
        conn.commit()
        return success(data)
    except sqlite3.IntegrityError:
        conn.rollback()
        current = conn.execute(
            'SELECT * FROM nbagame_careers WHERE application_id=? AND user_id=?',
            (g.nbagame_app_id, user['id']),
        ).fetchone()
        return career_conflict(current)


@nbagame_bp.route('/career', methods=['DELETE'])
@require_auth
def delete_career():
    key, error = require_idempotency_key()
    if error:
        return error
    conn, user = get_nbagame_db(), g.nbagame_user
    saved = idempotent_response(conn, g.nbagame_app_id, user['id'], request.path, key)
    if saved:
        return success(saved)
    conn.execute('BEGIN IMMEDIATE')
    saved = idempotent_response(conn, g.nbagame_app_id, user['id'], request.path, key)
    if saved:
        conn.rollback()
        return success(saved)
    row = conn.execute('SELECT * FROM nbagame_careers WHERE application_id=? AND user_id=?', (g.nbagame_app_id, user['id'])).fetchone()
    if request.headers.get('If-Match') != '"career-{}"'.format(row['revision'] if row else 0):
        conn.rollback()
        return career_conflict(row)
    conn.execute('DELETE FROM nbagame_careers WHERE application_id=? AND user_id=?', (g.nbagame_app_id, user['id']))
    data = {'deleted': bool(row), 'revision': 0}
    save_idempotent_response(conn, g.nbagame_app_id, user['id'], request.path, key, data)
    conn.commit()
    return success(data)


@nbagame_bp.route('/leaderboards/season-starts/events', methods=['POST'])
@require_auth
def create_season_start():
    key, error = require_idempotency_key()
    if error:
        return error
    conn, user, body = get_nbagame_db(), g.nbagame_user, payload()
    saved = idempotent_response(conn, g.nbagame_app_id, user['id'], request.path, key)
    if saved:
        return success(saved)
    event_id, team, season_number = str(body.get('eventId') or '').strip(), body.get('team'), body.get('seasonNumber')
    try:
        is_valid_event_id = str(uuid.UUID(event_id)) == event_id.lower()
    except ValueError:
        is_valid_event_id = False
    if not is_valid_event_id or team not in VALID_TEAMS or not isinstance(season_number, int) or season_number < 1:
        return failure('VALIDATION_ERROR', 'invalid season start event', 400)
    occurred_at = str(body.get('occurredAt') or '').strip() or iso()
    try:
        parsed_occurred_at = datetime.fromisoformat(occurred_at.replace('Z', '+00:00'))
        if not occurred_at.endswith('Z') or parsed_occurred_at.utcoffset().total_seconds() != 0:
            raise ValueError
    except ValueError:
        return failure('VALIDATION_ERROR', 'occurredAt must be ISO 8601 UTC', 400)
    try:
        conn.execute('BEGIN IMMEDIATE')
        saved = idempotent_response(conn, g.nbagame_app_id, user['id'], request.path, key)
        if saved:
            conn.rollback()
            return success(saved)
        existing_event = conn.execute(
            '''SELECT result_json FROM nbagame_season_start_events
               WHERE application_id=? AND user_id=? AND event_id=?''',
            (g.nbagame_app_id, user['id'], event_id),
        ).fetchone()
        if existing_event:
            data = json.loads(existing_event['result_json'])
            save_idempotent_response(conn, g.nbagame_app_id, user['id'], request.path, key, data)
            conn.commit()
            return success(data)
        career = conn.execute(
            '''SELECT revision, season_number, career_team FROM nbagame_careers
               WHERE application_id=? AND user_id=?''',
            (g.nbagame_app_id, user['id']),
        ).fetchone()
        if not career or career['season_number'] != season_number or career['career_team'] != team:
            conn.rollback()
            return failure(
                'CAREER_CONFLICT',
                'season start event does not match the current career',
                409,
                {'revision': career['revision'] if career else 0},
            )
        career_event = conn.execute(
            '''SELECT result_json FROM nbagame_season_start_events
               WHERE application_id=? AND user_id=? AND career_revision=?''',
            (g.nbagame_app_id, user['id'], career['revision']),
        ).fetchone()
        if career_event:
            data = json.loads(career_event['result_json'])
            save_idempotent_response(conn, g.nbagame_app_id, user['id'], request.path, key, data)
            conn.commit()
            return success(data)
        server_time = iso()
        aggregate = conn.execute(
            '''SELECT starts FROM nbagame_season_start_aggregates
               WHERE application_id=? AND user_id=? AND team=?''',
            (g.nbagame_app_id, user['id'], team),
        ).fetchone()
        starts = aggregate['starts'] + 1 if aggregate else 1
        if aggregate:
            conn.execute(
                '''UPDATE nbagame_season_start_aggregates
                   SET starts=?, first_reached_at=?, updated_at=?
                   WHERE application_id=? AND user_id=? AND team=?''',
                (starts, server_time, server_time, g.nbagame_app_id, user['id'], team),
            )
        else:
            conn.execute(
                '''INSERT INTO nbagame_season_start_aggregates
                   (application_id, user_id, team, starts, first_reached_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (g.nbagame_app_id, user['id'], team, starts, server_time, server_time),
            )
        data = {'eventId': event_id, 'team': team, 'starts': starts, 'duplicate': False}
        conn.execute(
            '''INSERT INTO nbagame_season_start_events
               (application_id, user_id, event_id, team, season_number, occurred_at, created_at,
                career_revision, result_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                g.nbagame_app_id, user['id'], event_id, team, season_number, occurred_at,
                server_time, career['revision'], json.dumps(data, ensure_ascii=False),
            ),
        )
        save_idempotent_response(conn, g.nbagame_app_id, user['id'], request.path, key, data)
        conn.commit()
        return success(data)
    except sqlite3.IntegrityError:
        conn.rollback()
        existing_event = conn.execute(
            '''SELECT result_json FROM nbagame_season_start_events
               WHERE application_id=? AND user_id=? AND (event_id=? OR career_revision=(
                   SELECT revision FROM nbagame_careers WHERE application_id=? AND user_id=?
               )) ORDER BY event_id=? DESC LIMIT 1''',
            (g.nbagame_app_id, user['id'], event_id, g.nbagame_app_id, user['id'], event_id),
        ).fetchone()
        if existing_event:
            return success(json.loads(existing_event['result_json']))
        raise


@nbagame_bp.route('/leaderboards/season-starts', methods=['GET'])
@require_auth
def season_starts_leaderboard():
    scope = str(request.args.get('scope') or 'global')
    try:
        limit = min(max(int(request.args.get('limit', 20)), 1), 50)
    except ValueError:
        return failure('VALIDATION_ERROR', 'limit must be an integer', 400)
    if scope not in {'personal', 'friends', 'global'}:
        return failure('VALIDATION_ERROR', 'scope is invalid', 400)
    cursor = str(request.args.get('cursor') or '').strip()
    try:
        offset = int(json.loads(base64.urlsafe_b64decode(cursor + '=' * (-len(cursor) % 4))).get('offset', 0)) if cursor else 0
        if offset < 0:
            raise ValueError
    except (AttributeError, ValueError, TypeError, binascii.Error, json.JSONDecodeError):
        return failure('VALIDATION_ERROR', 'cursor is invalid', 400)
    conn, user = get_nbagame_db(), g.nbagame_user
    if scope == 'friends':
        rows, available = [], False
    else:
        query = '''SELECT a.user_id, a.team, a.starts, u.nickname FROM nbagame_season_start_aggregates a
                   JOIN nbagame_application_users u ON u.id=a.user_id AND u.application_id=a.application_id
                   WHERE a.application_id=?'''
        parameters = [g.nbagame_app_id]
        if scope == 'personal':
            query += ' AND a.user_id=?'
            parameters.append(user['id'])
        rows = conn.execute(query + ' ORDER BY a.starts DESC, a.first_reached_at ASC, a.user_id ASC LIMIT ? OFFSET ?', parameters + [limit + 1, offset]).fetchall()
        available = True
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (base64.urlsafe_b64encode(json.dumps({'offset': offset + limit}, separators=(',', ':')).encode()).rstrip(b'=').decode() if has_more else None)
    data = {'scope': scope, 'friendsAvailable': available, 'rows': [
        {'rank': index, 'playerName': row['nickname'] or 'Player', 'team': row['team'], 'starts': row['starts'], 'isSelf': row['user_id'] == user['id']}
        for index, row in enumerate(rows, offset + 1)], 'nextCursor': next_cursor, 'generatedAt': iso()}
    response, status = success(data)
    response.headers['Cache-Control'] = 'private, max-age=30'
    return response, status
