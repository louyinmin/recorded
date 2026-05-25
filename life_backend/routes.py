"""Flask routes for life backend."""

import os
import secrets
from datetime import timedelta

from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.utils import secure_filename

from .security import hash_password, verify_password
from .service import (
    MODULE_TABLES,
    ROLE_ADMIN,
    ROLE_USER,
    STATUS_ACTIVE,
    STATUS_DELETED,
    STATUS_INACTIVE,
    add_months,
    bootstrap_payload,
    create_session,
    delete_module_record,
    ensure_unique_username,
    ensure_upload_dir,
    find_account_row,
    gen_id,
    get_life_db,
    normalize_account_payload,
    normalize_account_identifier,
    normalize_mock_mode,
    replace_module_records,
    request_is_mock,
    require_life_admin,
    require_life_auth,
    set_storage_value,
    get_storage_snapshot,
    today_iso,
    upsert_module_record,
    user_public_dict,
)


life_bp = Blueprint('life_backend', __name__, url_prefix='/api/life')

ALLOWED_IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif'}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def parse_json():
    return request.get_json(silent=True) or {}


def module_from_path(module):
    if module not in MODULE_TABLES:
        return None, jsonify({'error': '不支持的模块'}), 404
    return module, None, None


@life_bp.route('/auth/register', methods=['POST'])
def register():
    payload, error = normalize_account_payload(parse_json())
    if error:
        return jsonify({'error': error}), 400
    conn = get_life_db()
    if find_account_row(conn, payload['email']):
        return jsonify({'error': '这个账号已经注册'}), 400
    now = today_iso()
    user_id = gen_id()
    username = ensure_unique_username(conn, payload['username'])
    lifecycle = [
        {'label': '创建账号', 'date': now, 'status': 'done'},
        {'label': '完善资料', 'date': now, 'status': 'active'},
        {'label': '启用安全设置', 'date': '待完成', 'status': 'todo'},
    ]
    if payload['role'] == ROLE_ADMIN:
        lifecycle.insert(1, {'label': '设置为管理员', 'date': now, 'status': 'done'})
    conn.execute(
        '''
        INSERT INTO life_users (
            id, username, email, name, password_hash, role, status, avatar,
            preferences_json, lifecycle_json, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ''',
        (
            user_id,
            username,
            payload['email'],
            payload['name'],
            hash_password(payload['password']),
            payload['role'],
            STATUS_ACTIVE,
            payload['avatar'],
            '{"reminder":true,"theme":"light","defaultView":"timeline"}',
            __import__('json').dumps(lifecycle, ensure_ascii=False),
            __import__('datetime').datetime.utcnow().replace(microsecond=0).isoformat(),
            __import__('datetime').datetime.utcnow().replace(microsecond=0).isoformat(),
        ),
    )
    token, expires_at = create_session(conn, user_id)
    row = conn.execute('SELECT * FROM life_users WHERE id=?', (user_id,)).fetchone()
    return jsonify({'token': token, 'expires_at': expires_at, 'user': user_public_dict(row)}), 201


@life_bp.route('/auth/login', methods=['POST'])
def login():
    data = parse_json()
    account = normalize_account_identifier(data.get('account') or data.get('username') or data.get('email'))
    password = str(data.get('password', ''))
    conn = get_life_db()
    row = find_account_row(conn, account)
    if not row or row['status'] != STATUS_ACTIVE or not verify_password(password, row['password_hash']):
        return jsonify({'error': '账号或密码不正确'}), 401
    token, expires_at = create_session(conn, row['id'])
    conn.execute(
        'UPDATE life_users SET last_login_at=?, updated_at=? WHERE id=?',
        (
            __import__('datetime').datetime.utcnow().replace(microsecond=0).isoformat(),
            __import__('datetime').datetime.utcnow().replace(microsecond=0).isoformat(),
            row['id'],
        ),
    )
    conn.commit()
    fresh = conn.execute('SELECT * FROM life_users WHERE id=?', (row['id'],)).fetchone()
    return jsonify({'token': token, 'expires_at': expires_at, 'user': user_public_dict(fresh)})


