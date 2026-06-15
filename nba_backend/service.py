"""Services for collecting and serving Sina NBA player data."""

import concurrent.futures
import json
import os
import re
import sqlite3
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime

from flask import current_app, g


SINA_API_URL = 'https://slamdunk.sports.sina.com.cn/api'
SINA_PLAYER_PAGE = 'https://slamdunk.sports.sina.com.cn/player?pid={pid}'
DEFAULT_TIMEOUT = 20
DEFAULT_CONCURRENCY = 8
MAX_CONCURRENCY = 16


def utcnow_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat()


def connect_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def get_nba_db():
    if 'nba_db' not in g:
        g.nba_db = connect_db(current_app.config['NBA_DB_PATH'])
    return g.nba_db


def close_nba_db(exc=None):
    db = g.pop('nba_db', None)
    if db is not None:
        db.close()


def init_nba_db(db_path):
    conn = connect_db(db_path)
    try:
        conn.executescript(
            '''
            CREATE TABLE IF NOT EXISTS nba_players (
                pid TEXT PRIMARY KEY,
                first_name TEXT NOT NULL DEFAULT '',
                last_name TEXT NOT NULL DEFAULT '',
                first_name_cn TEXT NOT NULL DEFAULT '',
                last_name_cn TEXT NOT NULL DEFAULT '',
                chinese_name TEXT NOT NULL DEFAULT '',
                english_name TEXT NOT NULL DEFAULT '',
                team_tid TEXT NOT NULL DEFAULT '',
                team_market TEXT NOT NULL DEFAULT '',
                team_name TEXT NOT NULL DEFAULT '',
                team_full_name TEXT NOT NULL DEFAULT '',
                jersey_number TEXT NOT NULL DEFAULT '',
                primary_position TEXT NOT NULL DEFAULT '',
                position TEXT NOT NULL DEFAULT '',
                birthdate TEXT NOT NULL DEFAULT '',
                age INTEGER,
                nation TEXT NOT NULL DEFAULT '',
                college TEXT NOT NULL DEFAULT '',
                experience INTEGER,
                draft_year TEXT NOT NULL DEFAULT '',
                draft_round TEXT NOT NULL DEFAULT '',
                draft_pick TEXT NOT NULL DEFAULT '',
                height_cm INTEGER,
                weight_kg INTEGER,
                wingspan TEXT NOT NULL DEFAULT '',
                standing_reach TEXT NOT NULL DEFAULT '',
                salary_wan_usd REAL,
                current_salary TEXT NOT NULL DEFAULT '',
                avg_points REAL,
                avg_rebounds REAL,
                avg_assists REAL,
                avg_steals REAL,
                avg_blocks REAL,
                source_url TEXT NOT NULL DEFAULT '',
                source_updated_at TEXT NOT NULL DEFAULT '',
                raw_info_json TEXT NOT NULL DEFAULT '{}',
                raw_stats_json TEXT NOT NULL DEFAULT '{}',
                image_path TEXT NOT NULL DEFAULT '',
                image_filename TEXT NOT NULL DEFAULT '',
                image_url TEXT NOT NULL DEFAULT '',
                image_missing INTEGER NOT NULL DEFAULT 1,
                image_checked_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_nba_players_team ON nba_players(team_tid);
            CREATE INDEX IF NOT EXISTS idx_nba_players_chinese_name ON nba_players(chinese_name);
            CREATE INDEX IF NOT EXISTS idx_nba_players_english_name ON nba_players(english_name);
            '''
        )
        migrate_nba_db(conn)
        conn.commit()
    finally:
        conn.close()


def has_column(conn, table_name, column_name):
    rows = conn.execute("PRAGMA table_info({})".format(table_name)).fetchall()
    return any(row['name'] == column_name for row in rows)


