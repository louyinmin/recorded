"""Services for WeChat Mini Program code exchange and local user records."""

import functools
import hashlib
import json
import re
import secrets
import sqlite3
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta

from flask import current_app, g, jsonify, request


WECHAT_CODE2SESSION_URL = 'https://api.weixin.qq.com/sns/jscode2session'
DEFAULT_TIMEOUT = 10
SESSION_DAYS = 30
NBA_APP = 'nba'
TIMING_PROJECT = 'timing'
WECHAT_PROJECTS = {NBA_APP, TIMING_PROJECT}
DEFAULT_NBA_USER_CONFIG = {
    'associated_home_player_pid': [],
    'current_home_player_pid': None,
    'current_home_card_id': None,
    'home_player_card_selection': {},
    'search_default_player_pid': [],
}
TIMING_DEFAULT_TASK_DURATIONS = {
    'look_far': 300,
    'homework': 1800,
    'watch_tv': 1200,
    'play_game': 1800,
}
TIMING_TASK_TYPES = {'study', 'relax', 'rest'}
TIMING_CONFIG_TASK_TYPES = {'regular', 'special'}


class WeChatCodeExchangeError(Exception):
    def __init__(self, errcode, message='wechat code2Session failed'):
        super().__init__(message)
        self.errcode = errcode


class WeChatUpstreamError(Exception):
    pass


def utcnow_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat()


def utcnow():
    return datetime.utcnow().replace(microsecond=0)


def gen_user_id():
    return 'wx_' + uuid.uuid4().hex[:24]


def gen_config_id(prefix='cfg'):
    return prefix + '_' + uuid.uuid4().hex[:24]


def gen_plan_id():
    return 'plan_' + uuid.uuid4().hex[:16]


def gen_task_id():
    return 'task_' + uuid.uuid4().hex[:16]


def hash_session_token(token):
    return hashlib.sha256(str(token or '').encode('utf-8')).hexdigest()


def connect_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def get_wechat_db():
    if 'wechat_db' not in g:
        g.wechat_db = connect_db(current_app.config['WECHAT_DB_PATH'])
    return g.wechat_db


def close_wechat_db(exc=None):
    db = g.pop('wechat_db', None)
    if db is not None:
        db.close()


def has_column(conn, table_name, column_name):
    rows = conn.execute("PRAGMA table_info({})".format(table_name)).fetchall()
    return any(row['name'] == column_name for row in rows)


def table_sql(conn, table_name):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return (row['sql'] or '') if row else ''


def migrate_wechat_users_schema(conn):
    sql = table_sql(conn, 'wechat_users')
    needs_project = not has_column(conn, 'wechat_users', 'project')
    needs_unique_rebuild = 'wechat_openid TEXT UNIQUE NOT NULL' in sql
    if not needs_project and not needs_unique_rebuild:
        return

    foreign_keys = conn.execute('PRAGMA foreign_keys').fetchone()[0]
    conn.commit()
    conn.execute('PRAGMA foreign_keys=OFF')
    try:
        conn.execute('DROP TABLE IF EXISTS wechat_users_new')
        conn.execute(
            '''
            CREATE TABLE wechat_users_new (
                id TEXT PRIMARY KEY,
                project TEXT NOT NULL DEFAULT '',
                wechat_openid TEXT NOT NULL,
                wechat_unionid TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT NOT NULL,
                UNIQUE (project, wechat_openid)
            )
            '''
        )
        project_expr = 'COALESCE(NULLIF(project, \'\'), ?)' if has_column(conn, 'wechat_users', 'project') else '?'
        conn.execute(
            '''
            INSERT OR IGNORE INTO wechat_users_new (
                id, project, wechat_openid, wechat_unionid, created_at, updated_at, last_login_at
            )
            SELECT id, {project_expr}, wechat_openid, wechat_unionid, created_at, updated_at, last_login_at
            FROM wechat_users
            ORDER BY created_at
            '''.format(project_expr=project_expr),
            (NBA_APP,),
        )
        conn.execute('DROP TABLE wechat_users')
        conn.execute('ALTER TABLE wechat_users_new RENAME TO wechat_users')
        conn.commit()
    finally:
        if foreign_keys:
            conn.execute('PRAGMA foreign_keys=ON')