@life_bp.route('/auth/logout', methods=['POST'])
@require_life_auth
def logout():
    token = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
    conn = get_life_db()
    conn.execute('DELETE FROM life_sessions WHERE token=?', (token,))
    conn.commit()
    return jsonify({'ok': True})


@life_bp.route('/auth/me', methods=['GET'])
@require_life_auth
def me():
    return jsonify(user_public_dict(g.life_user))


@life_bp.route('/auth/profile', methods=['PUT'])
@require_life_auth
def update_profile():
    data = parse_json()
    name = str(data.get('name', '')).strip()
    email = normalize_account_identifier(data.get('account') or data.get('username') or data.get('email'))
    avatar = str(data.get('avatar', '')).strip() or 'Q1'
    if not name:
        return jsonify({'error': '请输入昵称'}), 400
    if not email:
        return jsonify({'error': '请输入账号'}), 400
    conn = get_life_db()
    dup = conn.execute(
        'SELECT id FROM life_users WHERE (email=? OR username=?) AND id!=?',
        (email, email, g.life_user['id']),
    ).fetchone()
    if dup:
        return jsonify({'error': '这个账号已被其他用户使用'}), 400
    preferences = data.get('preferences') or {}
    old = user_public_dict(g.life_user)
    merged_preferences = dict(old.get('preferences') or {})
    merged_preferences.update(preferences if isinstance(preferences, dict) else {})
    lifecycle = list(old.get('lifecycle') or [])
    lifecycle.append({'label': '更新资料', 'date': today_iso(), 'status': 'done'})
    now = __import__('datetime').datetime.utcnow().replace(microsecond=0).isoformat()
    conn.execute(
        '''
        UPDATE life_users
        SET name=?, username=?, email=?, avatar=?, preferences_json=?, lifecycle_json=?, updated_at=?
        WHERE id=?
        ''',
        (
            name,
            email,
            email,
            avatar,
            __import__('json').dumps(merged_preferences, ensure_ascii=False),
            __import__('json').dumps(lifecycle, ensure_ascii=False),
            now,
            g.life_user['id'],
        ),
    )
    conn.commit()
    row = conn.execute('SELECT * FROM life_users WHERE id=?', (g.life_user['id'],)).fetchone()
    return jsonify({'ok': True, 'user': user_public_dict(row)})


@life_bp.route('/auth/password', methods=['POST'])
@require_life_auth
def change_password():
    data = parse_json()
    old_password = str(data.get('oldPassword', data.get('old_password', '')))
    new_password = str(data.get('newPassword', data.get('new_password', '')))
    if len(new_password) < 6:
        return jsonify({'error': '新密码至少需要 6 位'}), 400
    conn = get_life_db()
    row = conn.execute('SELECT password_hash, lifecycle_json FROM life_users WHERE id=?', (g.life_user['id'],)).fetchone()
    if not row or not verify_password(old_password, row['password_hash']):
        return jsonify({'error': '当前密码不正确'}), 400
    lifecycle = __import__('json').loads(row['lifecycle_json'] or '[]')
    lifecycle.append({'label': '修改密码', 'date': today_iso(), 'status': 'done'})
    conn.execute(
        'UPDATE life_users SET password_hash=?, lifecycle_json=?, updated_at=? WHERE id=?',
        (hash_password(new_password), __import__('json').dumps(lifecycle, ensure_ascii=False), __import__('datetime').datetime.utcnow().replace(microsecond=0).isoformat(), g.life_user['id']),
    )
    conn.commit()
    return jsonify({'ok': True})


@life_bp.route('/auth/deactivate', methods=['POST'])
@require_life_auth
def deactivate():
    conn = get_life_db()
    row = conn.execute('SELECT lifecycle_json FROM life_users WHERE id=?', (g.life_user['id'],)).fetchone()
    lifecycle = __import__('json').loads((row and row['lifecycle_json']) or '[]')
    lifecycle.append({'label': '停用账号', 'date': today_iso(), 'status': 'done'})
    now = __import__('datetime').datetime.utcnow().replace(microsecond=0).isoformat()
    conn.execute(
        'UPDATE life_users SET status=?, lifecycle_json=?, updated_at=? WHERE id=?',
        (STATUS_INACTIVE, __import__('json').dumps(lifecycle, ensure_ascii=False), now, g.life_user['id']),
    )
    conn.execute('DELETE FROM life_sessions WHERE user_id=?', (g.life_user['id'],))
    conn.commit()
    return jsonify({'ok': True})


