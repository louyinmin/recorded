"""Flask routes for the expiry module."""

from flask import Blueprint, current_app, g, jsonify, request

from .service import (
    DEFAULT_NOTIFY_OFFSETS,
    DEFAULT_TIMEZONE,
    RESOURCE_ACTIVE,
    RESOURCE_STOPPED,
    ROLE_ADMIN,
    ROLE_USER,
    STATUS_ACTIVE,
    STATUS_DISABLED,
    build_dashboard,
    build_stats,
    create_session,
    ensure_user_settings,
    gen_id,
    get_email_settings,
    get_email_delivery_auth,
    get_expiry_db,
    get_resource,
    get_resources,
    get_user_settings,
    hash_password,
    list_notifications,
    local_today,
    mark_notification_read,
    normalize_offsets,
    require_admin,
    require_expiry_auth,
    row_to_dict,
    update_email_settings,
    utcnow_iso,
    validate_resource_payload,
    verify_password,
)
from .reminder import send_email


expiry_bp = Blueprint('expiry', __name__, url_prefix='/api/expiry')


@expiry_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', '')).strip()
    conn = get_expiry_db()
    row = conn.execute(
        'SELECT * FROM expiry_users WHERE username=?',
        (username,),
    ).fetchone()
    if not row or row['status'] != STATUS_ACTIVE or not verify_password(password, row['password_hash']):
        return jsonify({'error': '账号或密码错误'}), 401
    token, expires_at = create_session(conn, row['id'])
    conn.execute(
        'UPDATE expiry_users SET last_login_at=? WHERE id=?',
        (utcnow_iso(), row['id']),
    )
    conn.commit()
    ensure_user_settings(conn, row['id'])
    return jsonify({
        'token': token,
        'expires_at': expires_at,
        'user': {
            'id': row['id'],
            'username': row['username'],
            'role': row['role'],
            'email': row['email'],
            'must_change_password': bool(row['must_change_password']),
        },
    })


@expiry_bp.route('/auth/logout', methods=['POST'])
@require_expiry_auth
def logout():
    conn = get_expiry_db()
    token = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
    conn.execute('DELETE FROM expiry_sessions WHERE token=?', (token,))
    conn.commit()
    return jsonify({'ok': True})


@expiry_bp.route('/auth/me', methods=['GET'])
@require_expiry_auth
def me():
    user = dict(g.expiry_user)
    user.pop('password_hash', None)
    user['must_change_password'] = bool(user.get('must_change_password'))
    return jsonify(user)


@expiry_bp.route('/auth/change-password', methods=['POST'])
@require_expiry_auth
def change_password():
    data = request.get_json(silent=True) or {}
    old_password = str(data.get('old_password', '')).strip()
    new_password = str(data.get('new_password', '')).strip()
    if len(new_password) < 6:
        return jsonify({'error': '新密码至少 6 位'}), 400
    conn = get_expiry_db()
    row = conn.execute(
        'SELECT password_hash FROM expiry_users WHERE id=?',
        (g.expiry_user['id'],),
    ).fetchone()
    if not row or not verify_password(old_password, row['password_hash']):
        return jsonify({'error': '原密码错误'}), 400
    conn.execute(
        'UPDATE expiry_users SET password_hash=?, must_change_password=0 WHERE id=?',
        (hash_password(new_password), g.expiry_user['id']),
    )
    conn.commit()
    return jsonify({'ok': True})


@expiry_bp.route('/dashboard', methods=['GET'])
@require_expiry_auth
def dashboard():
    conn = get_expiry_db()
    return jsonify(build_dashboard(conn, g.expiry_user['id']))


@expiry_bp.route('/stats', methods=['GET'])
@require_expiry_auth
def stats():
    conn = get_expiry_db()
    settings = get_user_settings(conn, g.expiry_user['id'])
    resources = get_resources(conn, g.expiry_user['id'], {'user_settings': settings, 'timezone': settings.get('timezone')})
    today = local_today(settings.get('timezone') or DEFAULT_TIMEZONE)
    try:
        year = int(request.args.get('year', today.year))
    except ValueError:
        return jsonify({'error': '年份格式无效'}), 400
    return jsonify(build_stats(resources, year, today))


