"""Flask routes for WeChat Mini Program session exchange."""

from flask import Blueprint, current_app, jsonify, request

from .service import (
    WeChatCodeExchangeError,
    WeChatUpstreamError,
    create_session,
    exchange_wechat_code,
    find_or_create_user,
    get_wechat_db,
    user_session_payload,
)


wechat_bp = Blueprint('wechat', __name__, url_prefix='/api/wechat')


def parse_json():
    return request.get_json(silent=True) or {}


def create_wechat_session_response(app_name=''):
    payload = parse_json()
    code = str(payload.get('code') or '').strip()
    if not code:
        return jsonify({'message': 'code is required'}), 400
    app_name = str(app_name or payload.get('app') or '').strip()

    appid = str(current_app.config.get('WECHAT_MINIPROGRAM_APPID') or '').strip()
    secret = str(current_app.config.get('WECHAT_MINIPROGRAM_SECRET') or '').strip()
    if not appid or not secret:
        return jsonify({'message': 'wechat credentials are not configured'}), 500

    try:
        session = exchange_wechat_code(appid, secret, code)
    except WeChatCodeExchangeError as exc:
        return jsonify({
            'message': 'wechat code2Session failed',
            'errcode': exc.errcode,
        }), 401
    except WeChatUpstreamError:
        return jsonify({'message': 'wechat code2Session upstream error'}), 502

    user = find_or_create_user(
        get_wechat_db(),
        str(session.get('openid') or ''),
        str(session.get('unionid') or ''),
    )
    session_token, expires_at = create_session(get_wechat_db(), user['id'], app_name)
    return jsonify(user_session_payload(user, app_name, session_token, expires_at))


@wechat_bp.route('/session', methods=['POST'])
def create_generic_session():
    return create_wechat_session_response()
