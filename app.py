#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""旅游记账系统 - Flask 后端"""

import os
import sqlite3
import uuid
import functools
from flask import Flask, request, jsonify, g, send_from_directory, Response
from urllib.parse import quote
import io

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=None)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.db')

# 固定账号
FIXED_USER = 'lou'
FIXED_PASS = '123'

# 密码文件路径（用于保存修改后的密码）
PASSWORD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.password')

# 简单 token 存储（内存中，重启后失效，用户重新登录即可）
valid_tokens = set()

def get_password():
    """获取当前密码（优先从文件读取）"""
    if os.path.exists(PASSWORD_FILE):
        try:
            with open(PASSWORD_FILE, 'r') as f:
                return f.read().strip()
        except:
            pass
    return FIXED_PASS

def set_password(new_password):
    """保存新密码到文件"""
    with open(PASSWORD_FILE, 'w') as f:
        f.write(new_password)

DEFAULT_CATEGORIES = ['交通工具（飞机/动车/自驾）', '住宿', '餐费', '打车']

# ===== 数据库 =====

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """初始化数据库表和默认数据"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS trips (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            note TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS records (
            id TEXT PRIMARY KEY,
            trip_id TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            payer TEXT NOT NULL,
            date TEXT,
            note TEXT,
            FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS payers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    ''')
    # 插入默认类别（忽略已存在的）
    for cat in DEFAULT_CATEGORIES:
        conn.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (cat,))
    conn.commit()
    conn.close()

# ===== Token 鉴权 =====

def require_auth(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token or token not in valid_tokens:
            return jsonify({'error': '未登录或登录已过期'}), 401
        return f(*args, **kwargs)
    return wrapper

# ===== 工具函数 =====

def gen_id():
    return uuid.uuid4().hex[:16]

def row_to_dict(row):
    if row is None:
        return None
    return dict(row)

def rows_to_list(rows):
    return [dict(r) for r in rows]

# ===== API：登录 =====

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '')
    password = data.get('password', '')
    if username == FIXED_USER and password == get_password():
        token = uuid.uuid4().hex
        valid_tokens.add(token)
        return jsonify({'token': token})
    return jsonify({'error': '账号或密码错误'}), 401

# ===== API：修改密码 =====

@app.route('/api/password', methods=['POST'])
@require_auth
def change_password():
    data = request.get_json(silent=True) or {}
    old_password = data.get('oldPassword', '')
    new_password = data.get('newPassword', '')
    if not old_password or not new_password:
        return jsonify({'error': '请填写完整'}), 400
    if len(new_password) < 3:
        return jsonify({'error': '新密码至少3位'}), 400
    if old_password != get_password():
        return jsonify({'error': '原密码错误'}), 400
    set_password(new_password)
    return jsonify({'ok': True})

# ===== API：旅行 =====

@app.route('/api/trips', methods=['GET'])
@require_auth
def get_trips():
    db = get_db()
    trips = rows_to_list(db.execute(
        'SELECT * FROM trips ORDER BY created_at DESC'
    ).fetchall())
    # 为每个旅行附加汇总信息
    for t in trips:
        row = db.execute(
            'SELECT COUNT(*) as cnt, COALESCE(SUM(amount),0) as total FROM records WHERE trip_id=?',
            (t['id'],)
        ).fetchone()
        t['record_count'] = row['cnt']
        t['total_amount'] = row['total']
        # 参与人
        payers = db.execute(
            'SELECT DISTINCT payer FROM records WHERE trip_id=?', (t['id'],)
        ).fetchall()
        t['payers'] = [p['payer'] for p in payers]
    return jsonify(trips)

@app.route('/api/trips', methods=['POST'])
@require_auth
def create_trip():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '旅行名称不能为空'}), 400
    trip_id = gen_id()
    db = get_db()
    db.execute(
        'INSERT INTO trips (id, name, start_date, end_date, note, created_at) VALUES (?,?,?,?,?,datetime("now"))',
        (trip_id, name, data.get('startDate', ''), data.get('endDate', ''), data.get('note', ''))
    )
    db.commit()
    return jsonify({'id': trip_id, 'name': name}), 201

@app.route('/api/trips/<trip_id>', methods=['GET'])
@require_auth
def get_trip(trip_id):
    db = get_db()
    trip = row_to_dict(db.execute('SELECT * FROM trips WHERE id=?', (trip_id,)).fetchone())
    if not trip:
        return jsonify({'error': '旅行不存在'}), 404
    records = rows_to_list(db.execute(
        'SELECT * FROM records WHERE trip_id=? ORDER BY date DESC', (trip_id,)
    ).fetchall())
    trip['records'] = records
    # 汇总
    trip['total_amount'] = sum(r['amount'] for r in records)
    by_payer = {}
    by_category = {}
    for r in records:
        by_payer[r['payer']] = by_payer.get(r['payer'], 0) + r['amount']
        by_category[r['category']] = by_category.get(r['category'], 0) + r['amount']
    trip['by_payer'] = by_payer
    trip['by_category'] = by_category
    return jsonify(trip)

@app.route('/api/trips/<trip_id>', methods=['PUT'])
@require_auth
def update_trip(trip_id):
    db = get_db()
    existing = db.execute('SELECT id FROM trips WHERE id=?', (trip_id,)).fetchone()
    if not existing:
        return jsonify({'error': '旅行不存在'}), 404
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '旅行名称不能为空'}), 400
    db.execute(
        'UPDATE trips SET name=?, start_date=?, end_date=?, note=? WHERE id=?',
        (name, data.get('startDate', ''), data.get('endDate', ''), data.get('note', ''), trip_id)
    )
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/trips/<trip_id>', methods=['DELETE'])
@require_auth
def delete_trip(trip_id):
    db = get_db()
    db.execute('DELETE FROM records WHERE trip_id=?', (trip_id,))
    db.execute('DELETE FROM trips WHERE id=?', (trip_id,))
    db.commit()
    return jsonify({'ok': True})

# ===== API：记账记录 =====

@app.route('/api/trips/<trip_id>/records', methods=['POST'])
@require_auth
def create_record(trip_id):
    db = get_db()
    trip = db.execute('SELECT id FROM trips WHERE id=?', (trip_id,)).fetchone()
    if not trip:
        return jsonify({'error': '旅行不存在'}), 404
    data = request.get_json(silent=True) or {}
    category = data.get('category', '').strip()
    amount = data.get('amount', 0)
    payer = data.get('payer', '').strip()
    if not category or not payer:
        return jsonify({'error': '类别和支付人不能为空'}), 400
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({'error': '金额必须为正数'}), 400
    rec_id = gen_id()
    db.execute(
        'INSERT INTO records (id, trip_id, category, amount, payer, date, note) VALUES (?,?,?,?,?,?,?)',
        (rec_id, trip_id, category, amount, payer, data.get('date', ''), data.get('note', ''))
    )
    # 自动记录支付人和类别
    db.execute('INSERT OR IGNORE INTO payers (name) VALUES (?)', (payer,))
    db.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (category,))
    db.commit()
    return jsonify({'id': rec_id}), 201

@app.route('/api/records/<rec_id>', methods=['PUT'])
@require_auth
def update_record(rec_id):
    db = get_db()
    existing = db.execute('SELECT id FROM records WHERE id=?', (rec_id,)).fetchone()
    if not existing:
        return jsonify({'error': '记录不存在'}), 404
    data = request.get_json(silent=True) or {}
    category = data.get('category', '').strip()
    amount = data.get('amount', 0)
    payer = data.get('payer', '').strip()
    if not category or not payer:
        return jsonify({'error': '类别和支付人不能为空'}), 400
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({'error': '金额必须为正数'}), 400
    db.execute(
        'UPDATE records SET category=?, amount=?, payer=?, date=?, note=? WHERE id=?',
        (category, amount, payer, data.get('date', ''), data.get('note', ''), rec_id)
    )
    db.execute('INSERT OR IGNORE INTO payers (name) VALUES (?)', (payer,))
    db.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (category,))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/records/<rec_id>', methods=['DELETE'])
@require_auth
def delete_record(rec_id):
    db = get_db()
    db.execute('DELETE FROM records WHERE id=?', (rec_id,))
    db.commit()
    return jsonify({'ok': True})

# ===== API：支付人 =====

@app.route('/api/payers', methods=['GET'])
@require_auth
def get_payers():
    db = get_db()
    rows = db.execute('SELECT name FROM payers ORDER BY id').fetchall()
    return jsonify([r['name'] for r in rows])

@app.route('/api/payers', methods=['POST'])
@require_auth
def create_payer():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '姓名不能为空'}), 400
    db = get_db()
    db.execute('INSERT OR IGNORE INTO payers (name) VALUES (?)', (name,))
    db.commit()
    return jsonify({'ok': True}), 201

@app.route('/api/payers/<name>', methods=['PUT'])
@require_auth
def update_payer(name):
    data = request.get_json(silent=True) or {}
    new_name = data.get('name', '').strip()
    if not new_name:
        return jsonify({'error': '姓名不能为空'}), 400
    db = get_db()
    existing = db.execute('SELECT id FROM payers WHERE name=?', (name,)).fetchone()
    if not existing:
        return jsonify({'error': '支付人不存在'}), 404
    # 检查新名称是否已存在
    duplicate = db.execute('SELECT id FROM payers WHERE name=? AND name!=?', (new_name, name)).fetchone()
    if duplicate:
        return jsonify({'error': '该姓名已存在'}), 400
    db.execute('UPDATE payers SET name=? WHERE name=?', (new_name, name))
    # 同步更新记录中的支付人
    db.execute('UPDATE records SET payer=? WHERE payer=?', (new_name, name))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/payers/<name>', methods=['DELETE'])
@require_auth
def delete_payer(name):
    db = get_db()
    existing = db.execute('SELECT id FROM payers WHERE name=?', (name,)).fetchone()
    if not existing:
        return jsonify({'error': '支付人不存在'}), 404
    db.execute('DELETE FROM payers WHERE name=?', (name,))
    db.commit()
    return jsonify({'ok': True})

# ===== API：类别 =====

@app.route('/api/categories', methods=['GET'])
@require_auth
def get_categories():
    db = get_db()
    rows = db.execute('SELECT name FROM categories ORDER BY id').fetchall()
    return jsonify([r['name'] for r in rows])

@app.route('/api/categories', methods=['POST'])
@require_auth
def create_category():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '类别名称不能为空'}), 400
    db = get_db()
    db.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (name,))
    db.commit()
    return jsonify({'ok': True}), 201

@app.route('/api/categories/<name>', methods=['PUT'])
@require_auth
def update_category(name):
    data = request.get_json(silent=True) or {}
    new_name = data.get('name', '').strip()
    if not new_name:
        return jsonify({'error': '类别名称不能为空'}), 400
    db = get_db()
    existing = db.execute('SELECT id FROM categories WHERE name=?', (name,)).fetchone()
    if not existing:
        return jsonify({'error': '类别不存在'}), 404
    # 检查新名称是否已存在
    duplicate = db.execute('SELECT id FROM categories WHERE name=? AND name!=?', (new_name, name)).fetchone()
    if duplicate:
        return jsonify({'error': '该类别已存在'}), 400
    db.execute('UPDATE categories SET name=? WHERE name=?', (new_name, name))
    # 同步更新记录中的类别
    db.execute('UPDATE records SET category=? WHERE category=?', (new_name, name))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/categories/<name>', methods=['DELETE'])
@require_auth
def delete_category(name):
    db = get_db()
    existing = db.execute('SELECT id FROM categories WHERE name=?', (name,)).fetchone()
    if not existing:
        return jsonify({'error': '类别不存在'}), 404
    db.execute('DELETE FROM categories WHERE name=?', (name,))
    db.commit()
    return jsonify({'ok': True})

# ===== API：导出Excel =====

@app.route('/api/trips/<trip_id>/export', methods=['GET'])
def export_trip_excel(trip_id):
    # 支持URL参数传递token（用于下载）
    token = request.args.get('token', '')
    if not token or token not in valid_tokens:
        return jsonify({'error': '未登录或登录已过期'}), 401
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        trip = conn.execute('SELECT * FROM trips WHERE id=?', (trip_id,)).fetchone()
        if not trip:
            return jsonify({'error': '旅行不存在'}), 404
        trip = dict(trip)
        records = [dict(r) for r in conn.execute(
            'SELECT * FROM records WHERE trip_id=? ORDER BY date DESC', (trip_id,)
        ).fetchall()]
    finally:
        conn.close()
    
    # 生成CSV格式（无需额外依赖）
    output = io.StringIO()
    # BOM头，确保Excel正确识别UTF-8
    output.write('\ufeff')
    # 标题行
    output.write('旅行名称,{}\n'.format(trip['name']))
    if trip['start_date']:
        output.write('开始日期,{}\n'.format(trip['start_date']))
    if trip['end_date']:
        output.write('结束日期,{}\n'.format(trip['end_date']))
    if trip['note']:
        output.write('备注,{}\n'.format(trip['note']))
    output.write('\n')
    # 明细表头
    output.write('日期,类别,金额,支付人,备注\n')
    # 明细数据
    total = 0
    for r in records:
        output.write('{},{},{},{},{}\n'.format(
            r['date'] or '',
            r['category'],
            r['amount'],
            r['payer'],
            r['note'] or ''
        ))
        total += r['amount']
    output.write('\n')
    # 汇总
    output.write('总计,{}\n'.format(total))
    
    # 按支付人汇总
    by_payer = {}
    for r in records:
        by_payer[r['payer']] = by_payer.get(r['payer'], 0) + r['amount']
    output.write('\n按支付人汇总\n')
    for payer, amount in by_payer.items():
        output.write('{},{}\n'.format(payer, amount))
    
    # 按类别汇总
    by_category = {}
    for r in records:
        by_category[r['category']] = by_category.get(r['category'], 0) + r['amount']
    output.write('\n按类别汇总\n')
    for cat, amount in by_category.items():
        output.write('{},{}\n'.format(cat, amount))
    
    output.seek(0)
    # 转换为bytes
    csv_bytes = io.BytesIO(output.getvalue().encode('utf-8-sig'))
    
    filename = '{}.csv'.format(trip['name'])
    # RFC 5987 编码中文文件名
    encoded_filename = quote(filename)
    return Response(
        csv_bytes.getvalue(),
        mimetype='text/csv;charset=utf-8',
        headers={
            'Content-Disposition': "attachment; filename*=UTF-8''{}".format(encoded_filename)
        }
    )

# ===== 静态文件服务（无 Nginx 时 Flask 自身托管） =====

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(BASE_DIR, filename)

@app.route('/')
def serve_index():
    return send_from_directory(BASE_DIR, 'login.html')

# ===== 启动 =====

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
