"""Flask routes for NBA player data."""

from flask import Blueprint, current_app, g, jsonify, request, send_from_directory
from wechat_backend.routes import create_wechat_session_response
from wechat_backend.service import (
    NBA_APP,
    get_wechat_db,
    get_nba_user_config,
    patch_nba_user_config,
    require_wechat_project,
)

from .service import (
    MAX_BATCH_PLAYER_PIDS,
    get_nba_db,
    get_player,
    get_player_cards,
    home_cards_metadata,
    list_players_batch,
    list_filter_options,
    list_missing_avatars,
    list_missing_images,
    list_missing_team_images,
    list_players,
    nba_sync_token,
    row_to_player,
    sync_all_players,
    sync_player_avatars,
    sync_player_images,
    sync_2026_rookies,
    sync_team_images,
    sync_single_player,
)
from .salaryswish import (
    get_salaryswish_team,
    list_salaryswish_teams,
    sync_salaryswish,
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


@nba_bp.route('/wechat/session', methods=['POST'])
def create_nba_session():
    return create_wechat_session_response(NBA_APP)


@nba_bp.route('/user-config', methods=['GET'])
@require_wechat_project(NBA_APP)
def read_user_config():
    config, updated_at = get_nba_user_config(get_wechat_db(), g.wechat_user['id'])
    return jsonify({
        'app': NBA_APP,
        'config': config,
        'updatedAt': updated_at,
        'homeCards': home_cards_metadata(get_nba_db(), NBA_APP, config, updated_at),
    })


@nba_bp.route('/user-config', methods=['PATCH'])
@require_wechat_project(NBA_APP)
def update_user_config():
    payload = parse_json()
    try:
        config, updated_at = patch_nba_user_config(
            get_wechat_db(),
            g.wechat_user['id'],
            payload.get('config'),
        )
    except ValueError:
        return jsonify({'message': 'invalid nba user config'}), 400
    return jsonify({
        'app': NBA_APP,
        'config': config,
        'updatedAt': updated_at,
        'homeCards': home_cards_metadata(get_nba_db(), NBA_APP, config, updated_at),
    })


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


@nba_bp.route('/players/batch', methods=['GET'])
def players_batch():
    raw_pids = request.args.get('pids', '')
    try:
        result = list_players_batch(get_nba_db(), raw_pids)
    except ValueError:
        return jsonify({'message': 'too many pids', 'limit': MAX_BATCH_PLAYER_PIDS}), 400
    return jsonify(result)


@nba_bp.route('/filters', methods=['GET'])
def filters():
    return jsonify(list_filter_options(get_nba_db()))


@nba_bp.route('/salaryswish/teams', methods=['GET'])
def salaryswish_teams():
    return jsonify({'items': list_salaryswish_teams(get_nba_db())})


@nba_bp.route('/salaryswish/teams/<team_slug>', methods=['GET'])
def salaryswish_team_detail(team_slug):
    item = get_salaryswish_team(get_nba_db(), team_slug)
    if not item:
        return jsonify({'error': '球队薪资数据不存在'}), 404
    return jsonify(item)


@nba_bp.route('/players/<pid>', methods=['GET'])
def player_detail(pid):
    item = get_player(get_nba_db(), pid)
    if not item:
        return jsonify({'error': '球员不存在'}), 404
    return jsonify(item)


@nba_bp.route('/players/<pid>/cards', methods=['GET'])
def player_cards(pid):
    item = get_player(get_nba_db(), pid)
    if not item:
        return jsonify({'error': '球员不存在'}), 404
    cards = get_player_cards(get_nba_db(), pid)
    updated_values = [card.get('updated_at') for card in cards if card.get('updated_at')]
    return jsonify({
        'pid': pid,
        'items': cards,
        'updatedAt': max(updated_values) if updated_values else None,
    })


@nba_bp.route('/images/missing', methods=['GET'])
def missing_images():
    return jsonify({'items': list_missing_images(get_nba_db())})


@nba_bp.route('/card-images/<path:filename>', methods=['GET'])
def player_card_image(filename):
    return send_from_directory(current_app.config['NBA_IMAGE_DIR'], filename)


@nba_bp.route('/images/<path:filename>', methods=['GET'])
def player_image(filename):
    return send_from_directory(current_app.config['NBA_IMAGE_DIR'], filename)


@nba_bp.route('/avatars/missing', methods=['GET'])
def missing_avatars():
    return jsonify({'items': list_missing_avatars(get_nba_db())})


@nba_bp.route('/avatars/<path:filename>', methods=['GET'])
def player_avatar(filename):
    return send_from_directory(current_app.config['NBA_AVATAR_DIR'], filename)


@nba_bp.route('/team-images/missing', methods=['GET'])
def missing_team_images():
    return jsonify({'items': list_missing_team_images(get_nba_db())})


@nba_bp.route('/team-images/<path:filename>', methods=['GET'])
def team_image(filename):
    return send_from_directory(current_app.config['NBA_TEAM_IMAGE_DIR'], filename)


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


@nba_bp.route('/sync/team-images', methods=['POST'])
def sync_team_logos():
    payload = parse_json()
    error = require_sync_token(payload)
    if error:
        return error
    result = sync_team_images(
        get_nba_db(),
        current_app.config['NBA_TEAM_IMAGE_DIR'],
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


@nba_bp.route('/sync/rookies-2026', methods=['POST'])
def sync_rookies_2026():
    payload = parse_json()
    error = require_sync_token(payload)
    if error:
        return error
    try:
        result = sync_2026_rookies(get_nba_db())
    except Exception as exc:
        return jsonify({'error': '2026 NBA 新秀采集失败', 'detail': str(exc)}), 502
    return jsonify({'ok': True, 'result': result})


@nba_bp.route('/sync/salaryswish', methods=['POST'])
def sync_salaryswish_data():
    payload = parse_json()
    error = require_sync_token(payload)
    if error:
        return error
    team_slugs = payload.get('teamSlugs') or payload.get('team_slugs')
    if team_slugs is not None and not isinstance(team_slugs, list):
        return jsonify({'message': 'teamSlugs must be an array of team slugs'}), 400
    if team_slugs is not None and any(not isinstance(slug, str) for slug in team_slugs):
        return jsonify({'message': 'teamSlugs must contain only strings'}), 400
    if not team_slugs:
        single_slug = payload.get('teamSlug') or payload.get('team_slug') or request.args.get('teamSlug')
        if single_slug is not None and not isinstance(single_slug, str):
            return jsonify({'message': 'teamSlug must be a string'}), 400
        team_slugs = [single_slug] if single_slug else None
    try:
        result = sync_salaryswish(
            get_nba_db(),
            team_slugs=team_slugs,
            concurrency=payload.get('concurrency') or 4,
        )
    except Exception as exc:
        return jsonify({'error': 'SalarySwish 薪资采集失败', 'detail': str(exc)}), 502
    return jsonify({'ok': True, 'result': result})
