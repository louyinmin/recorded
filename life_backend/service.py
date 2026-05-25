"""Core services for Life backend."""

import functools
import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta

from flask import current_app, g, jsonify, request

from .security import hash_password, verify_password


ROLE_ADMIN = 'admin'
ROLE_USER = 'user'
STATUS_ACTIVE = 'active'
STATUS_INACTIVE = 'inactive'
STATUS_DELETED = 'deleted'
SESSION_DAYS = 30

MODULE_TABLES = {
    'moments': 'life_moments',
    'axis': 'life_axis_milestones',
    'decisions': 'life_decisions',
    'moods': 'life_mood_records',
    'relationships': 'life_relationships',
    'relationship-media': 'life_relationship_media',
    'wishes': 'life_wishes',
    'monthly': 'life_monthly',
    'watch': 'life_watch',
    'projects': 'life_projects',
    'health': 'life_health_records',
    'resources': 'life_resources',
}

SYNC_BRIDGE_STORAGE_MODULES = {
    'life_moments_v1': 'moments',
    'life_mock_moments_v1': 'moments',
    'life_axis_milestones_v1': 'axis',
    'life_mock_axis_milestones_v1': 'axis',
    'life_decisions_v1': 'decisions',
    'life_mock_decisions_v1': 'decisions',
    'life_mood_records_v1': 'moods',
    'life_mock_mood_records_v1': 'moods',
    'life_relationships_v1': 'relationships',
    'life_mock_relationships_v1': 'relationships',
    'life_wishes_v1': 'wishes',
    'life_mock_wishes_v1': 'wishes',
    'life_monthly_v1': 'monthly',
    'life_mock_monthly_v1': 'monthly',
    'life_watch_v1': 'watch',
    'life_mock_watch_v1': 'watch',
    'life_projects_v1': 'projects',
    'life_mock_projects_v1': 'projects',
    'life_health_records_v1': 'health',
    'life_mock_health_records_v1': 'health',
    'life_resources_v1': 'resources',
    'life_mock_resources_v1': 'resources',
}


def utcnow():
    return datetime.utcnow().replace(microsecond=0)


def utcnow_iso():
    return utcnow().isoformat()


def today_iso():
    return datetime.now().strftime('%Y-%m-%d')


def gen_id():
    return uuid.uuid4().hex[:16]


def connect_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def get_life_db():
    if 'life_db' not in g:
        g.life_db = connect_db(current_app.config['LIFE_DB_PATH'])
    return g.life_db


def close_life_db(exc=None):
    db = g.pop('life_db', None)
    if db is not None:
        db.close()


def row_to_dict(row):
    return dict(row) if row is not None else None


def normalize_mock_mode(value):
    text = str(value or '').strip().lower()
    return text in ('1', 'true', 'mock', 'yes', 'y')


def request_is_mock(payload=None):
    if payload and isinstance(payload, dict) and 'mode' in payload:
        return normalize_mock_mode(payload.get('mode'))
    return normalize_mock_mode(request.args.get('mode', '')) or normalize_mock_mode(request.args.get('mock', ''))


def parse_json(text, fallback):
    try:
        return json.loads(text or '')
    except Exception:
        return fallback


