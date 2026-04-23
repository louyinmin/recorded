"""Shared data and business helpers for the expiry module."""

import functools
import json
import secrets
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from flask import current_app, g, jsonify, request

from .security import decrypt_secret, encrypt_secret, ensure_app_secret, hash_password, verify_password


DEFAULT_TIMEZONE = 'Asia/Shanghai'
DEFAULT_NOTIFY_OFFSETS = '30,7,1'
SESSION_DAYS = 30
ROLE_ADMIN = 'admin'
ROLE_USER = 'user'
STATUS_ACTIVE = 'active'
STATUS_DISABLED = 'disabled'
RESOURCE_ACTIVE = 'active'
RESOURCE_STOPPED = 'stopped'
EMAIL_AUTH_PASSWORD = 'password'
EMAIL_AUTH_MICROSOFT_OAUTH2 = 'microsoft_oauth2'
MICROSOFT_OAUTH_SCOPE = 'https://outlook.office.com/SMTP.Send offline_access'


def utcnow():
    return datetime.utcnow().replace(microsecond=0)


def utcnow_iso():
    return utcnow().isoformat()


def local_today(timezone_name=DEFAULT_TIMEZONE):
    return datetime.now(ZoneInfo(timezone_name)).date()


def get_db_path():
    return current_app.config['EXPIRY_DB_PATH']


def get_base_dir():
    return current_app.config['EXPIRY_BASE_DIR']


def connect_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def get_expiry_db():
    if 'expiry_db' not in g:
        g.expiry_db = connect_db(get_db_path())
    return g.expiry_db


def close_expiry_db(exc=None):
    db = g.pop('expiry_db', None)
    if db is not None:
        db.close()


def row_to_dict(row):
    return dict(row) if row is not None else None


def init_expiry_db(db_path, base_dir):
    conn = connect_db(db_path)
    try:
        conn.executescript(
            '''
            CREATE TABLE IF NOT EXISTS expiry_users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin','user')),
                status TEXT NOT NULL CHECK(status IN ('active','disabled')) DEFAULT 'active',
                email TEXT DEFAULT '',
                must_change_password INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                last_login_at TEXT
            );

            CREATE TABLE IF NOT EXISTS expiry_sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES expiry_users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS expiry_resources (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                provider TEXT DEFAULT '',
                category TEXT DEFAULT '',
                resource_type TEXT NOT NULL CHECK(resource_type IN ('subscription','one_time')),
                billing_cycle TEXT NOT NULL CHECK(billing_cycle IN ('monthly','yearly','none')),
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'CNY',
                start_date TEXT DEFAULT '',
                next_due_date TEXT NOT NULL,
                auto_renew INTEGER NOT NULL DEFAULT 0,
                manual_status TEXT NOT NULL CHECK(manual_status IN ('active','stopped')) DEFAULT 'active',
                notify_offsets TEXT DEFAULT '',
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES expiry_users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS expiry_notifications (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                channel TEXT NOT NULL CHECK(channel IN ('site','email')),
                scheduled_for TEXT NOT NULL,
                sent_at TEXT,
                read_at TEXT,
                status TEXT NOT NULL CHECK(status IN ('pending','sent','failed','read','canceled')),
                message TEXT NOT NULL,
                dedupe_key TEXT NOT NULL,
                error_message TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES expiry_users(id) ON DELETE CASCADE,
                FOREIGN KEY (resource_id) REFERENCES expiry_resources(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS expiry_email_settings (
                user_id TEXT PRIMARY KEY,
                smtp_host TEXT DEFAULT '',
                smtp_port INTEGER DEFAULT 587,
                smtp_username TEXT DEFAULT '',
                smtp_password_encrypted TEXT DEFAULT '',
                smtp_security TEXT NOT NULL DEFAULT 'starttls',
                from_email TEXT DEFAULT '',
                from_name TEXT DEFAULT '',
                auth_mode TEXT NOT NULL DEFAULT 'password',
                oauth_tenant_id TEXT DEFAULT '',
                oauth_client_id TEXT DEFAULT '',
                oauth_client_secret_encrypted TEXT DEFAULT '',
                oauth_refresh_token_encrypted TEXT DEFAULT '',
                oauth_access_token_encrypted TEXT DEFAULT '',
                oauth_access_token_expires_at TEXT DEFAULT '',
                enabled INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES expiry_users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS expiry_user_settings (
                user_id TEXT PRIMARY KEY,
                default_notify_offsets TEXT NOT NULL DEFAULT '30,7,1',
                timezone TEXT NOT NULL DEFAULT 'Asia/Shanghai',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES expiry_users(id) ON DELETE CASCADE
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_expiry_notifications_dedupe
            ON expiry_notifications(dedupe_key);

            CREATE INDEX IF NOT EXISTS idx_expiry_resources_user_status
            ON expiry_resources(user_id, manual_status, next_due_date);

            CREATE INDEX IF NOT EXISTS idx_expiry_notifications_user_status
            ON expiry_notifications(user_id, channel, status, scheduled_for);
            '''
        )
        ensure_email_settings_columns(conn)
        conn.commit()
    finally:
        conn.close()
    ensure_app_secret(base_dir)