@life_bp.route('/auth/me', methods=['DELETE'])
@require_life_auth
def delete_me():
    conn = get_life_db()
    row = conn.execute('SELECT lifecycle_json FROM life_users WHERE id=?', (g.life_user['id'],)).fetchone()
    lifecycle = __import__('json').loads((row and row['lifecycle_json']) or '[]')
    lifecycle.append({'label': '删除账号', 'date': today_iso(), 'status': 'done'})
    now = __import__('datetime').datetime.utcnow().replace(microsecond=0).isoformat()
    conn.execute(
        'UPDATE life_users SET status=?, deleted_at=?, lifecycle_json=?, updated_at=? WHERE id=?',
        (STATUS_DELETED, now, __import__('json').dumps(lifecycle, ensure_ascii=False), now, g.life_user['id']),
    )
    conn.execute('DELETE FROM life_sessions WHERE user_id=?', (g.life_user['id'],))
    conn.commit()
    return jsonify({'ok': True})


@life_bp.route('/auth/recover/request', methods=['POST'])
def recover_request():
    data = parse_json()
    email = normalize_account_identifier(data.get('account') or data.get('username') or data.get('email'))
    conn = get_life_db()
    user = conn.execute(
        'SELECT id FROM life_users WHERE (email=? OR username=?) AND status!=?',
        (email, email, STATUS_DELETED),
    ).fetchone()
    if not user:
        return jsonify({'error': '没有找到这个账号'}), 404
    code = str(secrets.randbelow(900000) + 100000)
    now = __import__('datetime').datetime.utcnow().replace(microsecond=0)
    expires_at = (now + timedelta(minutes=10)).isoformat()
    conn.execute(
        '''
        INSERT INTO life_password_resets (email, code, expires_at, created_at)
        VALUES (?,?,?,?)
        ON CONFLICT(email) DO UPDATE SET code=excluded.code, expires_at=excluded.expires_at, created_at=excluded.created_at
        ''',
        (email, code, expires_at, now.isoformat()),
    )
    conn.commit()
    return jsonify({'ok': True, 'code': code})


@life_bp.route('/auth/recover/confirm', methods=['POST'])
def recover_confirm():
    data = parse_json()
    email = normalize_account_identifier(data.get('account') or data.get('username') or data.get('email'))
    code = str(data.get('code', '')).strip()
    new_password = str(data.get('password', data.get('newPassword', '')))
    if len(new_password) < 6:
        return jsonify({'error': '新密码至少需要 6 位'}), 400
    conn = get_life_db()
    reset = conn.execute('SELECT * FROM life_password_resets WHERE email=?', (email,)).fetchone()
    if not reset or reset['code'] != code:
        return jsonify({'error': '验证码不正确'}), 400
    if __import__('datetime').datetime.fromisoformat(reset['expires_at']) < __import__('datetime').datetime.utcnow():
        return jsonify({'error': '验证码已过期'}), 400
    user = find_account_row(conn, email)
    if not user:
        return jsonify({'error': '账号不存在'}), 404
    lifecycle = __import__('json').loads(user['lifecycle_json'] or '[]')
    lifecycle.append({'label': '重置密码', 'date': today_iso(), 'status': 'done'})
    conn.execute(
        'UPDATE life_users SET password_hash=?, status=?, lifecycle_json=?, updated_at=? WHERE id=?',
        (
            hash_password(new_password),
            STATUS_ACTIVE,
            __import__('json').dumps(lifecycle, ensure_ascii=False),
            __import__('datetime').datetime.utcnow().replace(microsecond=0).isoformat(),
            user['id'],
        ),
    )
    conn.execute('DELETE FROM life_password_resets WHERE email=?', (email,))
    token, expires_at = create_session(conn, user['id'])
    row = conn.execute('SELECT * FROM life_users WHERE id=?', (user['id'],)).fetchone()
    return jsonify({'ok': True, 'token': token, 'expires_at': expires_at, 'user': user_public_dict(row)})


