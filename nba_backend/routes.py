"""Flask routes for NBA player data."""

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from .service import (
    get_nba_db,
    get_player,
    list_filter_options,
    list_missing_avatars,
    list_missing_images,
    list_players,
    nba_sync_token,
    row_to_player,
    sync_all_players,
    sync_player_avatars,
    sync_player_images,
    sync_single_player,
)


nba_bp = Blueprint('nba', __name__, url_prefix='/api/nba')


def parse_json():
    return request.get_json(silent=True) or {}


def int_arg(name, default, minimum=0, maximum=None):
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        value = default
    value = max(minimum, value)
    if maximum is not None:
        value = min(value, maximum)
    return value


def require_sync_token(payload):
    expected = nba_sync_token()
    if not expected:
        return None
    provided = (
        request.headers.get('X-NBA-Sync-Token')
        or request.args.get('token')
        or payload.get('token')
        or ''
    )
    if provided != expected:
        return jsonify({'error': 'NBA sync token is invalid'}), 403
    return None


@nba_bp.route('/players', methods=['GET'])
def players():
    conn = get_nba_db()
    total, items = list_players(
        conn,
        query=str(request.args.get('q', '')).strip(),
        team_tid=str(request.args.get('teamTid') or request.args.get('team_tid') or '').strip(),
        team=str(request.args.get('team') or request.args.get('teamName') or request.args.get('team_name') or '').strip(),
        position=str(request.args.get('position') or '').strip(),
        limit=int_arg('limit', 50, minimum=1, maximum=200),
        offset=int_arg('offset', 0, minimum=0),
    )
    return jsonify({'items': items, 'total': total})


@nba_bp.route('/players/search', methods=['GET'])
def search_players():
    query = str(request.args.get('q') or request.args.get('keyword') or request.args.get('name') or '').strip()
    if not query:
        return jsonify({'items': [], 'total': 0})
    total, items = list_players(
        get_nba_db(),
        query=query,
        team_tid=str(request.args.get('teamTid') or request.args.get('team_tid') or '').strip(),
        team=str(request.args.get('team') or request.args.get('teamName') or request.args.get('team_name') or '').strip(),
        position=str(request.args.get('position') or '').strip(),
        limit=int_arg('limit', 20, minimum=1, maximum=50),
        offset=int_arg('offset', 0, minimum=0),
        name_only=True,
    )
    return jsonify({'items': items, 'total': total})


@nba_bp.route('/filters', methods=['GET'])
def filters():
    return jsonify(list_filter_options(get_nba_db()))


@nba_bp.route('/players/<pid>', methods=['GET'])
def player_detail(pid):
    item = get_player(get_nba_db(), pid)
    if not item:
        return jsonify({'error': '球员不存在'}), 404
    return jsonify(item)


@nba_bp.route('/images/missing', methods=['GET'])
def missing_images():
    return jsonify({'items': list_missing_images(get_nba_db())})


@nba_bp.route('/images/<path:filename>', methods=['GET'])
def player_image(filename):
    return send_from_directory(current_app.config['NBA_IMAGE_DIR'], filename)


@nba_bp.route('/avatars/missing', methods=['GET'])
def missing_avatars():
    return jsonify({'items': list_missing_avatars(get_nba_db())})


@nba_bp.route('/avatars/<path:filename>', methods=['GET'])
def player_avatar(filename):
    return send_from_directory(current_app.config['NBA_AVATAR_DIR'], filename)


@nba_bp.route('/sync/player', methods=['POST'])
def sync_player():
    payload = parse_json()
    error = require_sync_token(payload)
    if error:
        return error
    pid = str(payload.get('pid') or request.args.get('pid') or '').strip()
    if not pid:
        return jsonify({'error': '缺少球员 pid'}), 400
    try:
        player = sync_single_player(get_nba_db(), pid)
    except Exception as exc:
        return jsonify({'error': '新浪 NBA 球员采集失败', 'detail': str(exc)}), 502
    return jsonify({'ok': True, 'player': row_to_player(player)})


@nba_bp.route('/sync/images', methods=['POST'])
def sync_images():
    payload = parse_json()
    error = require_sync_token(payload)
    if error:
        return error
    result = sync_player_images(
        get_nba_db(),
        current_app.config['NBA_IMAGE_DIR'],
    )
    return jsonify({'ok': True, 'result': result})


@nba_bp.route('/sync/avatars', methods=['POST'])
def sync_avatars():
    payload = parse_json()
    error = require_sync_token(payload)
    if error:
        return error
    result = sync_player_avatars(
        get_nba_db(),
        current_app.config['NBA_AVATAR_DIR'],
    )
    return jsonify({'ok': True, 'result': result})


@nba_bp.route('/sync', methods=['POST'])
def sync_all():
    payload = parse_json()
    error = require_sync_token(payload)
    if error:
        return error
    conn = get_nba_db()
    try:
        result = sync_all_players(
            conn,
            limit_teams=payload.get('limitTeams') or payload.get('limit_teams'),
            limit_players=payload.get('limitPlayers') or payload.get('limit_players'),
            concurrency=payload.get('concurrency') or 8,
            season=payload.get('season'),
        )
    except Exception as exc:
        return jsonify({'error': '新浪 NBA 批量采集失败', 'detail': str(exc)}), 502
    return jsonify({'ok': True, 'result': result})