@expiry_bp.route('/resources', methods=['GET'])
@require_expiry_auth
def list_resources():
    conn = get_expiry_db()
    settings = get_user_settings(conn, g.expiry_user['id'])
    filters = {
        'search': request.args.get('search', ''),
        'status': request.args.get('status', ''),
        'category': request.args.get('category', ''),
        'billing_cycle': request.args.get('billing_cycle', ''),
        'user_settings': settings,
        'timezone': settings.get('timezone'),
    }
    items = get_resources(conn, g.expiry_user['id'], filters)
    categories = sorted({item['category'] for item in items if item['category']})
    return jsonify({'items': items, 'categories': categories})


@expiry_bp.route('/resources', methods=['POST'])
@require_expiry_auth
def create_resource():
    conn = get_expiry_db()
    settings = get_user_settings(conn, g.expiry_user['id'])
    payload, error = validate_resource_payload(request.get_json(silent=True) or {}, settings)
    if error:
        return jsonify({'error': error}), 400
    now = utcnow_iso()
    resource_id = gen_id()
    conn.execute(
        '''
        INSERT INTO expiry_resources (
            id, user_id, name, provider, category, resource_type, billing_cycle,
            amount, currency, start_date, next_due_date, auto_renew, manual_status,
            notify_offsets, note, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''',
        (
            resource_id,
            g.expiry_user['id'],
            payload['name'],
            payload['provider'],
            payload['category'],
            payload['resource_type'],
            payload['billing_cycle'],
            payload['amount'],
            payload['currency'],
            payload['start_date'],
            payload['next_due_date'],
            payload['auto_renew'],
            payload['manual_status'],
            payload['notify_offsets'],
            payload['note'],
            now,
            now,
        ),
    )
    conn.commit()
    return jsonify({'id': resource_id}), 201


@expiry_bp.route('/resources/<resource_id>', methods=['GET'])
@require_expiry_auth
def resource_detail(resource_id):
    conn = get_expiry_db()
    item = get_resource(conn, g.expiry_user['id'], resource_id)
    if not item:
        return jsonify({'error': '资源不存在'}), 404
    return jsonify(item)


@expiry_bp.route('/resources/<resource_id>', methods=['PUT'])
@require_expiry_auth
def update_resource(resource_id):
    conn = get_expiry_db()
    existing = conn.execute(
        'SELECT id FROM expiry_resources WHERE id=? AND user_id=?',
        (resource_id, g.expiry_user['id']),
    ).fetchone()
    if not existing:
        return jsonify({'error': '资源不存在'}), 404
    settings = get_user_settings(conn, g.expiry_user['id'])
    payload, error = validate_resource_payload(request.get_json(silent=True) or {}, settings)
    if error:
        return jsonify({'error': error}), 400
    conn.execute(
        '''
        UPDATE expiry_resources
        SET name=?, provider=?, category=?, resource_type=?, billing_cycle=?, amount=?, currency=?,
            start_date=?, next_due_date=?, auto_renew=?, manual_status=?, notify_offsets=?, note=?, updated_at=?
        WHERE id=? AND user_id=?
        ''',
        (
            payload['name'],
            payload['provider'],
            payload['category'],
            payload['resource_type'],
            payload['billing_cycle'],
            payload['amount'],
            payload['currency'],
            payload['start_date'],
            payload['next_due_date'],
            payload['auto_renew'],
            payload['manual_status'],
            payload['notify_offsets'],
            payload['note'],
            utcnow_iso(),
            resource_id,
            g.expiry_user['id'],
        ),
    )
    conn.commit()
    return jsonify({'ok': True})


@expiry_bp.route('/resources/<resource_id>', methods=['DELETE'])
@require_expiry_auth
def delete_resource(resource_id):
    conn = get_expiry_db()
    conn.execute(
        'DELETE FROM expiry_resources WHERE id=? AND user_id=?',
        (resource_id, g.expiry_user['id']),
    )
    conn.commit()
    return jsonify({'ok': True})


@expiry_bp.route('/resources/<resource_id>/stop', methods=['POST'])
@require_expiry_auth
def stop_resource(resource_id):
    conn = get_expiry_db()
    conn.execute(
        'UPDATE expiry_resources SET manual_status=?, updated_at=? WHERE id=? AND user_id=?',
        (RESOURCE_STOPPED, utcnow_iso(), resource_id, g.expiry_user['id']),
    )
    conn.commit()
    return jsonify({'ok': True})