def init_wechat_db(db_path):
    conn = connect_db(db_path)
    try:
        conn.executescript(
            '''
            CREATE TABLE IF NOT EXISTS wechat_users (
                id TEXT PRIMARY KEY,
                project TEXT NOT NULL DEFAULT '',
                wechat_openid TEXT NOT NULL,
                wechat_unionid TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT NOT NULL,
                UNIQUE (project, wechat_openid)
            );

            CREATE INDEX IF NOT EXISTS idx_wechat_users_unionid ON wechat_users(wechat_unionid);

            CREATE TABLE IF NOT EXISTS wechat_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                app TEXT NOT NULL DEFAULT '',
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_seen_at TEXT,
                FOREIGN KEY (user_id) REFERENCES wechat_users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_wechat_sessions_user_id ON wechat_sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_wechat_sessions_expires_at ON wechat_sessions(expires_at);

            CREATE TABLE IF NOT EXISTS user_configs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                app TEXT NOT NULL,
                config_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES wechat_users(id) ON DELETE CASCADE,
                UNIQUE (user_id, app)
            );

            CREATE TABLE IF NOT EXISTS timing_plan_configs (
                id TEXT PRIMARY KEY,
                project TEXT NOT NULL,
                user_id TEXT NOT NULL,
                wechat_openid TEXT NOT NULL DEFAULT '',
                plan_config_json TEXT NOT NULL DEFAULT '{}',
                version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                FOREIGN KEY (user_id) REFERENCES wechat_users(id) ON DELETE CASCADE,
                UNIQUE (project, user_id)
            );

            CREATE TABLE IF NOT EXISTS timing_task_configs (
                id TEXT PRIMARY KEY,
                project TEXT NOT NULL,
                user_id TEXT NOT NULL,
                wechat_openid TEXT NOT NULL DEFAULT '',
                task_config_json TEXT NOT NULL DEFAULT '{}',
                version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                FOREIGN KEY (user_id) REFERENCES wechat_users(id) ON DELETE CASCADE,
                UNIQUE (project, user_id)
            );

            CREATE TABLE IF NOT EXISTS timing_stat_records (
                id TEXT PRIMARY KEY,
                project TEXT NOT NULL,
                user_id TEXT NOT NULL,
                wechat_openid TEXT NOT NULL DEFAULT '',
                record_date TEXT NOT NULL,
                stats_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                FOREIGN KEY (user_id) REFERENCES wechat_users(id) ON DELETE CASCADE,
                UNIQUE (project, user_id, record_date)
            );
            '''
        )
        migrate_wechat_users_schema(conn)
        conn.execute('CREATE INDEX IF NOT EXISTS idx_wechat_users_unionid ON wechat_users(wechat_unionid)')
        conn.commit()
    finally:
        conn.close()