def ensure_email_settings_columns(conn):
    rows = conn.execute("PRAGMA table_info('expiry_email_settings')").fetchall()
    column_names = {row['name'] for row in rows}
    add_columns = [
        ('auth_mode', "TEXT NOT NULL DEFAULT 'password'"),
        ('oauth_tenant_id', "TEXT DEFAULT ''"),
        ('oauth_client_id', "TEXT DEFAULT ''"),
        ('oauth_client_secret_encrypted', "TEXT DEFAULT ''"),
        ('oauth_refresh_token_encrypted', "TEXT DEFAULT ''"),
        ('oauth_access_token_encrypted', "TEXT DEFAULT ''"),
        ('oauth_access_token_expires_at', "TEXT DEFAULT ''"),
    ]
    changed = False
    for column_name, column_sql in add_columns:
        if column_name in column_names:
            continue
        conn.execute(
            "ALTER TABLE expiry_email_settings ADD COLUMN {} {}".format(column_name, column_sql)
        )
        changed = True
    if changed:
        conn.commit()


def normalize_email_auth_mode(value):
    text = str(value or '').strip().lower()
    if text == EMAIL_AUTH_MICROSOFT_OAUTH2:
        return EMAIL_AUTH_MICROSOFT_OAUTH2
    return EMAIL_AUTH_PASSWORD


def ensure_initial_admin(db_path, base_dir, username='lou'):
    secret, created_secret = ensure_app_secret(base_dir)
    del secret
    conn = connect_db(db_path)
    try:
        existing = conn.execute(
            'SELECT id FROM expiry_users WHERE username=?',
            (username,),
        ).fetchone()
        if existing:
            return {'created': False, 'username': username, 'password': None, 'secret_created': created_secret}
        password = secrets.token_urlsafe(10)
        user_id = gen_id()
        now = utcnow_iso()
        conn.execute(
            '''
            INSERT INTO expiry_users (
                id, username, password_hash, role, status, email, must_change_password, created_at
            ) VALUES (?,?,?,?,?,?,?,?)
            ''',
            (
                user_id,
                username,
                hash_password(password),
                ROLE_ADMIN,
                STATUS_ACTIVE,
                '',
                1,
                now,
            ),
        )
        conn.execute(
            '''
            INSERT INTO expiry_user_settings (user_id, default_notify_offsets, timezone, updated_at)
            VALUES (?,?,?,?)
            ''',
            (user_id, DEFAULT_NOTIFY_OFFSETS, DEFAULT_TIMEZONE, now),
        )
        conn.execute(
            '''
            INSERT INTO expiry_email_settings (
                user_id, smtp_host, smtp_port, smtp_username, smtp_password_encrypted,
                smtp_security, from_email, from_name, enabled, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            ''',
            (user_id, '', 587, '', '', 'starttls', '', '', 0, now),
        )
        conn.commit()
        return {'created': True, 'username': username, 'password': password, 'secret_created': created_secret}
    finally:
        conn.close()