def migrate_nba_db(conn):
    columns = {
        'image_path': "TEXT NOT NULL DEFAULT ''",
        'image_filename': "TEXT NOT NULL DEFAULT ''",
        'image_url': "TEXT NOT NULL DEFAULT ''",
        'image_missing': 'INTEGER NOT NULL DEFAULT 1',
        'image_checked_at': "TEXT NOT NULL DEFAULT ''",
    }
    for name, definition in columns.items():
        if not has_column(conn, 'nba_players', name):
            conn.execute('ALTER TABLE nba_players ADD COLUMN {} {}'.format(name, definition))


def row_to_player(row):
    if row is None:
        return None
    item = dict(row)
    for key in ('age', 'experience', 'height_cm', 'weight_kg'):
        if item.get(key) is not None:
            item[key] = int(item[key])
    for key in ('salary_wan_usd', 'avg_points', 'avg_rebounds', 'avg_assists', 'avg_steals', 'avg_blocks'):
        if item.get(key) is not None:
            item[key] = float(item[key])
    item['source'] = 'sina_nba'
    item['team'] = {
        'tid': item.get('team_tid') or '',
        'market': item.get('team_market') or '',
        'name': item.get('team_name') or '',
        'full_name': item.get('team_full_name') or '',
    }
    item['stats'] = {
        'avg_points': item.get('avg_points'),
        'avg_rebounds': item.get('avg_rebounds'),
        'avg_assists': item.get('avg_assists'),
        'avg_steals': item.get('avg_steals'),
        'avg_blocks': item.get('avg_blocks'),
    }
    item['profile'] = {
        'birthdate': item.get('birthdate') or '',
        'age': item.get('age'),
        'nation': item.get('nation') or '',
        'college': item.get('college') or '',
        'experience': item.get('experience'),
        'draft_year': item.get('draft_year') or '',
        'draft_round': item.get('draft_round') or '',
        'draft_pick': item.get('draft_pick') or '',
        'height_cm': item.get('height_cm'),
        'weight_kg': item.get('weight_kg'),
        'wingspan': item.get('wingspan') or '',
        'standing_reach': item.get('standing_reach') or '',
        'current_salary': item.get('current_salary') or '',
        'salary_wan_usd': item.get('salary_wan_usd'),
    }
    item['image'] = {
        'filename': item.get('image_filename') or '',
        'url': item.get('image_url') or '',
        'missing': bool(item.get('image_missing')),
        'checked_at': item.get('image_checked_at') or '',
    }
    item.pop('raw_info_json', None)
    item.pop('raw_stats_json', None)
    item.pop('image_path', None)
    item.pop('image_filename', None)
    item.pop('image_url', None)
    item.pop('image_missing', None)
    item.pop('image_checked_at', None)
    return item


def to_int(value):
    if value in (None, ''):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def to_float(value):
    if value in (None, ''):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_name(first_name, last_name, separator):
    parts = [str(first_name or '').strip(), str(last_name or '').strip()]
    parts = [part for part in parts if part]
    return separator.join(parts)


def normalize_salary(value):
    amount = to_float(value)
    if amount is None or amount <= 0:
        return None, ''
    if amount.is_integer():
        display = '{}万美元'.format(int(amount))
    else:
        display = '{}万美元'.format(amount)
    return amount, display


def strip_accents(value):
    return ''.join(
        char
        for char in unicodedata.normalize('NFKD', str(value or ''))
        if not unicodedata.combining(char)
    )


