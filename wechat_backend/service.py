"""Services for WeChat Mini Program code exchange and local user records."""

import json
import sqlite3
import urllib.parse
import urllib.request
import uuid
from datetime import datetime

from flask import current_app, g


WECHAT_CODE2SESSION_URL = 'https://api.weixin.qq.com/sns/jscode2session'
DEFAULT_TIMEOUT = 10


class WeChatCodeExchangeError(Exception):
    def __init__(self, errcode, message='wechat code2Session failed'):
        super().__init__(message)
        self.errcode = errcode


class WeChatUpstreamError(Exception):
    pass


def utcnow_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat()


def gen_user_id():
    return 'wx_' + uuid.uuid4().hex[:24]


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


def init_wechat_db(db_path):
    conn = connect_db(db_path)
    try:
        conn.executescript(
            '''
            CREATE TABLE IF NOT EXISTS wechat_users (
                id TEXT PRIMARY KEY,
                wechat_openid TEXT UNIQUE NOT NULL,
                wechat_unionid TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_wechat_users_unionid ON wechat_users(wechat_unionid);
            '''
        )
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


def find_or_create_user(conn, openid, unionid=''):
    now = utcnow_iso()
    row = conn.execute(
        'SELECT * FROM wechat_users WHERE wechat_openid=?',
        (openid,),
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
            id, wechat_openid, wechat_unionid, created_at, updated_at, last_login_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (user_id, openid, unionid or None, now, now, now),
    )
    conn.commit()
    return conn.execute('SELECT * FROM wechat_users WHERE id=?', (user_id,)).fetchone()


def user_session_payload(user):
    payload = {
        'userId': user['id'],
        'openid': user['wechat_openid'],
    }
    if user['wechat_unionid']:
        payload['unionid'] = user['wechat_unionid']
    return payload