def init_life_db(db_path):
    conn = connect_db(db_path)
    try:
        conn.executescript(
            '''
            CREATE TABLE IF NOT EXISTS life_users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin','user')) DEFAULT 'user',
                status TEXT NOT NULL CHECK(status IN ('active','inactive','deleted')) DEFAULT 'active',
                avatar TEXT DEFAULT 'Q1',
                preferences_json TEXT NOT NULL DEFAULT '{}',
                lifecycle_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT,
                deleted_at TEXT
            );

            CREATE TABLE IF NOT EXISTS life_sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES life_users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS life_password_resets (
                email TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS life_storage (
                user_id TEXT NOT NULL,
                is_mock INTEGER NOT NULL DEFAULT 0,
                storage_key TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, is_mock, storage_key),
                FOREIGN KEY (user_id) REFERENCES life_users(id) ON DELETE CASCADE
            );
            '''
        )
        for table in MODULE_TABLES.values():
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS {} (
                    user_id TEXT NOT NULL,
                    is_mock INTEGER NOT NULL DEFAULT 0,
                    id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, is_mock, id),
                    FOREIGN KEY (user_id) REFERENCES life_users(id) ON DELETE CASCADE
                )
                '''.format(table)
            )
        migrate_sync_bridge_storage_to_mock_modules(conn)
        conn.commit()
        ensure_seed_accounts(conn)
        conn.commit()
    finally:
        conn.close()


def retire_conflicting_accounts(conn, user_id, usernames, emails):
    usernames = [item for item in usernames if item]
    emails = [item for item in emails if item]
    if not usernames and not emails:
        return
    rows = conn.execute(
        '''
        SELECT id, username, email FROM life_users
        WHERE id!=?
          AND (
            username IN ({usernames})
            OR email IN ({emails})
          )
        '''.format(
            usernames=','.join('?' for _ in usernames) or "''",
            emails=','.join('?' for _ in emails) or "''",
        ),
        [user_id] + usernames + emails,
    ).fetchall()
    now = utcnow_iso()
    for row in rows:
      suffix = '_deleted_' + row['id'][:8]
      conn.execute(
          '''
          UPDATE life_users
          SET username=?, email=?, status=?, deleted_at=?, updated_at=?
          WHERE id=?
          ''',
          (
              (row['username'] or 'user') + suffix,
              (row['email'] or 'account') + suffix,
              STATUS_DELETED,
              now,
              now,
              row['id'],
          ),
      )
      conn.execute('DELETE FROM life_sessions WHERE user_id=?', (row['id'],))


def find_account_row(conn, account):
    account = normalize_account_identifier(account)
    if not account:
        return None
    return conn.execute(
        '''
        SELECT * FROM life_users
        WHERE username=? OR email=?
        ORDER BY status='active' DESC, created_at ASC
        LIMIT 1
        ''',
        (account, account),
    ).fetchone()


def upsert_seed_account(conn, account, password, role, avatar):
    now = utcnow_iso()
    row = find_account_row(conn, account)
    lifecycle = [
        {'label': '创建账号', 'date': today_iso(), 'status': 'done'},
        {'label': '完善资料', 'date': today_iso(), 'status': 'done'},
        {'label': '启用安全设置', 'date': today_iso(), 'status': 'active'},
    ]
    preferences = {'reminder': True, 'theme': 'light', 'defaultView': 'timeline'}
    if row:
        status = STATUS_ACTIVE if role == ROLE_ADMIN else row['status']
        deleted_at = row['deleted_at'] if status == STATUS_DELETED else None
        preserved_lifecycle = row['lifecycle_json'] or json.dumps(lifecycle, ensure_ascii=False)
        preserved_preferences = row['preferences_json'] or json.dumps(preferences, ensure_ascii=False)
        retire_conflicting_accounts(conn, row['id'], [account], [account])
        conn.execute(
            '''
            UPDATE life_users
            SET username=?, email=?, name=?, password_hash=?, role=?, status=?, avatar=?,
                preferences_json=?, lifecycle_json=?, deleted_at=?, updated_at=?
            WHERE id=?
            ''',
            (
                account,
                account,
                account,
                hash_password(password),
                role,
                status,
                avatar,
                preserved_preferences,
                preserved_lifecycle,
                deleted_at,
                now,
                row['id'],
            ),
        )
        if status != STATUS_ACTIVE:
            conn.execute('DELETE FROM life_sessions WHERE user_id=?', (row['id'],))
        return
    user_id = gen_id()
    retire_conflicting_accounts(conn, user_id, [account], [account])
    conn.execute(
        '''
        INSERT INTO life_users (
            id, username, email, name, password_hash, role, status, avatar,
            preferences_json, lifecycle_json, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ''',
        (
            user_id,
            account,
            account,
            account,
            hash_password(password),
            role,
            STATUS_ACTIVE,
            avatar,
            json.dumps(preferences, ensure_ascii=False),
            json.dumps(lifecycle, ensure_ascii=False),
            now,
            now,
        ),
    )


def migrate_legacy_xyc_seed(conn):
    legacy = conn.execute(
        '''
        SELECT * FROM life_users
        WHERE username='admin' AND email='654321' AND lower(name)='xyc'
        ORDER BY created_at ASC
        LIMIT 1
        '''
    ).fetchone()
    if not legacy:
        return
    retire_conflicting_accounts(conn, legacy['id'], ['xyc'], ['xyc', 'xyc@qq.com'])
    now = utcnow_iso()
    lifecycle = [
        {'label': '修正为普通用户', 'date': today_iso(), 'status': 'done'},
        {'label': '启用安全设置', 'date': today_iso(), 'status': 'active'},
    ]
    conn.execute(
        '''
        UPDATE life_users
        SET username=?, email=?, name=?, password_hash=?, role=?, status=?, avatar=?,
            lifecycle_json=?, deleted_at=NULL, updated_at=?
        WHERE id=?
        ''',
        (
            'xyc',
            'xyc',
            'xyc',
            hash_password('654321'),
            ROLE_USER,
            STATUS_ACTIVE,
            'Q1',
            json.dumps(lifecycle, ensure_ascii=False),
            now,
            legacy['id'],
        ),
    )
    conn.execute('DELETE FROM life_sessions WHERE user_id=?', (legacy['id'],))


def ensure_seed_accounts(conn):
    migrate_legacy_xyc_seed(conn)
    upsert_seed_account(conn, 'admin', 'OOoo0000', ROLE_ADMIN, 'Q1')
    upsert_seed_account(conn, 'xyc', '654321', ROLE_USER, 'Q1')


def get_user_by_token(conn, token):
    token = str(token or '').strip()
    if not token:
        return None
    row = conn.execute(
        '''
        SELECT u.*, s.expires_at
        FROM life_sessions s
        JOIN life_users u ON u.id = s.user_id
        WHERE s.token=?
        ''',
        (token,),
    ).fetchone()
    if not row:
        return None
    if datetime.fromisoformat(row['expires_at']) < utcnow():
        conn.execute('DELETE FROM life_sessions WHERE token=?', (token,))
        conn.commit()
        return None
    if row['status'] != STATUS_ACTIVE:
        return None
    return row_to_dict(row)


def get_token_from_request():
    auth = request.headers.get('Authorization', '')
    if auth.lower().startswith('bearer '):
        return auth[7:].strip()
    return ''


def create_session(conn, user_id):
    token = uuid.uuid4().hex + uuid.uuid4().hex
    now = utcnow()
    expires_at = now + timedelta(days=SESSION_DAYS)
    conn.execute(
        '''
        INSERT INTO life_sessions (token, user_id, expires_at, created_at)
        VALUES (?,?,?,?)
        ''',
        (token, user_id, expires_at.isoformat(), now.isoformat()),
    )
    conn.commit()
    return token, expires_at.isoformat()


def require_life_auth(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        conn = get_life_db()
        user = get_user_by_token(conn, get_token_from_request())
        if not user:
            return jsonify({'error': '未登录或登录已过期'}), 401
        g.life_user = user
        return func(*args, **kwargs)
    return wrapped


def require_life_admin(func):
    @functools.wraps(func)
    @require_life_auth
    def wrapped(*args, **kwargs):
        if str(g.life_user.get('role') or '') != ROLE_ADMIN:
            return jsonify({'error': '只有管理员可以执行此操作'}), 403
        return func(*args, **kwargs)
    return wrapped


def normalize_account_payload(payload):
    name = str(payload.get('name', '')).strip()
    account = normalize_account_identifier(payload.get('account') or payload.get('username') or payload.get('email'))
    password = str(payload.get('password', ''))
    role = str(payload.get('role', ROLE_USER)).strip().lower()
    avatar = str(payload.get('avatar', 'Q1')).strip() or 'Q1'
    if not name:
        return None, '请输入昵称'
    if not account:
        return None, '请输入账号'
    if len(password) < 6:
        return None, '密码至少需要 6 位'
    if role not in (ROLE_USER, ROLE_ADMIN):
        role = ROLE_USER
    if role == ROLE_ADMIN and str(payload.get('adminCode', '')).strip() != 'LIFE-ADMIN':
        return None, '管理员邀请码不正确'
    return {
        'name': name,
        'username': username_from_email(account),
        'email': account,
        'password': password,
        'role': role,
        'avatar': avatar,
    }, None


def user_public_dict(user):
    data = dict(user)
    data.pop('password_hash', None)
    data['preferences'] = parse_json(data.pop('preferences_json', '{}'), {})
    data['lifecycle'] = parse_json(data.pop('lifecycle_json', '[]'), [])
    return data


def username_from_email(email):
    base = str(email or '').split('@', 1)[0].strip() or 'life'
    safe = ''.join(ch for ch in base if ch.isalnum() or ch in ('-', '_')).lower()
    return safe or 'life'


def normalize_account_identifier(value):
    return str(value or '').strip().lower()


def ensure_unique_username(conn, username):
    candidate = username
    index = 1
    while conn.execute('SELECT id FROM life_users WHERE username=?', (candidate,)).fetchone():
        index += 1
        candidate = '{}{}'.format(username, index)
    return candidate


def add_months(iso_date, months):
    try:
        value = datetime.strptime(str(iso_date), '%Y-%m-%d')
    except Exception:
        return ''
    month = value.month - 1 + int(months)
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(value.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return '{}-{:02d}-{:02d}'.format(year, month, day)


def axis_date_label(iso_date):
    try:
        value = datetime.strptime(str(iso_date), '%Y-%m-%d')
    except Exception:
        return ''
    return '{:02d}-{:02d}'.format(value.month, value.day)


def normalize_record_for_module(module, payload):
    data = dict(payload or {})
    if not data.get('id'):
        data['id'] = gen_id()
    if module == 'decisions':
        record_date = str(data.get('date') or data.get('recordDate') or '').strip()
        review_date = str(data.get('reviewDate') or '').strip()
        if record_date and not review_date:
            data['reviewDate'] = add_months(record_date, 6)
    if module == 'axis':
        date_value = str(data.get('date') or '').strip()
        if date_value:
            data['dateLabel'] = axis_date_label(date_value)
    return data


def sync_bridge_record_id_prefix(storage_key, storage_is_mock):
    source = '{}-{}'.format('mock' if storage_is_mock else 'real', storage_key)
    safe_key = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '-' for ch in source)
    return 'sync-bridge-' + safe_key[:72] + '-'


def sync_bridge_record_id(storage_key, storage_is_mock, index, original_id):
    source = '{}-{}-{}'.format('mock' if storage_is_mock else 'real', storage_key, original_id or index)
    safe = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '-' for ch in source)
    return 'sync-bridge-' + safe[:96]


def sync_bridge_items_from_storage_value(value):
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []
    if isinstance(value.get('added'), list) or isinstance(value.get('edits'), dict):
        items = []
        seen = set()
        deleted = set(str(item) for item in value.get('deleted', []) if item is not None)
        for item in value.get('added', []):
            if isinstance(item, dict) and str(item.get('id', '')) not in deleted:
                items.append(dict(item))
                if item.get('id') is not None:
                    seen.add(str(item.get('id')))
        edits = value.get('edits') or {}
        if isinstance(edits, dict):
            for item_id, item in edits.items():
                if str(item_id) in deleted:
                    continue
                if isinstance(item, dict):
                    edited = dict(item)
                    edited.setdefault('id', item_id)
                    if str(edited.get('id', '')) not in seen:
                        items.append(edited)
        return items
    if any(value.get(key) for key in ('bookmarked', 'reports', 'archived', 'letters', 'quotes', 'summaries')):
        monthly = dict(value)
        monthly.setdefault('id', 'sync-bridge-monthly')
        return [monthly]
    return []


def sync_bridge_item_signature(module, item):
    if module == 'watch':
        return (
            str(item.get('title', '')).strip(),
            str(item.get('date', '')).strip(),
            str(item.get('kind', '')).strip(),
            str(item.get('watchState', '')).strip(),
        )
    if module == 'moments':
        return (
            str(item.get('title', '')).strip(),
            str(item.get('date', '')).strip(),
            str(item.get('time', '')).strip(),
            str(item.get('type', '')).strip(),
        )
    if module == 'relationships':
        return (
            str(item.get('name', '')).strip(),
            str(item.get('nextDate', '')).strip(),
            str(item.get('group', '')).strip(),
        )
    if module == 'wishes':
        return (
            str(item.get('name', '')).strip(),
            str(item.get('due', '')).strip(),
            str(item.get('status', '')).strip(),
        )
    if module == 'axis':
        return (
            str(item.get('title', '')).strip(),
            str(item.get('date', '')).strip(),
            str(item.get('type', '')).strip(),
            str(item.get('place', '')).strip(),
        )
    if module == 'decisions':
        return (
            str(item.get('title', '')).strip(),
            str(item.get('date', '')).strip(),
            str(item.get('choice', '')).strip(),
            str(item.get('status', '')).strip(),
        )
    if module == 'moods':
        return (
            str(item.get('date', '')).strip(),
            str(item.get('score', '')).strip(),
            str(item.get('feeling', '')).strip(),
            str(item.get('weather', '')).strip(),
        )
    if module == 'monthly':
        return ('monthly-state',)
    if module in ('projects', 'health', 'resources'):
        return (
            str(item.get('name', '')).strip(),
            str(item.get('value', '')).strip(),
            str(item.get('status', '')).strip(),
        )
    normalized = dict(item)
    normalized.pop('id', None)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True)


def dedupe_sync_bridge_items(module, items):
    seen = set()
    unique = []
    for item in list(items or []):
        sig = sync_bridge_item_signature(module, item)
        if sig in seen:
            continue
        seen.add(sig)
        unique.append(item)
    return unique


def mark_sync_bridge_test_item(storage_key, storage_is_mock, item, index):
    original_id = item.get('id')
    marked = dict(item)
    marked['id'] = sync_bridge_record_id(storage_key, storage_is_mock, index, original_id)
    if original_id is not None:
        marked['originalId'] = str(original_id)
    marked['isTestData'] = True
    marked['dataTag'] = 'test'
    marked['dataScope'] = 'sync_bridge_test'
    marked['_syncBridge'] = {
        'storageKey': storage_key,
        'storageMode': 'mock' if storage_is_mock else 'real',
        'originalId': str(original_id or ''),
    }
    marked.setdefault('source', 'sync_bridge')
    return marked


def migrate_sync_bridge_storage_to_mock_modules(conn, user_id=None):
    where = 'WHERE user_id=?' if user_id else ''
    params = (user_id,) if user_id else ()
    rows = conn.execute(
        '''
        SELECT user_id, is_mock, storage_key, payload_json
        FROM life_storage
        {}
        '''.format(where),
        params,
    ).fetchall()
    now = utcnow_iso()
    migrated = 0
    # Merge sources per (user,module): combine mock+real storage rows, then dedupe.
    grouped = {}
    for row in rows:
        module = SYNC_BRIDGE_STORAGE_MODULES.get(row['storage_key'])
        if not module:
            continue
        value = parse_json(row['payload_json'], None)
        items = dedupe_sync_bridge_items(module, sync_bridge_items_from_storage_value(value))
        key = (row['user_id'], module)
        grouped.setdefault(key, []).append({'row': row, 'items': items})

    for key, group in grouped.items():
        group = sorted(group, key=lambda item: (1 if bool(item['row']['is_mock']) else 0), reverse=True)
        row = group[0]['row']
        module = SYNC_BRIDGE_STORAGE_MODULES.get(row['storage_key'])
        merged_items = []
        for entry in group:
            merged_items.extend(entry['items'])
        items = dedupe_sync_bridge_items(module, merged_items)
        table = MODULE_TABLES[module]

        conn.execute(
            '''
            DELETE FROM {}
            WHERE user_id=? AND is_mock=1
              AND json_extract(payload_json, '$.dataScope')='sync_bridge_test'
            '''.format(table),
            (row['user_id'],),
        )

        for index, item in enumerate(items):
            payload = mark_sync_bridge_test_item(row['storage_key'], bool(row['is_mock']), item, index)
            payload = normalize_record_for_module(module, payload)
            conn.execute(
                '''
                INSERT INTO {} (user_id, is_mock, id, payload_json, created_at, updated_at)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(user_id, is_mock, id)
                DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at
                '''.format(table),
                (
                    row['user_id'],
                    1,
                    payload['id'],
                    json.dumps(payload, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            migrated += 1
    return migrated


def list_module_records(conn, module, user_id, is_mock, filters=None):
    table = MODULE_TABLES[module]
    rows = conn.execute(
        '''
        SELECT payload_json FROM {}
        WHERE user_id=? AND is_mock=?
        ORDER BY updated_at DESC, created_at DESC
        '''.format(table),
        (user_id, int(bool(is_mock))),
    ).fetchall()
    items = [parse_json(row['payload_json'], {}) for row in rows]
    filters = filters or {}
    query = str(filters.get('query', '')).strip().lower()
    if query:
        items = [item for item in items if query in json.dumps(item, ensure_ascii=False).lower()]
    status = str(filters.get('status', '')).strip()
    if status:
        items = [item for item in items if str(item.get('status', '')).strip() == status]
    category = str(filters.get('category', '')).strip()
    if category:
        items = [item for item in items if str(item.get('category', '')).strip() == category]
    year = str(filters.get('year', '')).strip()
    if year:
        items = [item for item in items if str(item.get('year', '')).strip() == year]
    return items


def get_module_record(conn, module, user_id, is_mock, record_id):
    table = MODULE_TABLES[module]
    row = conn.execute(
        '''
        SELECT payload_json FROM {}
        WHERE user_id=? AND is_mock=? AND id=?
        '''.format(table),
        (user_id, int(bool(is_mock)), record_id),
    ).fetchone()
    return parse_json(row['payload_json'], {}) if row else None


def upsert_module_record(conn, module, user_id, is_mock, payload):
    table = MODULE_TABLES[module]
    item = normalize_record_for_module(module, payload)
    now = utcnow_iso()
    conn.execute(
        '''
        INSERT INTO {} (user_id, is_mock, id, payload_json, created_at, updated_at)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(user_id, is_mock, id)
        DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at
        '''.format(table),
        (
            user_id,
            int(bool(is_mock)),
            item['id'],
            json.dumps(item, ensure_ascii=False),
            now,
            now,
        ),
    )
    conn.commit()
    return item


def delete_module_record(conn, module, user_id, is_mock, record_id):
    table = MODULE_TABLES[module]
    conn.execute(
        'DELETE FROM {} WHERE user_id=? AND is_mock=? AND id=?'.format(table),
        (user_id, int(bool(is_mock)), record_id),
    )
    conn.commit()


def replace_module_records(conn, module, user_id, is_mock, items):
    table = MODULE_TABLES[module]
    now = utcnow_iso()
    conn.execute(
        'DELETE FROM {} WHERE user_id=? AND is_mock=?'.format(table),
        (user_id, int(bool(is_mock))),
    )
    for payload in list(items or []):
        item = normalize_record_for_module(module, payload)
        conn.execute(
            '''
            INSERT INTO {} (user_id, is_mock, id, payload_json, created_at, updated_at)
            VALUES (?,?,?,?,?,?)
            '''.format(table),
            (
                user_id,
                int(bool(is_mock)),
                item['id'],
                json.dumps(item, ensure_ascii=False),
                now,
                now,
            ),
        )
    conn.commit()


def bootstrap_payload(conn, user_id, is_mock):
    if is_mock:
        ensure_mock_module_records(conn, user_id)
    data = {}
    for module in MODULE_TABLES:
        data[module] = list_module_records(conn, module, user_id, is_mock)
    return data


def mark_server_mock_item(module, item):
    payload = dict(item)
    payload.setdefault('id', 'mock-{}-{}'.format(module, gen_id()))
    payload['isTestData'] = True
    payload['dataTag'] = 'test'
    payload['dataScope'] = 'server_mock_fixture'
    payload.setdefault('source', 'server_mock_fixture')
    return payload


def ensure_mock_module_records(conn, user_id):
    from .mock_data import MOCK_MODULE_RECORDS

    now = utcnow_iso()
    changed = False
    for module, items in MOCK_MODULE_RECORDS.items():
        if module not in MODULE_TABLES:
            continue
        table = MODULE_TABLES[module]
        for item in items:
            payload = normalize_record_for_module(module, mark_server_mock_item(module, item))
            existing = conn.execute(
                '''
                SELECT payload_json
                FROM {}
                WHERE user_id=? AND is_mock=1 AND id=?
                LIMIT 1
                '''.format(table),
                (user_id, payload['id']),
            ).fetchone()
            if existing:
                existing_payload = parse_json(existing['payload_json'], {})
                if str(existing_payload.get('dataScope') or '') != 'server_mock_fixture':
                    continue
                conn.execute(
                    '''
                    UPDATE {}
                    SET payload_json=?, updated_at=?
                    WHERE user_id=? AND is_mock=1 AND id=?
                    '''.format(table),
                    (
                        json.dumps(payload, ensure_ascii=False),
                        now,
                        user_id,
                        payload['id'],
                    ),
                )
                changed = True
                continue
            conn.execute(
                '''
                INSERT INTO {} (user_id, is_mock, id, payload_json, created_at, updated_at)
                VALUES (?,?,?,?,?,?)
                '''.format(table),
                (
                    user_id,
                    1,
                    payload['id'],
                    json.dumps(payload, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            changed = True
    if changed:
        conn.commit()


def get_storage_snapshot(conn, user_id, is_mock):
    rows = conn.execute(
        '''
        SELECT storage_key, payload_json
        FROM life_storage
        WHERE user_id=? AND is_mock=?
        ''',
        (user_id, int(bool(is_mock))),
    ).fetchall()
    result = {}
    for row in rows:
        result[row['storage_key']] = parse_json(row['payload_json'], [])
    return result


def set_storage_value(conn, user_id, is_mock, storage_key, value):
    conn.execute(
        '''
        INSERT INTO life_storage (user_id, is_mock, storage_key, payload_json, updated_at)
        VALUES (?,?,?,?,?)
        ON CONFLICT(user_id, is_mock, storage_key)
        DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at
        ''',
        (
            user_id,
            int(bool(is_mock)),
            storage_key,
            json.dumps(value, ensure_ascii=False),
            utcnow_iso(),
        ),
    )
    migrate_sync_bridge_storage_to_mock_modules(conn, user_id)
    conn.commit()


def ensure_upload_dir(base_dir, user_id):
    folder = os.path.join(base_dir, 'assets', 'uploads', 'life', user_id)
    os.makedirs(folder, exist_ok=True)
    return folder