@expiry_bp.route('/resources/<resource_id>/resume', methods=['POST'])
@require_expiry_auth
def resume_resource(resource_id):
    conn = get_expiry_db()
    conn.execute(
        'UPDATE expiry_resources SET manual_status=?, updated_at=? WHERE id=? AND user_id=?',
        (RESOURCE_ACTIVE, utcnow_iso(), resource_id, g.expiry_user['id']),
    )
    conn.commit()
    return jsonify({'ok': True})


@expiry_bp.route('/notifications', methods=['GET'])
@require_expiry_auth
def notifications():
    conn = get_expiry_db()
    return jsonify(list_notifications(conn, g.expiry_user['id']))


@expiry_bp.route('/notifications/<notification_id>/read', methods=['POST'])
@require_expiry_auth
def read_notification(notification_id):
    conn = get_expiry_db()
    ok = mark_notification_read(conn, g.expiry_user['id'], notification_id)
    if not ok:
        return jsonify({'error': '提醒不存在'}), 404
    return jsonify({'ok': True})


@expiry_bp.route('/settings/profile', methods=['GET'])
@require_expiry_auth
def profile():
    user = dict(g.expiry_user)
    user.pop('password_hash', None)
    user['must_change_password'] = bool(user.get('must_change_password'))
    return jsonify(user)


@expiry_bp.route('/settings/profile', methods=['PUT'])
@require_expiry_auth
def update_profile():
    data = request.get_json(silent=True) or {}
    email = str(data.get('email', '')).strip()
    conn = get_expiry_db()
    conn.execute(
        'UPDATE expiry_users SET email=? WHERE id=?',
        (email, g.expiry_user['id']),
    )
    conn.commit()
    return jsonify({'ok': True})


@expiry_bp.route('/settings/email', methods=['GET'])
@require_expiry_auth
def email_settings():
    conn = get_expiry_db()
    return jsonify(get_email_settings(conn, g.expiry_user['id']))


@expiry_bp.route('/settings/email', methods=['PUT'])
@require_expiry_auth
def save_email_settings():
    conn = get_expiry_db()
    try:
        update_email_settings(
            conn,
            g.expiry_user['id'],
            request.get_json(silent=True) or {},
            current_app.config['EXPIRY_BASE_DIR'],
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'ok': True})


@expiry_bp.route('/settings/email/test', methods=['POST'])
@require_expiry_auth
def test_email():
    conn = get_expiry_db()
    user = conn.execute(
        'SELECT email FROM expiry_users WHERE id=?',
        (g.expiry_user['id'],),
    ).fetchone()
    recipient = (user['email'] if user else '') or ''
    recipient = recipient.strip()
    if not recipient:
        return jsonify({'error': '请先在账号资料中填写接收邮箱'}), 400
    email_settings = row_to_dict(
        conn.execute(
            'SELECT * FROM expiry_email_settings WHERE user_id=?',
            (g.expiry_user['id'],),
        ).fetchone()
    ) or {}
    if not email_settings.get('enabled'):
        return jsonify({'error': '请先启用邮件提醒'}), 400
    try:
        auth_payload = get_email_delivery_auth(conn, email_settings, current_app.config['EXPIRY_BASE_DIR'])
        send_email(
            email_settings,
            auth_payload.get('smtp_password', ''),
            recipient,
            '【续费雷达】测试邮件',
            '这是一封来自续费雷达的测试邮件，用于验证你的提醒发送配置。',
            auth_mode=auth_payload.get('auth_mode', 'password'),
            oauth_access_token=auth_payload.get('oauth_access_token', ''),
        )
    except Exception as exc:
        return jsonify({'error': '测试发送失败: {}'.format(exc)}), 400
    return jsonify({'ok': True, 'recipient': recipient})


@expiry_bp.route('/settings/reminders', methods=['GET'])
@require_expiry_auth
def reminder_settings():
    conn = get_expiry_db()
    return jsonify(get_user_settings(conn, g.expiry_user['id']))