@life_bp.route('/admin/users', methods=['GET'])
@require_life_admin
def admin_list_users():
    conn = get_life_db()
    rows = conn.execute(
        'SELECT * FROM life_users WHERE status!=? ORDER BY created_at DESC',
        (STATUS_DELETED,),
    ).fetchall()
    return jsonify({'items': [user_public_dict(row) for row in rows]})


@life_bp.route('/admin/users', methods=['POST'])
@require_life_admin
def admin_create_user():
    payload, error = normalize_account_payload(parse_json())
    if error:
        return jsonify({'error': error}), 400
    conn = get_life_db()
    if find_account_row(conn, payload['email']):
        return jsonify({'error': '这个账号已经注册'}), 400
    now = __import__('datetime').datetime.utcnow().replace(microsecond=0).isoformat()
    user_id = gen_id()
    username = ensure_unique_username(conn, payload['username'])
    lifecycle = [
        {'label': '管理员创建账号', 'date': today_iso(), 'status': 'done'},
        {'label': '完善资料', 'date': today_iso(), 'status': 'active'},
    ]
    conn.execute(
        '''
        INSERT INTO life_users (
            id, username, email, name, password_hash, role, status, avatar,
            preferences_json, lifecycle_json, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ''',
        (
            user_id,
            username,
            payload['email'],
            payload['name'],
            hash_password(payload['password']),
            payload['role'],
            STATUS_ACTIVE,
            payload['avatar'],
            '{"reminder":true,"theme":"light","defaultView":"timeline"}',
            __import__('json').dumps(lifecycle, ensure_ascii=False),
            now,
            now,
        ),
    )
    conn.commit()
    row = conn.execute('SELECT * FROM life_users WHERE id=?', (user_id,)).fetchone()
    return jsonify({'ok': True, 'user': user_public_dict(row)}), 201


@life_bp.route('/admin/users/<user_id>', methods=['PATCH'])
@require_life_admin
def admin_patch_user(user_id):
    data = parse_json()
    conn = get_life_db()
    row = conn.execute('SELECT * FROM life_users WHERE id=?', (user_id,)).fetchone()
    if not row:
        return jsonify({'error': '账号不存在'}), 404
    if row['status'] == STATUS_DELETED:
        return jsonify({'error': '账号已删除'}), 400
    status = str(data.get('status', row['status'])).strip()
    role = str(data.get('role', row['role'])).strip()
    if status not in (STATUS_ACTIVE, STATUS_INACTIVE):
        return jsonify({'error': '状态无效'}), 400
    if role not in (ROLE_ADMIN, 'user'):
        return jsonify({'error': '角色无效'}), 400
    status_changed = status != row['status']
    if status_changed:
        if user_id == g.life_user['id']:
            return jsonify({'error': '管理员不能在这里停用或启用当前登录账号'}), 400
        if row['role'] != ROLE_USER:
            return jsonify({'error': '仅支持停用或启用普通用户'}), 400
    name = str(data.get('name', row['name'])).strip() or row['name']
    email = normalize_account_identifier(data.get('account') or data.get('username') or data.get('email') or row['email']) or row['email']
    avatar = str(data.get('avatar', row['avatar'])).strip() or row['avatar']
    dup = conn.execute('SELECT id FROM life_users WHERE (email=? OR username=?) AND id!=?', (email, email, user_id)).fetchone()
    if dup:
        return jsonify({'error': '账号已被占用'}), 400
    lifecycle = __import__('json').loads(row['lifecycle_json'] or '[]')
    if status_changed:
        lifecycle.append({'label': '管理员启用账号' if status == STATUS_ACTIVE else '管理员停用账号', 'date': today_iso(), 'status': 'done'})
    else:
        lifecycle.append({'label': '管理员更新账号', 'date': today_iso(), 'status': 'done'})
    now = __import__('datetime').datetime.utcnow().replace(microsecond=0).isoformat()
    conn.execute(
        '''
        UPDATE life_users
        SET name=?, username=?, email=?, role=?, status=?, avatar=?, lifecycle_json=?, updated_at=?
        WHERE id=?
        ''',
        (name, email, email, role, status, avatar, __import__('json').dumps(lifecycle, ensure_ascii=False), now, user_id),
    )
    if status != STATUS_ACTIVE:
        conn.execute('DELETE FROM life_sessions WHERE user_id=?', (user_id,))
    conn.commit()
    latest = conn.execute('SELECT * FROM life_users WHERE id=?', (user_id,)).fetchone()
    return jsonify({'ok': True, 'user': user_public_dict(latest)})