def gen_id():
    return uuid.uuid4().hex[:16]


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def format_date(value):
    if isinstance(value, date):
        return value.isoformat()
    return value or ''


def add_months(source, months):
    month = source.month - 1 + months
    year = source.year + month // 12
    month = month % 12 + 1
    day = min(
        source.day,
        [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1],
    )
    return date(year, month, day)


def advance_due_date(next_due_date, billing_cycle):
    if billing_cycle == 'monthly':
        return add_months(next_due_date, 1)
    if billing_cycle == 'yearly':
        return add_months(next_due_date, 12)
    return next_due_date


def advance_due_date_until_future(next_due_date, billing_cycle, today):
    cursor = next_due_date
    while billing_cycle in ('monthly', 'yearly') and cursor < today:
        cursor = advance_due_date(cursor, billing_cycle)
    return cursor


def normalize_offsets(offsets):
    if isinstance(offsets, list):
        raw_parts = offsets
    else:
        raw_parts = str(offsets or '').replace('，', ',').split(',')
    values = []
    for part in raw_parts:
        text = str(part).strip()
        if not text:
            continue
        if not text.isdigit():
            continue
        num = int(text)
        if num < 0:
            continue
        values.append(num)
    if not values:
        values = [30, 7, 1]
    values = sorted(set(values), reverse=True)
    return ','.join(str(v) for v in values)


def offsets_to_list(offsets):
    return [int(item) for item in normalize_offsets(offsets).split(',')]


def purge_expired_sessions(conn):
    conn.execute('DELETE FROM expiry_sessions WHERE expires_at < ?', (utcnow_iso(),))
    conn.commit()


def create_session(conn, user_id):
    purge_expired_sessions(conn)
    token = secrets.token_hex(24)
    expires_at = (utcnow() + timedelta(days=SESSION_DAYS)).isoformat()
    conn.execute(
        'INSERT INTO expiry_sessions (token, user_id, expires_at, created_at) VALUES (?,?,?,?)',
        (token, user_id, expires_at, utcnow_iso()),
    )
    conn.commit()
    return token, expires_at


def get_token_from_request():
    return request.headers.get('Authorization', '').replace('Bearer ', '').strip()


def resolve_session(conn, token):
    if not token:
        return None
    purge_expired_sessions(conn)
    row = conn.execute(
        '''
        SELECT u.*, s.token, s.expires_at
        FROM expiry_sessions s
        JOIN expiry_users u ON u.id = s.user_id
        WHERE s.token=? AND u.status='active'
        ''',
        (token,),
    ).fetchone()
    return row_to_dict(row)