@expiry_bp.route('/settings/reminders', methods=['PUT'])
@require_expiry_auth
def save_reminder_settings():
    conn = get_expiry_db()
    data = request.get_json(silent=True) or {}
    notify_offsets = normalize_offsets(data.get('default_notify_offsets', DEFAULT_NOTIFY_OFFSETS))
    timezone_name = str(data.get('timezone', DEFAULT_TIMEZONE)).strip() or DEFAULT_TIMEZONE
    try:
        local_today(timezone_name)
    except Exception:
        return jsonify({'error': '时区无效'}), 400
    conn.execute(
        '''
        UPDATE expiry_user_settings
        SET default_notify_offsets=?, timezone=?, updated_at=?
        WHERE user_id=?
        ''',
        (notify_offsets, timezone_name, utcnow_iso(), g.expiry_user['id']),
    )
    conn.commit()
    return jsonify({'ok': True})


@expiry_bp.route('/admin/users', methods=['GET'])
@require_admin
def admin_users():
    conn = get_expiry_db()
    rows = conn.execute(
        '''
        SELECT id, username, role, status, email, must_change_password, created_at, last_login_at
        FROM expiry_users
        ORDER BY created_at DESC
        '''
    ).fetchall()
    return jsonify([row_to_dict(row) for row in rows])


@expiry_bp.route('/admin/users', methods=['POST'])
@require_admin
def admin_create_user():
    data = request.get_json(silent=True) or {}
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', '')).strip()
    email = str(data.get('email', '')).strip()
    role = ROLE_ADMIN if str(data.get('role', ROLE_USER)).strip() == ROLE_ADMIN else ROLE_USER
    if not username:
        return jsonify({'error': '账号不能为空'}), 400
    if len(password) < 6:
        return jsonify({'error': '初始密码至少 6 位'}), 400
    conn = get_expiry_db()
    existing = conn.execute(
        'SELECT id FROM expiry_users WHERE username=?',
        (username,),
    ).fetchone()
    if existing:
        return jsonify({'error': '账号已存在'}), 400
    user_id = gen_id()
    now = utcnow_iso()
    conn.execute(
        '''
        INSERT INTO expiry_users (
            id, username, password_hash, role, status, email, must_change_password, created_at
        ) VALUES (?,?,?,?,?,?,?,?)
        ''',
        (user_id, username, hash_password(password), role, STATUS_ACTIVE, email, 1, now),
    )
    conn.commit()
    ensure_user_settings(conn, user_id)
    return jsonify({'id': user_id}), 201


@expiry_bp.route('/admin/users/<user_id>', methods=['PUT'])
@require_admin
def admin_update_user(user_id):
    data = request.get_json(silent=True) or {}
    email = str(data.get('email', '')).strip()
    role = ROLE_ADMIN if str(data.get('role', ROLE_USER)).strip() == ROLE_ADMIN else ROLE_USER
    conn = get_expiry_db()
    conn.execute(
        'UPDATE expiry_users SET email=?, role=? WHERE id=?',
        (email, role, user_id),
    )
    conn.commit()
    return jsonify({'ok': True})


@expiry_bp.route('/admin/users/<user_id>/reset-password', methods=['POST'])
@require_admin
def admin_reset_password(user_id):
    conn = get_expiry_db()
    row = conn.execute(
        'SELECT id FROM expiry_users WHERE id=?',
        (user_id,),
    ).fetchone()
    if not row:
        return jsonify({'error': '用户不存在'}), 404
    new_password = request.get_json(silent=True) or {}
    password = str(new_password.get('password', '')).strip()
    if not password:
        password = 'Reset@{}'.format(gen_id()[:6])
    conn.execute(
        'UPDATE expiry_users SET password_hash=?, must_change_password=1 WHERE id=?',
        (hash_password(password), user_id),
    )
    conn.commit()
    return jsonify({'ok': True, 'temporary_password': password})


@expiry_bp.route('/admin/users/<user_id>/toggle-status', methods=['POST'])
@require_admin
def admin_toggle_status(user_id):
    conn = get_expiry_db()
    row = conn.execute(
        'SELECT status FROM expiry_users WHERE id=?',
        (user_id,),
    ).fetchone()
    if not row:
        return jsonify({'error': '用户不存在'}), 404
    if user_id == g.expiry_user['id']:
        return jsonify({'error': '不能停用当前管理员账号'}), 400
    new_status = STATUS_DISABLED if row['status'] == STATUS_ACTIVE else STATUS_ACTIVE
    conn.execute(
        'UPDATE expiry_users SET status=? WHERE id=?',
        (new_status, user_id),
    )
    conn.commit()
    return jsonify({'ok': True, 'status': new_status})