def image_name_variants(value):
    if not value:
        return set()
    basename = os.path.basename(str(value))
    stem, ext = os.path.splitext(basename)
    if ext.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
        stem = basename
    text = strip_accents(stem.replace('_', ' ')).lower()

    def alnum(source):
        return re.sub(r'[^a-z0-9]+', '', source)

    variants = {alnum(text)}
    spaced = re.sub(r'([a-z])\\.([a-z])\\.?', r'\1 \2 ', text)
    spaced = spaced.replace("'", ' ').replace('-', ' ')
    variants.add(alnum(spaced))
    variants.add(alnum(re.sub(r'\b(jr|ii|iii|iv)\b', '', spaced)))

    tokens = [token for token in re.split(r'[^a-z0-9]+', spaced) if token]
    merged = []
    index = 0
    while index < len(tokens):
        if len(tokens[index]) == 1:
            end = index
            group = []
            while end < len(tokens) and len(tokens[end]) == 1:
                group.append(tokens[end])
                end += 1
            if len(group) > 1:
                merged.append(''.join(group))
            else:
                merged.extend(group)
            index = end
        else:
            merged.append(tokens[index])
            index += 1
    if merged:
        variants.add(''.join(merged))
        variants.add(''.join(token for token in merged if token not in ('jr', 'ii', 'iii', 'iv')))
    return {variant for variant in variants if variant}


def collect_image_index(image_dir):
    index = {}
    collisions = {}
    if not image_dir or not os.path.isdir(image_dir):
        return index, collisions
    for filename in sorted(os.listdir(image_dir)):
        path = os.path.join(image_dir, filename)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
            continue
        for key in image_name_variants(filename):
            existing = index.get(key)
            if existing and existing != filename:
                collisions.setdefault(key, set()).update([existing, filename])
            else:
                index[key] = filename
    return index, collisions


def match_image_filename(english_name, image_index):
    for key in image_name_variants(english_name):
        filename = image_index.get(key)
        if filename:
            return filename
    return ''