def exchange_wechat_code(appid, secret, code, timeout=DEFAULT_TIMEOUT):
    query = urllib.parse.urlencode({
        'appid': appid,
        'secret': secret,
        'js_code': code,
        'grant_type': 'authorization_code',
    })
    request = urllib.request.Request(
        WECHAT_CODE2SESSION_URL + '?' + query,
        headers={'User-Agent': 'recorded-wechat-session/1.0'},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or 'utf-8'
            payload = response.read().decode(charset)
    except Exception as exc:
        raise WeChatUpstreamError('wechat code2Session request failed') from exc
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise WeChatUpstreamError('wechat code2Session returned invalid JSON') from exc
    if data.get('errcode'):
        raise WeChatCodeExchangeError(data.get('errcode'))
    if not data.get('openid'):
        raise WeChatUpstreamError('wechat code2Session response missing openid')
    return data


def find_or_create_user(conn, project, openid, unionid=''):
    now = utcnow_iso()
    row = conn.execute(
        'SELECT * FROM wechat_users WHERE project=? AND wechat_openid=?',
        (project, openid),
    ).fetchone()
    if row:
        conn.execute(
            '''
            UPDATE wechat_users
            SET wechat_unionid=COALESCE(NULLIF(?, ''), wechat_unionid),
                updated_at=?,
                last_login_at=?
            WHERE id=?
            ''',
            (unionid or '', now, now, row['id']),
        )
        conn.commit()
        return conn.execute('SELECT * FROM wechat_users WHERE id=?', (row['id'],)).fetchone()

    user_id = gen_user_id()
    conn.execute(
        '''
        INSERT INTO wechat_users (
            id, project, wechat_openid, wechat_unionid, created_at, updated_at, last_login_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        (user_id, project, openid, unionid or None, now, now, now),
    )
    conn.commit()
    return conn.execute('SELECT * FROM wechat_users WHERE id=?', (user_id,)).fetchone()


def purge_expired_sessions(conn):
    conn.execute('DELETE FROM wechat_sessions WHERE expires_at < ?', (utcnow_iso(),))
    conn.commit()


def create_session(conn, user_id, app=''):
    purge_expired_sessions(conn)
    token = secrets.token_urlsafe(32)
    now = utcnow()
    expires_at = now + timedelta(days=SESSION_DAYS)
    conn.execute(
        '''
        INSERT INTO wechat_sessions (token_hash, user_id, app, expires_at, created_at)
        VALUES (?,?,?,?,?)
        ''',
        (hash_session_token(token), user_id, str(app or '').strip(), expires_at.isoformat(), now.isoformat()),
    )
    conn.commit()
    return token, expires_at.isoformat()


def get_token_from_request():
    auth = request.headers.get('Authorization', '')
    if auth.lower().startswith('bearer '):
        return auth[7:].strip()
    return ''


def resolve_session(conn, token):
    token = str(token or '').strip()
    if not token:
        return None
    purge_expired_sessions(conn)
    row = conn.execute(
        '''
        SELECT u.*, s.app AS session_app, s.expires_at AS session_expires_at
        FROM wechat_sessions s
        JOIN wechat_users u ON u.id = s.user_id
        WHERE s.token_hash=?
        ''',
        (hash_session_token(token),),
    ).fetchone()
    if not row:
        return None
    conn.execute(
        'UPDATE wechat_sessions SET last_seen_at=? WHERE token_hash=?',
        (utcnow_iso(), hash_session_token(token)),
    )
    conn.commit()
    return dict(row)


def require_wechat_auth(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        user = resolve_session(get_wechat_db(), get_token_from_request())
        if not user:
            return jsonify({'message': 'unauthorized'}), 401
        g.wechat_user = user
        return func(*args, **kwargs)
    return wrapped


def require_wechat_project(project):
    def decorator(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            user = resolve_session(get_wechat_db(), get_token_from_request())
            if not user or user.get('session_app') != project:
                return jsonify({'message': 'unauthorized'}), 401
            g.wechat_user = user
            return func(*args, **kwargs)
        return wrapped
    return decorator


def user_session_payload(user, app='', session_token='', expires_at=''):
    payload = {
        'userId': user['id'],
        'openid': user['wechat_openid'],
    }
    if user['wechat_unionid']:
        payload['unionid'] = user['wechat_unionid']
    if app:
        payload['app'] = app
    if session_token:
        payload['sessionToken'] = session_token
        payload['expiresAt'] = expires_at
    return payload


def load_json_object(raw, default_value):
    try:
        value = json.loads(raw or '{}')
    except (TypeError, json.JSONDecodeError):
        return dict(default_value)
    if not isinstance(value, dict):
        return dict(default_value)
    return value


def normalize_nba_player_pid(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError('invalid nba player pid')
    return value.strip() or None


def normalize_nba_player_pid_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        pid = value.strip()
        return [pid] if pid else []
    if not isinstance(value, list):
        raise ValueError('invalid nba player pid list')
    seen = set()
    players = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError('invalid nba player pid list')
        pid = item.strip()
        if pid and pid not in seen:
            seen.add(pid)
            players.append(pid)
    return players


def normalize_nba_card_id(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError('invalid nba card id')
    return value.strip() or None


def normalize_nba_player_card_selection(value):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError('invalid nba player card selection')
    result = {}
    for raw_pid, raw_card_id in value.items():
        if not isinstance(raw_pid, str) or not isinstance(raw_card_id, str):
            raise ValueError('invalid nba player card selection')
        pid = raw_pid.strip()
        card_id = raw_card_id.strip()
        if not pid or not card_id:
            raise ValueError('invalid nba player card selection')
        result[pid] = card_id
    return result


def normalize_nba_user_config(config, strict_unknown=True):
    result = dict(DEFAULT_NBA_USER_CONFIG)
    if not isinstance(config, dict):
        raise ValueError('invalid nba user config')
    if strict_unknown:
        unknown = set(config.keys()) - set(DEFAULT_NBA_USER_CONFIG.keys())
        if unknown:
            raise ValueError('unknown nba user config field')
    if 'associated_home_player_pid' in config:
        result['associated_home_player_pid'] = normalize_nba_player_pid_list(
            config.get('associated_home_player_pid')
        )
    if 'current_home_player_pid' in config:
        result['current_home_player_pid'] = normalize_nba_player_pid(
            config.get('current_home_player_pid')
        )
    if 'current_home_card_id' in config:
        result['current_home_card_id'] = normalize_nba_card_id(
            config.get('current_home_card_id')
        )
    if 'home_player_card_selection' in config:
        result['home_player_card_selection'] = normalize_nba_player_card_selection(
            config.get('home_player_card_selection')
        )
    if 'search_default_player_pid' in config:
        result['search_default_player_pid'] = normalize_nba_player_pid_list(
            config.get('search_default_player_pid')
        )
    return result


def get_nba_user_config(conn, user_id):
    row = conn.execute(
        '''
        SELECT * FROM user_configs
        WHERE user_id=? AND app=?
        ''',
        (user_id, NBA_APP),
    ).fetchone()
    if not row:
        return dict(DEFAULT_NBA_USER_CONFIG), None
    saved = load_json_object(row['config_json'], DEFAULT_NBA_USER_CONFIG)
    config = dict(DEFAULT_NBA_USER_CONFIG)
    config.update(normalize_nba_user_config({
        key: saved[key]
        for key in saved
        if key in DEFAULT_NBA_USER_CONFIG
    }, strict_unknown=False))
    return config, row['updated_at']


def patch_nba_user_config(conn, user_id, patch):
    if not isinstance(patch, dict):
        raise ValueError('invalid nba user config')
    current_config, _ = get_nba_user_config(conn, user_id)
    normalized_patch = normalize_nba_user_config(patch)
    for key in patch:
        current_config[key] = normalized_patch[key]
    now = utcnow_iso()
    conn.execute(
        '''
        INSERT INTO user_configs (id, user_id, app, config_json, created_at, updated_at)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(user_id, app) DO UPDATE SET
            config_json=excluded.config_json,
            updated_at=excluded.updated_at
        ''',
        (
            gen_config_id('ucfg'),
            user_id,
            NBA_APP,
            json.dumps(current_config, ensure_ascii=False, separators=(',', ':')),
            now,
            now,
        ),
    )
    conn.commit()
    return current_config, now


def timing_default_config():
    return {
        'defaultTaskDurations': dict(TIMING_DEFAULT_TASK_DURATIONS),
        'customPlans': [],
    }


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validate_duration_seconds(value):
    if not is_int(value) or value < 60 or value > 10800:
        raise ValueError('invalid timing plan config')
    return value


def normalize_timing_plan(plan, now, existing=None, assign_id=False, order_fallback=0):
    existing = existing or {}
    name = plan.get('name', existing.get('name', ''))
    name = str(name or '').strip()
    if not name or len(name) > 20:
        raise ValueError('invalid timing plan config')

    duration = validate_duration_seconds(plan.get('durationSeconds', existing.get('durationSeconds')))
    task_type = str(plan.get('taskType', existing.get('taskType', ''))).strip()
    if task_type not in TIMING_TASK_TYPES:
        raise ValueError('invalid timing plan config')

    order = plan.get('order', existing.get('order', order_fallback))
    if not is_int(order) or order < 0:
        raise ValueError('invalid timing plan config')

    enabled = plan.get('enabled', existing.get('enabled', True))
    if not isinstance(enabled, bool):
        raise ValueError('invalid timing plan config')

    plan_id = str(plan.get('id') or existing.get('id') or '').strip()
    if not plan_id and assign_id:
        plan_id = gen_plan_id()
    if not plan_id:
        raise ValueError('invalid timing plan config')

    created_at = str(existing.get('createdAt') or plan.get('createdAt') or now)
    updated_at = str(plan.get('updatedAt') or existing.get('updatedAt') or now)
    return {
        'id': plan_id,
        'name': name,
        'durationSeconds': duration,
        'taskType': task_type,
        'order': order,
        'enabled': enabled,
        'createdAt': created_at,
        'updatedAt': updated_at,
    }


def normalize_timing_config(config, now):
    if not isinstance(config, dict):
        raise ValueError('invalid timing plan config')
    result = timing_default_config()
    durations = config.get('defaultTaskDurations', result['defaultTaskDurations'])
    if not isinstance(durations, dict):
        raise ValueError('invalid timing plan config')
    unknown_keys = set(durations.keys()) - set(TIMING_DEFAULT_TASK_DURATIONS.keys())
    if unknown_keys:
        raise ValueError('invalid timing plan config')
    for key, value in durations.items():
        result['defaultTaskDurations'][key] = validate_duration_seconds(value)

    custom_plans = config.get('customPlans', [])
    if not isinstance(custom_plans, list):
        raise ValueError('invalid timing plan config')
    normalized_plans = []
    seen_ids = set()
    for index, plan in enumerate(custom_plans):
        if not isinstance(plan, dict):
            raise ValueError('invalid timing plan config')
        normalized = normalize_timing_plan(plan, now, assign_id=True, order_fallback=index)
        if normalized['id'] in seen_ids:
            raise ValueError('invalid timing plan config')
        seen_ids.add(normalized['id'])
        normalized_plans.append(normalized)
    result['customPlans'] = sorted(normalized_plans, key=lambda item: item['order'])
    return result


def get_timing_plan_row(conn, user_id):
    return conn.execute(
        '''
        SELECT * FROM timing_plan_configs
        WHERE project=? AND user_id=? AND deleted_at IS NULL
        ''',
        (TIMING_PROJECT, user_id),
    ).fetchone()


def get_timing_plan_config(conn, user):
    row = get_timing_plan_row(conn, user['id'])
    if not row:
        return timing_default_config(), 0, None
    config = load_json_object(row['plan_config_json'], timing_default_config())
    return normalize_timing_config(config, row['updated_at']), int(row['version']), row['updated_at']


def assert_timing_version(row, requested_version):
    if requested_version is None:
        return
    if not is_int(requested_version):
        raise ValueError('invalid timing plan config')
    current_version = int(row['version']) if row else 0
    if requested_version != current_version:
        raise RuntimeError(current_version)


def save_timing_plan_config(conn, user, config, current_row=None):
    current_version = int(current_row['version']) if current_row else 0
    next_version = current_version + 1
    now = utcnow_iso()
    normalized = normalize_timing_config(config, now)
    conn.execute(
        '''
        INSERT INTO timing_plan_configs (
            id, project, user_id, wechat_openid, plan_config_json, version, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(project, user_id) DO UPDATE SET
            wechat_openid=excluded.wechat_openid,
            plan_config_json=excluded.plan_config_json,
            version=excluded.version,
            updated_at=excluded.updated_at,
            deleted_at=NULL
        ''',
        (
            gen_config_id('tpcfg'),
            TIMING_PROJECT,
            user['id'],
            user['wechat_openid'],
            json.dumps(normalized, ensure_ascii=False, separators=(',', ':')),
            next_version,
            now,
            now,
        ),
    )
    conn.commit()
    return normalized, next_version, now


def timing_task_default_config():
    return {'tasks': []}


def validate_timing_time(value):
    value = str(value or '').strip()
    if not re.match(r'^\d{2}:\d{2}$', value):
        raise ValueError('invalid timing task config')
    hour, minute = [int(part) for part in value.split(':')]
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError('invalid timing task config')
    return value


def timing_minutes(value):
    hour, minute = [int(part) for part in value.split(':')]
    return hour * 60 + minute


def normalize_timing_task(task, now, existing=None, assign_id=False, order_fallback=0):
    existing = existing or {}
    title = str(task.get('title', existing.get('title', '')) or '').strip()
    if not title or len(title) > 20:
        raise ValueError('invalid timing task config')

    start_time = validate_timing_time(task.get('startTime', existing.get('startTime', '')))
    end_time = validate_timing_time(task.get('endTime', existing.get('endTime', '')))
    if timing_minutes(end_time) <= timing_minutes(start_time):
        raise ValueError('invalid timing task config')

    task_type = str(task.get('type', existing.get('type', '')) or '').strip()
    if task_type not in TIMING_CONFIG_TASK_TYPES:
        raise ValueError('invalid timing task config')

    order = task.get('order', existing.get('order', order_fallback))
    if not is_int(order) or order < 0:
        raise ValueError('invalid timing task config')

    enabled = task.get('enabled', existing.get('enabled', True))
    if not isinstance(enabled, bool):
        raise ValueError('invalid timing task config')

    task_id = str(task.get('id') or existing.get('id') or '').strip()
    if not task_id and assign_id:
        task_id = gen_task_id()
    if not task_id:
        raise ValueError('invalid timing task config')

    created_at = str(existing.get('createdAt') or task.get('createdAt') or now)
    updated_at = str(task.get('updatedAt') or existing.get('updatedAt') or now)
    return {
        'id': task_id,
        'title': title,
        'startTime': start_time,
        'endTime': end_time,
        'type': task_type,
        'order': order,
        'enabled': enabled,
        'createdAt': created_at,
        'updatedAt': updated_at,
    }


def normalize_timing_task_config(config, now):
    if not isinstance(config, dict):
        raise ValueError('invalid timing task config')
    tasks = config.get('tasks', [])
    if not isinstance(tasks, list):
        raise ValueError('invalid timing task config')
    normalized_tasks = []
    seen_ids = set()
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError('invalid timing task config')
        normalized = normalize_timing_task(task, now, assign_id=True, order_fallback=index)
        if normalized['id'] in seen_ids:
            raise ValueError('invalid timing task config')
        seen_ids.add(normalized['id'])
        normalized_tasks.append(normalized)
    return {'tasks': sorted(normalized_tasks, key=lambda item: item['order'])}


def get_timing_task_row(conn, user_id):
    return conn.execute(
        '''
        SELECT * FROM timing_task_configs
        WHERE project=? AND user_id=? AND deleted_at IS NULL
        ''',
        (TIMING_PROJECT, user_id),
    ).fetchone()


def get_timing_task_config(conn, user):
    row = get_timing_task_row(conn, user['id'])
    if not row:
        return timing_task_default_config(), 0, None
    config = load_json_object(row['task_config_json'], timing_task_default_config())
    return normalize_timing_task_config(config, row['updated_at']), int(row['version']), row['updated_at']


def assert_timing_task_version(row, requested_version):
    if requested_version is None:
        return
    if not is_int(requested_version):
        raise ValueError('invalid timing task config')
    current_version = int(row['version']) if row else 0
    if requested_version != current_version:
        raise RuntimeError(current_version)


def save_timing_task_config(conn, user, config, current_row=None):
    current_version = int(current_row['version']) if current_row else 0
    next_version = current_version + 1
    now = utcnow_iso()
    normalized = normalize_timing_task_config(config, now)
    conn.execute(
        '''
        INSERT INTO timing_task_configs (
            id, project, user_id, wechat_openid, task_config_json, version, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(project, user_id) DO UPDATE SET
            wechat_openid=excluded.wechat_openid,
            task_config_json=excluded.task_config_json,
            version=excluded.version,
            updated_at=excluded.updated_at,
            deleted_at=NULL
        ''',
        (
            gen_config_id('ttcfg'),
            TIMING_PROJECT,
            user['id'],
            user['wechat_openid'],
            json.dumps(normalized, ensure_ascii=False, separators=(',', ':')),
            next_version,
            now,
            now,
        ),
    )
    conn.commit()
    return normalized, next_version, now


def validate_date_text(value):
    value = str(value or '').strip()
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError as exc:
        raise ValueError('invalid timing stats record') from exc
    return value


def normalize_non_negative_int(value):
    if not is_int(value) or value < 0:
        raise ValueError('invalid timing stats record')
    return value


def normalize_task_ids(value):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError('invalid timing stats record')
    seen = set()
    task_ids = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError('invalid timing stats record')
        task_id = item.strip()
        if task_id and task_id not in seen:
            seen.add(task_id)
            task_ids.append(task_id)
    return task_ids


def normalize_custom_task_stats(value):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError('invalid timing stats record')
    result = {}
    for task_id, stats in value.items():
        task_id = str(task_id or '').strip()
        if not task_id:
            continue
        if not isinstance(stats, dict):
            raise ValueError('invalid timing stats record')
        last_result = stats.get('lastResult')
        if last_result not in (None, '', 'good', 'bad'):
            raise ValueError('invalid timing stats record')
        last_completed_at = stats.get('lastCompletedAt')
        if last_completed_at is not None and (not is_int(last_completed_at) or last_completed_at < 0):
            raise ValueError('invalid timing stats record')
        item = {
            'goodCount': normalize_non_negative_int(stats.get('goodCount', 0)),
            'badCount': normalize_non_negative_int(stats.get('badCount', 0)),
        }
        if last_result:
            item['lastResult'] = last_result
        if last_completed_at is not None:
            item['lastCompletedAt'] = last_completed_at
        result[task_id] = item
    return result


def normalize_timing_stats_record(record, expected_date=None):
    if not isinstance(record, dict):
        raise ValueError('invalid timing stats record')
    record_date = validate_date_text(record.get('date') or expected_date)
    if expected_date and record_date != expected_date:
        raise ValueError('invalid timing stats record')
    return {
        'date': record_date,
        'totalTasks': normalize_non_negative_int(record.get('totalTasks', 0)),
        'completedTasks': normalize_non_negative_int(record.get('completedTasks', 0)),
        'stars': normalize_non_negative_int(record.get('stars', 0)),
        'taskIds': normalize_task_ids(record.get('taskIds', [])),
        'customTaskGoodCount': normalize_non_negative_int(record.get('customTaskGoodCount', 0)),
        'customTaskBadCount': normalize_non_negative_int(record.get('customTaskBadCount', 0)),
        'customTaskStats': normalize_custom_task_stats(record.get('customTaskStats', {})),
    }


def upsert_timing_stats_record(conn, user, record_date, record):
    record_date = validate_date_text(record_date)
    normalized = normalize_timing_stats_record(record, record_date)
    now = utcnow_iso()
    conn.execute(
        '''
        INSERT INTO timing_stat_records (
            id, project, user_id, wechat_openid, record_date, stats_json, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(project, user_id, record_date) DO UPDATE SET
            wechat_openid=excluded.wechat_openid,
            stats_json=excluded.stats_json,
            updated_at=excluded.updated_at,
            deleted_at=NULL
        ''',
        (
            gen_config_id('tsrec'),
            TIMING_PROJECT,
            user['id'],
            user['wechat_openid'],
            record_date,
            json.dumps(normalized, ensure_ascii=False, separators=(',', ':')),
            now,
            now,
        ),
    )
    conn.commit()
    return normalized, now


def list_timing_stats_records(conn, user, start_date, end_date):
    start_date = validate_date_text(start_date)
    end_date = validate_date_text(end_date)
    if end_date < start_date:
        raise ValueError('invalid timing stats record')
    rows = conn.execute(
        '''
        SELECT stats_json
        FROM timing_stat_records
        WHERE project=? AND user_id=? AND deleted_at IS NULL
          AND record_date>=? AND record_date<=?
        ORDER BY record_date ASC
        ''',
        (TIMING_PROJECT, user['id'], start_date, end_date),
    ).fetchall()
    records = []
    for row in rows:
        record = load_json_object(row['stats_json'], {})
        records.append(normalize_timing_stats_record(record))
    return records


def delete_timing_stats_records(conn, user, start_date, end_date):
    start_date = validate_date_text(start_date)
    end_date = validate_date_text(end_date)
    if end_date < start_date:
        raise ValueError('invalid timing stats record')
    now = utcnow_iso()
    cursor = conn.execute(
        '''
        UPDATE timing_stat_records
        SET deleted_at=?, updated_at=?
        WHERE project=? AND user_id=? AND deleted_at IS NULL
          AND record_date>=? AND record_date<=?
        ''',
        (now, now, TIMING_PROJECT, user['id'], start_date, end_date),
    )
    conn.commit()
    return cursor.rowcount, now