@life_bp.route('/admin/users/<user_id>', methods=['DELETE'])
@require_life_admin
def admin_delete_user(user_id):
    if user_id == g.life_user['id']:
        return jsonify({'error': '管理员不能删除当前登录账号'}), 400
    conn = get_life_db()
    row = conn.execute('SELECT * FROM life_users WHERE id=?', (user_id,)).fetchone()
    if not row:
        return jsonify({'error': '账号不存在'}), 404
    lifecycle = __import__('json').loads(row['lifecycle_json'] or '[]')
    lifecycle.append({'label': '管理员删除账号', 'date': today_iso(), 'status': 'done'})
    now = __import__('datetime').datetime.utcnow().replace(microsecond=0).isoformat()
    conn.execute(
        'UPDATE life_users SET status=?, deleted_at=?, lifecycle_json=?, updated_at=? WHERE id=?',
        (STATUS_DELETED, now, __import__('json').dumps(lifecycle, ensure_ascii=False), now, user_id),
    )
    conn.execute('DELETE FROM life_sessions WHERE user_id=?', (user_id,))
    conn.commit()
    return jsonify({'ok': True})


@life_bp.route('/admin/users/<user_id>/reset-password', methods=['POST'])
@require_life_admin
def admin_reset_user_password(user_id):
    if user_id == g.life_user['id']:
        return jsonify({'error': '管理员不能重置当前登录账号密码'}), 400
    data = parse_json()
    next_password = str(data.get('password', data.get('newPassword', '')))
    if len(next_password) < 6:
        return jsonify({'error': '新密码至少需要 6 位'}), 400
    conn = get_life_db()
    row = conn.execute('SELECT * FROM life_users WHERE id=?', (user_id,)).fetchone()
    if not row:
        return jsonify({'error': '账号不存在'}), 404
    if row['status'] == STATUS_DELETED:
        return jsonify({'error': '账号已删除'}), 400
    if row['role'] != ROLE_USER:
        return jsonify({'error': '仅支持重置普通用户密码'}), 400
    lifecycle = __import__('json').loads(row['lifecycle_json'] or '[]')
    lifecycle.append({'label': '管理员重置密码', 'date': today_iso(), 'status': 'done'})
    now = __import__('datetime').datetime.utcnow().replace(microsecond=0).isoformat()
    conn.execute(
        'UPDATE life_users SET password_hash=?, status=?, lifecycle_json=?, updated_at=? WHERE id=?',
        (
            hash_password(next_password),
            STATUS_ACTIVE,
            __import__('json').dumps(lifecycle, ensure_ascii=False),
            now,
            user_id,
        ),
    )
    conn.execute('DELETE FROM life_sessions WHERE user_id=?', (user_id,))
    conn.commit()
    return jsonify({'ok': True})


@life_bp.route('/uploads', methods=['POST'])
@require_life_auth
def upload_image():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': '缺少文件'}), 400
    filename = secure_filename(file.filename or '')
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_IMAGE_EXT:
        return jsonify({'error': '仅支持图片文件'}), 400
    file.stream.seek(0, os.SEEK_END)
    file_size = file.stream.tell()
    file.stream.seek(0)
    if file_size > MAX_UPLOAD_BYTES:
        return jsonify({'error': '图片不能超过 8MB'}), 400
    folder = ensure_upload_dir(current_app.config['LIFE_BASE_DIR'], g.life_user['id'])
    name = '{}{}{}'.format(__import__('datetime').datetime.utcnow().strftime('%Y%m%d%H%M%S'), secrets.token_hex(4), ext)
    dest = os.path.join(folder, name)
    file.save(dest)
    rel_url = '/assets/uploads/life/{}/{}'.format(g.life_user['id'], name)
    return jsonify({'url': rel_url})