def fetch_sina_json(params, timeout=DEFAULT_TIMEOUT):
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        SINA_API_URL + '?' + query,
        headers={
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json,text/javascript,*/*',
            'Referer': 'https://slamdunk.sports.sina.com.cn/roster',
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or 'utf-8'
        payload = response.read().decode(charset)
    data = json.loads(payload)
    status = data.get('result', {}).get('status', {})
    if status.get('code') not in (0, '0'):
        raise RuntimeError(status.get('msg') or 'Sina API returned an error')
    return data


def sina_data(payload):
    return payload.get('result', {}).get('data') or {}


def collect_team_seeds(limit=None):
    payload = fetch_sina_json({'p': 'radar', 's': 'team', 'a': 'rosters', 'limit': limit or 500})
    data = sina_data(payload)
    season = data.get('league', {}).get('season')
    teams = []
    for item in data.get('teams') or []:
        team = item.get('team') or {}
        tid = team.get('tid')
        if tid:
            teams.append(team)
    return season, teams


def collect_roster_players(team, season):
    params = {'p': 'radar', 's': 'team', 'a': 'roster', 'tid': team['tid']}
    if season:
        params['season'] = season
    payload = fetch_sina_json(params)
    data = sina_data(payload)
    roster = data.get('roster') or []
    players = []
    for player in roster:
        pid = player.get('pid')
        if not pid:
            continue
        players.append({
            'pid': pid,
            'team': team,
            'roster': player,
        })
    return players


def collect_all_player_seeds(limit_teams=None, season=None):
    discovered_season, teams = collect_team_seeds()
    limit_teams = to_int(limit_teams)
    if limit_teams:
        teams = teams[:limit_teams]
    season = season or discovered_season
    seeds = []
    seen = set()
    for team in teams:
        for seed in collect_roster_players(team, season):
            pid = seed['pid']
            if pid in seen:
                continue
            seen.add(pid)
            seeds.append(seed)
    return season, teams, seeds


def stats_by_item(leaders_payload):
    average = sina_data(leaders_payload).get('reg', {}).get('average') or []
    return {item.get('item'): item.get('score') for item in average if item.get('item')}


def build_player_record(info_payload, leaders_payload):
    info = sina_data(info_payload)
    stats = stats_by_item(leaders_payload)
    pid = info.get('pid')
    if not pid:
        raise RuntimeError('Sina player info did not include pid')
    salary_amount, salary_text = normalize_salary(info.get('salary'))
    team_full_name = normalize_name(info.get('team_market'), info.get('team_name'), '')
    now = utcnow_iso()
    return {
        'pid': pid,
        'first_name': str(info.get('first_name') or ''),
        'last_name': str(info.get('last_name') or ''),
        'first_name_cn': str(info.get('first_name_cn') or ''),
        'last_name_cn': str(info.get('last_name_cn') or ''),
        'chinese_name': normalize_name(info.get('first_name_cn'), info.get('last_name_cn'), '-'),
        'english_name': normalize_name(info.get('first_name'), info.get('last_name'), ' '),
        'team_tid': str(info.get('tid') or ''),
        'team_market': str(info.get('team_market') or ''),
        'team_name': str(info.get('team_name') or ''),
        'team_full_name': team_full_name,
        'jersey_number': str(info.get('jersey_number') or ''),
        'primary_position': str(info.get('primary_position') or ''),
        'position': str(info.get('primary_position') or ''),
        'birthdate': str(info.get('birthdate') or ''),
        'age': to_int(info.get('age')),
        'nation': str(info.get('nation') or ''),
        'college': str(info.get('college') or ''),
        'experience': to_int(info.get('experience')),
        'draft_year': str(info.get('draft_year') or ''),
        'draft_round': str(info.get('draft_round') or ''),
        'draft_pick': str(info.get('draft_pick') or ''),
        'height_cm': to_int(info.get('centimeter')),
        'weight_kg': to_int(info.get('kilo')),
        'wingspan': str(info.get('wingspan') or ''),
        'standing_reach': str(info.get('reach') or ''),
        'salary_wan_usd': salary_amount,
        'current_salary': salary_text,
        'avg_points': to_float(stats.get('points')),
        'avg_rebounds': to_float(stats.get('rebounds')),
        'avg_assists': to_float(stats.get('assists')),
        'avg_steals': to_float(stats.get('steals')),
        'avg_blocks': to_float(stats.get('blocks')),
        'source_url': SINA_PLAYER_PAGE.format(pid=pid),
        'source_updated_at': info_payload.get('result', {}).get('timestamp') or now,
        'raw_info_json': json.dumps(info_payload, ensure_ascii=False, sort_keys=True),
        'raw_stats_json': json.dumps(leaders_payload, ensure_ascii=False, sort_keys=True),
        'created_at': now,
        'updated_at': now,
    }


def collect_player(pid):
    info_payload = fetch_sina_json({'p': 'radar', 's': 'player', 'a': 'info', 'pid': pid})
    leaders_payload = fetch_sina_json({'p': 'radar', 's': 'leaders', 'a': 'player', 'pid': pid})
    return build_player_record(info_payload, leaders_payload)


def upsert_player(conn, player):
    existing = conn.execute('SELECT created_at FROM nba_players WHERE pid=?', (player['pid'],)).fetchone()
    created_at = existing['created_at'] if existing else player['created_at']
    values = dict(player)
    values['created_at'] = created_at
    conn.execute(
        '''
        INSERT INTO nba_players (
            pid, first_name, last_name, first_name_cn, last_name_cn, chinese_name, english_name,
            team_tid, team_market, team_name, team_full_name, jersey_number, primary_position, position,
            birthdate, age, nation, college, experience, draft_year, draft_round, draft_pick,
            height_cm, weight_kg, wingspan, standing_reach, salary_wan_usd, current_salary,
            avg_points, avg_rebounds, avg_assists, avg_steals, avg_blocks, source_url,
            source_updated_at, raw_info_json, raw_stats_json, created_at, updated_at
        ) VALUES (
            :pid, :first_name, :last_name, :first_name_cn, :last_name_cn, :chinese_name, :english_name,
            :team_tid, :team_market, :team_name, :team_full_name, :jersey_number, :primary_position, :position,
            :birthdate, :age, :nation, :college, :experience, :draft_year, :draft_round, :draft_pick,
            :height_cm, :weight_kg, :wingspan, :standing_reach, :salary_wan_usd, :current_salary,
            :avg_points, :avg_rebounds, :avg_assists, :avg_steals, :avg_blocks, :source_url,
            :source_updated_at, :raw_info_json, :raw_stats_json, :created_at, :updated_at
        )
        ON CONFLICT(pid) DO UPDATE SET
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            first_name_cn=excluded.first_name_cn,
            last_name_cn=excluded.last_name_cn,
            chinese_name=excluded.chinese_name,
            english_name=excluded.english_name,
            team_tid=excluded.team_tid,
            team_market=excluded.team_market,
            team_name=excluded.team_name,
            team_full_name=excluded.team_full_name,
            jersey_number=excluded.jersey_number,
            primary_position=excluded.primary_position,
            position=excluded.position,
            birthdate=excluded.birthdate,
            age=excluded.age,
            nation=excluded.nation,
            college=excluded.college,
            experience=excluded.experience,
            draft_year=excluded.draft_year,
            draft_round=excluded.draft_round,
            draft_pick=excluded.draft_pick,
            height_cm=excluded.height_cm,
            weight_kg=excluded.weight_kg,
            wingspan=excluded.wingspan,
            standing_reach=excluded.standing_reach,
            salary_wan_usd=excluded.salary_wan_usd,
            current_salary=excluded.current_salary,
            avg_points=excluded.avg_points,
            avg_rebounds=excluded.avg_rebounds,
            avg_assists=excluded.avg_assists,
            avg_steals=excluded.avg_steals,
            avg_blocks=excluded.avg_blocks,
            source_url=excluded.source_url,
            source_updated_at=excluded.source_updated_at,
            raw_info_json=excluded.raw_info_json,
            raw_stats_json=excluded.raw_stats_json,
            updated_at=excluded.updated_at
        ''',
        values,
    )


def sync_single_player(conn, pid):
    player = collect_player(pid)
    upsert_player(conn, player)
    conn.commit()
    return player


def sync_all_players(conn, limit_teams=None, limit_players=None, concurrency=DEFAULT_CONCURRENCY, season=None):
    season, teams, seeds = collect_all_player_seeds(limit_teams=limit_teams, season=season)
    limit_players = to_int(limit_players)
    if limit_players:
        seeds = seeds[:limit_players]
    concurrency = max(1, min(to_int(concurrency) or DEFAULT_CONCURRENCY, MAX_CONCURRENCY))
    players = []
    errors = []
    started = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_seed = {executor.submit(collect_player, seed['pid']): seed for seed in seeds}
        for future in concurrent.futures.as_completed(future_to_seed):
            seed = future_to_seed[future]
            try:
                players.append(future.result())
            except Exception as exc:
                errors.append({'pid': seed['pid'], 'error': str(exc)})

    for player in players:
        upsert_player(conn, player)
    conn.commit()
    return {
        'season': season,
        'team_count': len(teams),
        'requested_count': len(seeds),
        'succeeded_count': len(players),
        'failed_count': len(errors),
        'errors': errors,
        'elapsed_seconds': round(time.time() - started, 3),
    }


def sync_player_images(conn, image_dir, url_prefix='/api/nba/images'):
    image_index, collisions = collect_image_index(image_dir)
    now = utcnow_iso()
    matched = 0
    missing = []
    rows = conn.execute(
        '''
        SELECT pid, chinese_name, english_name
        FROM nba_players
        ORDER BY team_full_name ASC, chinese_name ASC
        '''
    ).fetchall()
    for row in rows:
        filename = match_image_filename(row['english_name'], image_index)
        if filename:
            image_path = os.path.abspath(os.path.join(image_dir, filename))
            image_url = url_prefix.rstrip('/') + '/' + urllib.parse.quote(filename)
            conn.execute(
                '''
                UPDATE nba_players
                SET image_path=?, image_filename=?, image_url=?, image_missing=0, image_checked_at=?, updated_at=?
                WHERE pid=?
                ''',
                (image_path, filename, image_url, now, now, row['pid']),
            )
            matched += 1
            continue
        conn.execute(
            '''
            UPDATE nba_players
            SET image_path='', image_filename='', image_url='', image_missing=1, image_checked_at=?, updated_at=?
            WHERE pid=?
            ''',
            (now, now, row['pid']),
        )
        missing.append({
            'pid': row['pid'],
            'chinese_name': row['chinese_name'],
            'english_name': row['english_name'],
        })
    conn.commit()
    return {
        'total': len(rows),
        'image_count': len(set(image_index.values())),
        'matched_count': matched,
        'missing_count': len(missing),
        'missing': missing,
        'collisions': [
            {'key': key, 'filenames': sorted(value)}
            for key, value in sorted(collisions.items())
        ],
        'checked_at': now,
    }


def list_players(conn, query='', team_tid='', team='', position='', limit=50, offset=0, name_only=False):
    where = []
    params = []
    if query:
        like = '%' + query + '%'
        if name_only:
            where.append('(chinese_name LIKE ? OR english_name LIKE ?)')
            params.extend([like, like])
        else:
            where.append('(chinese_name LIKE ? OR english_name LIKE ? OR team_full_name LIKE ?)')
            params.extend([like, like, like])
    if team_tid:
        where.append('team_tid=?')
        params.append(team_tid)
    if team:
        like = '%' + team + '%'
        where.append('(team_full_name LIKE ? OR team_market LIKE ? OR team_name LIKE ?)')
        params.extend([like, like, like])
    if position:
        where.append('(primary_position=? OR position=?)')
        params.extend([position, position])
    clause = ' WHERE ' + ' AND '.join(where) if where else ''
    total = conn.execute('SELECT COUNT(*) AS total FROM nba_players' + clause, params).fetchone()['total']
    rows = conn.execute(
        '''
        SELECT * FROM nba_players
        {clause}
        ORDER BY team_full_name ASC, CAST(NULLIF(jersey_number, '') AS INTEGER) ASC, chinese_name ASC
        LIMIT ? OFFSET ?
        '''.format(clause=clause),
        params + [limit, offset],
    ).fetchall()
    return total, [row_to_player(row) for row in rows]


def list_filter_options(conn):
    team_rows = conn.execute(
        '''
        SELECT team_tid, team_market, team_name, team_full_name, COUNT(*) AS player_count
        FROM nba_players
        WHERE team_tid!=''
        GROUP BY team_tid, team_market, team_name, team_full_name
        ORDER BY team_full_name ASC
        '''
    ).fetchall()
    position_rows = conn.execute(
        '''
        SELECT primary_position AS position, COUNT(*) AS player_count
        FROM nba_players
        WHERE primary_position!=''
        GROUP BY primary_position
        ORDER BY primary_position ASC
        '''
    ).fetchall()
    return {
        'teams': [
            {
                'tid': row['team_tid'],
                'market': row['team_market'],
                'name': row['team_name'],
                'full_name': row['team_full_name'],
                'player_count': row['player_count'],
            }
            for row in team_rows
        ],
        'positions': [
            {
                'position': row['position'],
                'player_count': row['player_count'],
            }
            for row in position_rows
        ],
    }


def get_player(conn, pid):
    row = conn.execute('SELECT * FROM nba_players WHERE pid=?', (pid,)).fetchone()
    return row_to_player(row)


def list_missing_images(conn):
    rows = conn.execute(
        '''
        SELECT pid, chinese_name, english_name, team_full_name
        FROM nba_players
        WHERE image_missing=1
        ORDER BY team_full_name ASC, chinese_name ASC
        '''
    ).fetchall()
    return [dict(row) for row in rows]


def nba_sync_token():
    return os.environ.get('NBA_SYNC_TOKEN', '').strip()