def require_expiry_auth(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        conn = get_expiry_db()
        user = resolve_session(conn, get_token_from_request())
        if not user:
            return jsonify({'error': '未登录或登录已过期'}), 401
        g.expiry_user = user
        return f(*args, **kwargs)
    return wrapper


def require_admin(f):
    @require_expiry_auth
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        user = g.expiry_user
        if user['role'] != ROLE_ADMIN:
            return jsonify({'error': '无管理员权限'}), 403
        return f(*args, **kwargs)
    return wrapper


def ensure_user_settings(conn, user_id):
    ensure_email_settings_columns(conn)
    now = utcnow_iso()
    conn.execute(
        '''
        INSERT OR IGNORE INTO expiry_user_settings (user_id, default_notify_offsets, timezone, updated_at)
        VALUES (?,?,?,?)
        ''',
        (user_id, DEFAULT_NOTIFY_OFFSETS, DEFAULT_TIMEZONE, now),
    )
    conn.execute(
        '''
        INSERT OR IGNORE INTO expiry_email_settings (
            user_id, smtp_host, smtp_port, smtp_username, smtp_password_encrypted,
            smtp_security, from_email, from_name, enabled, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        ''',
        (user_id, '', 587, '', '', 'starttls', '', '', 0, now),
    )
    conn.commit()


def get_user_settings(conn, user_id):
    ensure_user_settings(conn, user_id)
    settings = conn.execute(
        'SELECT * FROM expiry_user_settings WHERE user_id=?',
        (user_id,),
    ).fetchone()
    return row_to_dict(settings)


def get_email_settings(conn, user_id):
    ensure_user_settings(conn, user_id)
    row = conn.execute(
        'SELECT * FROM expiry_email_settings WHERE user_id=?',
        (user_id,),
    ).fetchone()
    data = row_to_dict(row)
    data['auth_mode'] = normalize_email_auth_mode(data.get('auth_mode'))
    data['smtp_password_configured'] = bool(data.get('smtp_password_encrypted'))
    data['oauth_client_secret_configured'] = bool(data.get('oauth_client_secret_encrypted'))
    data['oauth_refresh_token_configured'] = bool(data.get('oauth_refresh_token_encrypted'))
    data['oauth_access_token_cached'] = bool(data.get('oauth_access_token_encrypted'))
    data.pop('smtp_password_encrypted', None)
    data.pop('oauth_client_secret_encrypted', None)
    data.pop('oauth_refresh_token_encrypted', None)
    data.pop('oauth_access_token_encrypted', None)
    return data


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def validate_resource_payload(data, user_settings):
    name = str(data.get('name', '')).strip()
    if not name:
        return None, '资源名称不能为空'
    resource_type = str(data.get('resource_type', '')).strip() or 'subscription'
    if resource_type not in ('subscription', 'one_time'):
        return None, '资源类型无效'
    billing_cycle = str(data.get('billing_cycle', '')).strip() or 'monthly'
    if resource_type == 'one_time':
        billing_cycle = 'none'
    if billing_cycle not in ('monthly', 'yearly', 'none'):
        return None, '计费周期无效'
    if resource_type == 'subscription' and billing_cycle == 'none':
        return None, '订阅资源必须选择月付或年付'
    try:
        amount = round(float(data.get('amount', 0)), 2)
    except (TypeError, ValueError):
        return None, '金额格式无效'
    if amount <= 0:
        return None, '金额必须大于 0'
    start_date = str(data.get('start_date', '')).strip()
    next_due_date = str(data.get('next_due_date', '')).strip()
    if start_date and not parse_date(start_date):
        return None, '开始日期格式错误'
    if not next_due_date or not parse_date(next_due_date):
        return None, '下次到期日格式错误'
    notify_offsets = normalize_offsets(data.get('notify_offsets') or user_settings.get('default_notify_offsets'))
    payload = {
        'name': name,
        'provider': str(data.get('provider', '')).strip(),
        'category': str(data.get('category', '')).strip() or '未分类',
        'resource_type': resource_type,
        'billing_cycle': billing_cycle,
        'amount': amount,
        'currency': 'CNY',
        'start_date': start_date,
        'next_due_date': next_due_date,
        'auto_renew': 1 if parse_bool(data.get('auto_renew')) else 0,
        'manual_status': RESOURCE_ACTIVE if str(data.get('manual_status', RESOURCE_ACTIVE)).strip() != RESOURCE_STOPPED else RESOURCE_STOPPED,
        'notify_offsets': notify_offsets,
        'note': str(data.get('note', '')).strip(),
    }
    return payload, None


def resource_effective_offsets(row, user_settings):
    return normalize_offsets(row.get('notify_offsets') or user_settings.get('default_notify_offsets'))


def compute_resource_state(row, user_settings, today=None):
    today = today or local_today(user_settings.get('timezone') or DEFAULT_TIMEZONE)
    due = parse_date(row['next_due_date'])
    offsets = offsets_to_list(resource_effective_offsets(row, user_settings))
    max_offset = max(offsets) if offsets else 0
    state = 'active'
    if row['manual_status'] == RESOURCE_STOPPED:
        state = 'stopped'
    elif due and due < today:
        state = 'expired'
    elif due and (due - today).days <= max_offset:
        state = 'upcoming'
    days_left = None if not due else (due - today).days
    return {
        'state': state,
        'days_left': days_left,
        'effective_notify_offsets': offsets,
    }


def serialize_resource(row, user_settings, today=None):
    item = row_to_dict(row) if not isinstance(row, dict) else dict(row)
    derived = compute_resource_state(item, user_settings, today)
    item.update(derived)
    item['auto_renew'] = bool(item['auto_renew'])
    item['amount'] = round(float(item['amount']), 2)
    return item


def advance_auto_renew_resources(conn, user_id=None, timezone_name=DEFAULT_TIMEZONE):
    today = local_today(timezone_name)
    params = []
    sql = '''
        SELECT * FROM expiry_resources
        WHERE resource_type='subscription'
          AND auto_renew=1
          AND manual_status='active'
          AND billing_cycle IN ('monthly','yearly')
    '''
    if user_id:
        sql += ' AND user_id=?'
        params.append(user_id)
    rows = conn.execute(sql, params).fetchall()
    changed = 0
    for row in rows:
        due = parse_date(row['next_due_date'])
        if not due or due >= today:
            continue
        new_due = advance_due_date_until_future(due, row['billing_cycle'], today)
        if new_due != due:
            conn.execute(
                'UPDATE expiry_resources SET next_due_date=?, updated_at=? WHERE id=?',
                (new_due.isoformat(), utcnow_iso(), row['id']),
            )
            changed += 1
    if changed:
        conn.commit()
    return changed


def get_resources(conn, user_id, filters=None):
    filters = filters or {}
    advance_auto_renew_resources(conn, user_id, filters.get('timezone') or DEFAULT_TIMEZONE)
    sql = 'SELECT * FROM expiry_resources WHERE user_id=?'
    params = [user_id]
    search = str(filters.get('search', '')).strip()
    if search:
        sql += ' AND (name LIKE ? OR provider LIKE ? OR category LIKE ?)'
        like = '%{}%'.format(search)
        params.extend([like, like, like])
    cycle = str(filters.get('billing_cycle', '')).strip()
    if cycle in ('monthly', 'yearly', 'none'):
        sql += ' AND billing_cycle=?'
        params.append(cycle)
    category = str(filters.get('category', '')).strip()
    if category:
        sql += ' AND category=?'
        params.append(category)
    status_filter = str(filters.get('status', '')).strip()
    sql += ' ORDER BY next_due_date ASC, created_at DESC'
    rows = conn.execute(sql, params).fetchall()
    user_settings = filters.get('user_settings') or get_user_settings(conn, user_id)
    today = local_today(user_settings.get('timezone') or DEFAULT_TIMEZONE)
    items = [serialize_resource(row, user_settings, today) for row in rows]
    if status_filter:
        items = [item for item in items if item['state'] == status_filter]
    return items


def get_resource(conn, user_id, resource_id):
    row = conn.execute(
        'SELECT * FROM expiry_resources WHERE id=? AND user_id=?',
        (resource_id, user_id),
    ).fetchone()
    if not row:
        return None
    settings = get_user_settings(conn, user_id)
    return serialize_resource(row, settings)


def monthly_yearly_projection(resource, year):
    due_date = parse_date(resource['next_due_date'])
    months = [0.0] * 12
    if resource['manual_status'] != RESOURCE_ACTIVE:
        return months
    amount = float(resource['amount'])
    if resource['billing_cycle'] == 'monthly':
        for idx in range(12):
            months[idx] += amount
    elif resource['billing_cycle'] == 'yearly':
        if due_date:
            months[due_date.month - 1] += amount
    elif resource['billing_cycle'] == 'none' and due_date and due_date.year == year:
        months[due_date.month - 1] += amount
    return months


def build_stats(resources, year, today):
    month_totals = [0.0] * 12
    category_totals = {}
    for item in resources:
        projected = monthly_yearly_projection(item, year)
        month_totals = [round(a + b, 2) for a, b in zip(month_totals, projected)]
        total_amount = sum(projected)
        if total_amount > 0:
            category_totals[item['category']] = round(category_totals.get(item['category'], 0) + total_amount, 2)
    current_month_index = today.month - 1
    current_month_spend = month_totals[current_month_index]
    yearly_spend = round(sum(month_totals), 2)
    return {
        'year': year,
        'month_breakdown': month_totals,
        'category_breakdown': [
            {'category': key, 'amount': value}
            for key, value in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        ],
        'current_month_spend': round(current_month_spend, 2),
        'yearly_spend': yearly_spend,
    }


def build_dashboard(conn, user_id):
    settings = get_user_settings(conn, user_id)
    resources = get_resources(conn, user_id, {'user_settings': settings, 'timezone': settings.get('timezone')})
    today = local_today(settings.get('timezone') or DEFAULT_TIMEZONE)
    stats = build_stats(resources, today.year, today)
    due_soon = [item for item in resources if item['state'] == 'upcoming' and item['days_left'] is not None and item['days_left'] <= 7]
    notifications = conn.execute(
        '''
        SELECT n.*, r.name AS resource_name, r.provider AS provider
        FROM expiry_notifications n
        JOIN expiry_resources r ON r.id = n.resource_id
        WHERE n.user_id=? AND n.channel='site' AND n.status IN ('pending','read')
        ORDER BY n.scheduled_for ASC, n.created_at DESC
        LIMIT 8
        ''',
        (user_id,),
    ).fetchall()
    unread_count = conn.execute(
        '''
        SELECT COUNT(*) AS c FROM expiry_notifications
        WHERE user_id=? AND channel='site' AND status='pending'
        ''',
        (user_id,),
    ).fetchone()['c']
    return {
        'summary': {
            'active_count': len([item for item in resources if item['manual_status'] == RESOURCE_ACTIVE]),
            'stopped_count': len([item for item in resources if item['manual_status'] == RESOURCE_STOPPED]),
            'due_soon_count': len(due_soon),
            'current_month_spend': stats['current_month_spend'],
            'yearly_spend': stats['yearly_spend'],
            'unread_notifications': unread_count,
        },
        'stats': stats,
        'upcoming': due_soon[:6],
        'notifications': [row_to_dict(row) for row in notifications],
        'resources': resources,
    }


def update_email_settings(conn, user_id, data, base_dir):
    ensure_user_settings(conn, user_id)
    secret, _ = ensure_app_secret(base_dir)
    password = str(data.get('smtp_password', '')).strip()
    oauth_client_secret = str(data.get('oauth_client_secret', '')).strip()
    oauth_refresh_token = str(data.get('oauth_refresh_token', '')).strip()
    try:
        smtp_port = int(data.get('smtp_port', 587) or 587)
    except (TypeError, ValueError):
        raise ValueError('SMTP 端口格式无效')
    existing = conn.execute(
        '''
        SELECT
            smtp_password_encrypted,
            oauth_tenant_id,
            oauth_client_id,
            oauth_client_secret_encrypted,
            oauth_refresh_token_encrypted,
            oauth_access_token_encrypted,
            oauth_access_token_expires_at,
            auth_mode
        FROM expiry_email_settings
        WHERE user_id=?
        ''',
        (user_id,),
    ).fetchone()
    encrypted = existing['smtp_password_encrypted'] if existing else ''
    oauth_client_secret_encrypted = existing['oauth_client_secret_encrypted'] if existing else ''
    oauth_refresh_token_encrypted = existing['oauth_refresh_token_encrypted'] if existing else ''
    oauth_access_token_encrypted = existing['oauth_access_token_encrypted'] if existing else ''
    oauth_access_token_expires_at = existing['oauth_access_token_expires_at'] if existing else ''
    previous_auth_mode = normalize_email_auth_mode(existing['auth_mode'] if existing else EMAIL_AUTH_PASSWORD)
    previous_oauth_tenant_id = str(existing['oauth_tenant_id'] if existing else '').strip()
    previous_oauth_client_id = str(existing['oauth_client_id'] if existing else '').strip()
    if password:
        encrypted = encrypt_secret(password, secret)
    if oauth_client_secret:
        oauth_client_secret_encrypted = encrypt_secret(oauth_client_secret, secret)
    if oauth_refresh_token:
        oauth_refresh_token_encrypted = encrypt_secret(oauth_refresh_token, secret)
    enabled = 1 if parse_bool(data.get('enabled')) else 0
    smtp_security = str(data.get('smtp_security', 'starttls')).strip().lower()
    if smtp_security not in ('ssl', 'starttls', 'none'):
        smtp_security = 'starttls'
    auth_mode = normalize_email_auth_mode(data.get('auth_mode', previous_auth_mode))
    oauth_tenant_id = str(data.get('oauth_tenant_id', previous_oauth_tenant_id)).strip()
    oauth_client_id = str(data.get('oauth_client_id', previous_oauth_client_id)).strip()
    oauth_credentials_changed = bool(oauth_client_secret or oauth_refresh_token)
    oauth_identity_changed = (
        oauth_tenant_id != previous_oauth_tenant_id
        or oauth_client_id != previous_oauth_client_id
    )
    if auth_mode != previous_auth_mode or oauth_credentials_changed or oauth_identity_changed:
        oauth_access_token_encrypted = ''
        oauth_access_token_expires_at = ''
    conn.execute(
        '''
        UPDATE expiry_email_settings
        SET smtp_host=?, smtp_port=?, smtp_username=?, smtp_password_encrypted=?,
            smtp_security=?, from_email=?, from_name=?, auth_mode=?,
            oauth_tenant_id=?, oauth_client_id=?, oauth_client_secret_encrypted=?,
            oauth_refresh_token_encrypted=?, oauth_access_token_encrypted=?, oauth_access_token_expires_at=?,
            enabled=?, updated_at=?
        WHERE user_id=?
        ''',
        (
            str(data.get('smtp_host', '')).strip(),
            smtp_port,
            str(data.get('smtp_username', '')).strip(),
            encrypted,
            smtp_security,
            str(data.get('from_email', '')).strip(),
            str(data.get('from_name', '')).strip(),
            auth_mode,
            oauth_tenant_id,
            oauth_client_id,
            oauth_client_secret_encrypted,
            oauth_refresh_token_encrypted,
            oauth_access_token_encrypted,
            oauth_access_token_expires_at,
            enabled,
            utcnow_iso(),
            user_id,
        ),
    )
    conn.commit()


def get_smtp_password(db_row, base_dir):
    secret, _ = ensure_app_secret(base_dir)
    return decrypt_secret(db_row.get('smtp_password_encrypted', ''), secret)


def parse_iso_datetime(value):
    text = str(value or '').strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def refresh_microsoft_oauth_token(conn, settings_row, base_dir):
    auth_mode = normalize_email_auth_mode(settings_row.get('auth_mode'))
    if auth_mode != EMAIL_AUTH_MICROSOFT_OAUTH2:
        raise ValueError('当前认证模式不是 Microsoft OAuth2')
    tenant_id = str(settings_row.get('oauth_tenant_id', '')).strip()
    client_id = str(settings_row.get('oauth_client_id', '')).strip()
    if not tenant_id or not client_id:
        raise ValueError('请先配置 OAuth2 Tenant ID 与 Client ID')
    secret, _ = ensure_app_secret(base_dir)
    client_secret = decrypt_secret(settings_row.get('oauth_client_secret_encrypted', ''), secret)
    refresh_token = decrypt_secret(settings_row.get('oauth_refresh_token_encrypted', ''), secret)
    if not client_secret:
        raise ValueError('请先配置 OAuth2 Client Secret')
    if not refresh_token:
        raise ValueError('请先配置 OAuth2 Refresh Token')
    token_url = 'https://login.microsoftonline.com/{}/oauth2/v2.0/token'.format(tenant_id)
    payload = urllib.parse.urlencode(
        {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
            'scope': MICROSOFT_OAUTH_SCOPE,
        }
    ).encode('utf-8')
    req = urllib.request.Request(
        token_url,
        data=payload,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        message = body
        try:
            parsed = json.loads(body)
            message = parsed.get('error_description') or parsed.get('error') or body
        except Exception:
            pass
        raise ValueError('OAuth2 刷新失败: {}'.format(message))
    except Exception as exc:
        raise ValueError('OAuth2 刷新失败: {}'.format(exc))
    try:
        token_data = json.loads(body)
    except Exception:
        raise ValueError('OAuth2 响应解析失败')
    access_token = str(token_data.get('access_token', '')).strip()
    if not access_token:
        raise ValueError('OAuth2 响应缺少 access_token')
    new_refresh_token = str(token_data.get('refresh_token', '')).strip() or refresh_token
    expires_in = token_data.get('expires_in', 3600)
    try:
        expires_in = int(expires_in)
    except (TypeError, ValueError):
        expires_in = 3600
    expires_at = (utcnow() + timedelta(seconds=max(60, expires_in - 60))).isoformat()
    conn.execute(
        '''
        UPDATE expiry_email_settings
        SET oauth_refresh_token_encrypted=?, oauth_access_token_encrypted=?, oauth_access_token_expires_at=?, updated_at=?
        WHERE user_id=?
        ''',
        (
            encrypt_secret(new_refresh_token, secret),
            encrypt_secret(access_token, secret),
            expires_at,
            utcnow_iso(),
            settings_row['user_id'],
        ),
    )
    conn.commit()
    return access_token


def get_email_delivery_auth(conn, settings_row, base_dir):
    auth_mode = normalize_email_auth_mode(settings_row.get('auth_mode'))
    if auth_mode == EMAIL_AUTH_MICROSOFT_OAUTH2:
        secret, _ = ensure_app_secret(base_dir)
        access_token = decrypt_secret(settings_row.get('oauth_access_token_encrypted', ''), secret)
        expires_at = parse_iso_datetime(settings_row.get('oauth_access_token_expires_at', ''))
        if not access_token or not expires_at or expires_at <= (utcnow() + timedelta(seconds=120)):
            access_token = refresh_microsoft_oauth_token(conn, settings_row, base_dir)
        return {
            'auth_mode': EMAIL_AUTH_MICROSOFT_OAUTH2,
            'oauth_access_token': access_token,
            'smtp_password': '',
        }
    return {
        'auth_mode': EMAIL_AUTH_PASSWORD,
        'oauth_access_token': '',
        'smtp_password': get_smtp_password(settings_row, base_dir),
    }


def notification_message(resource, days_left):
    if days_left < 0:
        return '【续费雷达】{} 已在 {} 过期，请及时处理。'.format(resource['name'], resource['next_due_date'])
    if days_left == 0:
        return '【续费雷达】{} 今天到期，请留意续费。'.format(resource['name'])
    return '【续费雷达】{} 将在 {} 天后到期（{}）。'.format(resource['name'], days_left, resource['next_due_date'])


def create_notification(conn, user_id, resource_id, channel, scheduled_for, message, dedupe_key, status='pending', error_message=''):
    existing = conn.execute(
        'SELECT id FROM expiry_notifications WHERE dedupe_key=?',
        (dedupe_key,),
    ).fetchone()
    if existing:
        return False
    now = utcnow_iso()
    conn.execute(
        '''
        INSERT INTO expiry_notifications (
            id, user_id, resource_id, channel, scheduled_for, sent_at, read_at,
            status, message, dedupe_key, error_message, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ''',
        (
            gen_id(),
            user_id,
            resource_id,
            channel,
            scheduled_for,
            now if status == 'sent' else None,
            now if status == 'read' else None,
            status,
            message,
            dedupe_key,
            error_message,
            now,
        ),
    )
    conn.commit()
    return True


def list_notifications(conn, user_id):
    rows = conn.execute(
        '''
        SELECT n.*, r.name AS resource_name, r.provider AS provider, r.next_due_date
        FROM expiry_notifications n
        JOIN expiry_resources r ON r.id = n.resource_id
        WHERE n.user_id=?
        ORDER BY n.created_at DESC
        ''',
        (user_id,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def mark_notification_read(conn, user_id, notification_id):
    row = conn.execute(
        '''
        SELECT * FROM expiry_notifications
        WHERE id=? AND user_id=? AND channel='site'
        ''',
        (notification_id, user_id),
    ).fetchone()
    if not row:
        return False
    conn.execute(
        'UPDATE expiry_notifications SET status=?, read_at=? WHERE id=?',
        ('read', utcnow_iso(), notification_id),
    )
    conn.commit()
    return True