@life_bp.route('/bootstrap', methods=['GET'])
@require_life_auth
def bootstrap():
    is_mock = request_is_mock()
    conn = get_life_db()
    return jsonify({
        'ok': True,
        'mode': 'mock' if is_mock else 'real',
        'user': user_public_dict(g.life_user),
        'storage': get_storage_snapshot(conn, g.life_user['id'], is_mock),
        'data': bootstrap_payload(conn, g.life_user['id'], is_mock),
    })


@life_bp.route('/storage', methods=['GET'])
@require_life_auth
def storage_snapshot():
    is_mock = request_is_mock()
    conn = get_life_db()
    return jsonify({'ok': True, 'items': get_storage_snapshot(conn, g.life_user['id'], is_mock)})


@life_bp.route('/storage/<path:storage_key>', methods=['PUT'])
@require_life_auth
def put_storage(storage_key):
    data = parse_json()
    if not isinstance(data, dict) or 'value' not in data:
        return jsonify({'error': '缺少 value'}), 400
    set_storage_value(get_life_db(), g.life_user['id'], request_is_mock(data), storage_key, data['value'])
    return jsonify({'ok': True})


@life_bp.route('/snapshot/<module>', methods=['PUT'])
@require_life_auth
def replace_snapshot(module):
    module_name, error_resp, code = module_from_path(module)
    if error_resp:
        return error_resp, code
    data = parse_json()
    items = data.get('items') or []
    if not isinstance(items, list):
        return jsonify({'error': 'items 必须是数组'}), 400
    conn = get_life_db()
    replace_module_records(conn, module_name, g.life_user['id'], request_is_mock(data), items)
    return jsonify({'ok': True, 'count': len(items)})


@life_bp.route('/<module>', methods=['GET'])
@require_life_auth
def list_module(module):
    module_name, error_resp, code = module_from_path(module)
    if error_resp:
        return error_resp, code
    conn = get_life_db()
    from .service import list_module_records
    items = list_module_records(
        conn,
        module_name,
        g.life_user['id'],
        request_is_mock(),
        {
            'query': request.args.get('query', ''),
            'status': request.args.get('status', ''),
            'category': request.args.get('category', ''),
            'year': request.args.get('year', ''),
        },
    )
    return jsonify({'items': items})


@life_bp.route('/<module>', methods=['POST'])
@require_life_auth
def create_module(module):
    module_name, error_resp, code = module_from_path(module)
    if error_resp:
        return error_resp, code
    data = parse_json()
    if not isinstance(data, dict):
        return jsonify({'error': '无效请求'}), 400
    payload = data.get('item') if isinstance(data.get('item'), dict) else data
    conn = get_life_db()
    item = upsert_module_record(conn, module_name, g.life_user['id'], request_is_mock(data), payload)
    return jsonify({'ok': True, 'item': item}), 201


@life_bp.route('/<module>/<record_id>', methods=['GET'])
@require_life_auth
def get_module_item(module, record_id):
    module_name, error_resp, code = module_from_path(module)
    if error_resp:
        return error_resp, code
    from .service import get_module_record
    item = get_module_record(get_life_db(), module_name, g.life_user['id'], request_is_mock(), record_id)
    if not item:
        return jsonify({'error': '记录不存在'}), 404
    return jsonify({'item': item})


@life_bp.route('/<module>/<record_id>', methods=['PUT'])
@require_life_auth
def update_module_item(module, record_id):
    module_name, error_resp, code = module_from_path(module)
    if error_resp:
        return error_resp, code
    data = parse_json()
    payload = dict(data.get('item') if isinstance(data.get('item'), dict) else data)
    payload['id'] = record_id
    conn = get_life_db()
    item = upsert_module_record(conn, module_name, g.life_user['id'], request_is_mock(data), payload)
    return jsonify({'ok': True, 'item': item})


@life_bp.route('/<module>/<record_id>', methods=['DELETE'])
@require_life_auth
def delete_module_item(module, record_id):
    module_name, error_resp, code = module_from_path(module)
    if error_resp:
        return error_resp, code
    conn = get_life_db()
    delete_module_record(conn, module_name, g.life_user['id'], request_is_mock(), record_id)
    return jsonify({'ok': True})
