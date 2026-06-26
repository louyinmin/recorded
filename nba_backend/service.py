"""Services for collecting and serving Sina NBA player data."""

import concurrent.futures
import hashlib
import json
import os
import re
import sqlite3
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime
from html.parser import HTMLParser

from flask import current_app, g


SINA_API_URL = 'https://slamdunk.sports.sina.com.cn/api'
SINA_PLAYER_PAGE = 'https://slamdunk.sports.sina.com.cn/player?pid={pid}'
ZHIBO8_2026_ROOKIES_URL = 'https://news.zhibo8.com/nba/2026-06-24/6a3b1f07f33eenative.htm'
ROOKIE_2026_TEAM_TID = 'rookies-2026'
ROOKIE_2026_TEAM_MARKET = '2026'
ROOKIE_2026_TEAM_NAME = '新秀'
ROOKIE_2026_TEAM_FULL_NAME = '2026 新秀'
DEFAULT_TIMEOUT = 20
DEFAULT_CONCURRENCY = 8
MAX_CONCURRENCY = 16
MAX_BATCH_PLAYER_PIDS = 50
VALID_PLAYER_CARD_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')
TEAM_IMAGE_NAMES_BY_FULL_NAME = {
    '亚特兰大老鹰': 'Atlanta Hawks',
    '波士顿凯尔特人': 'Boston Celtics',
    '布鲁克林篮网': 'Brooklyn Nets',
    '夏洛特黄蜂': 'Charlotte Hornets',
    '芝加哥公牛': 'Chicago Bulls',
    '克利夫兰骑士': 'Cleveland Cavaliers',
    '达拉斯独行侠': 'Dallas Mavericks',
    '丹佛掘金': 'Denver Nuggets',
    '底特律活塞': 'Detroit Pistons',
    '金州勇士': 'Golden State Warriors',
    '休斯顿火箭': 'Houston Rockets',
    '印第安纳步行者': 'Indiana Pacers',
    '洛杉矶快船': 'LA Clippers',
    '洛杉矶湖人': 'Los Angeles Lakers',
    '孟菲斯灰熊': 'Memphis Grizzlies',
    '迈阿密热火': 'Miami Heat',
    '密尔沃基雄鹿': 'Milwaukee Bucks',
    '明尼苏达森林狼': 'Minnesota Timberwolves',
    '新奥尔良鹈鹕': 'New Orleans Pelicans',
    '纽约尼克斯': 'New York Knicks',
    '俄克拉荷马城雷霆': 'Oklahoma City Thunder',
    '奥兰多魔术': 'Orlando Magic',
    '费城76人': 'Philadelphia 76ers',
    '菲尼克斯太阳': 'Phoenix Suns',
    '波特兰开拓者': 'Portland Trail Blazers',
    '萨克拉门托国王': 'Sacramento Kings',
    '圣安东尼奥马刺': 'San Antonio Spurs',
    '多伦多猛龙': 'Toronto Raptors',
    '犹他爵士': 'Utah Jazz',
    '华盛顿奇才': 'Washington Wizards',
}


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
                extension_json TEXT NOT NULL DEFAULT '{}',
                image_path TEXT NOT NULL DEFAULT '',
                image_filename TEXT NOT NULL DEFAULT '',
                image_url TEXT NOT NULL DEFAULT '',
                image_missing INTEGER NOT NULL DEFAULT 1,
                image_checked_at TEXT NOT NULL DEFAULT '',
                avatar_path TEXT NOT NULL DEFAULT '',
                avatar_filename TEXT NOT NULL DEFAULT '',
                avatar_url TEXT NOT NULL DEFAULT '',
                avatar_missing INTEGER NOT NULL DEFAULT 1,
                avatar_checked_at TEXT NOT NULL DEFAULT '',
                team_image_path TEXT NOT NULL DEFAULT '',
                team_image_filename TEXT NOT NULL DEFAULT '',
                team_image_url TEXT NOT NULL DEFAULT '',
                team_image_missing INTEGER NOT NULL DEFAULT 1,
                team_image_checked_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_nba_players_team ON nba_players(team_tid);
            CREATE INDEX IF NOT EXISTS idx_nba_players_chinese_name ON nba_players(chinese_name);
            CREATE INDEX IF NOT EXISTS idx_nba_players_english_name ON nba_players(english_name);

            CREATE TABLE IF NOT EXISTS nba_player_cards (
                card_id TEXT PRIMARY KEY,
                pid TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                season TEXT NOT NULL DEFAULT '',
                series TEXT NOT NULL DEFAULT '',
                variant TEXT NOT NULL DEFAULT '',
                rarity TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 10,
                image_path TEXT NOT NULL DEFAULT '',
                image_filename TEXT NOT NULL DEFAULT '',
                image_url TEXT NOT NULL DEFAULT '',
                image_missing INTEGER NOT NULL DEFAULT 1,
                image_checked_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (pid) REFERENCES nba_players(pid) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_nba_player_cards_pid_order
            ON nba_player_cards(pid, sort_order, created_at, card_id);
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
        'avatar_path': "TEXT NOT NULL DEFAULT ''",
        'avatar_filename': "TEXT NOT NULL DEFAULT ''",
        'avatar_url': "TEXT NOT NULL DEFAULT ''",
        'avatar_missing': 'INTEGER NOT NULL DEFAULT 1',
        'avatar_checked_at': "TEXT NOT NULL DEFAULT ''",
        'team_image_path': "TEXT NOT NULL DEFAULT ''",
        'team_image_filename': "TEXT NOT NULL DEFAULT ''",
        'team_image_url': "TEXT NOT NULL DEFAULT ''",
        'team_image_missing': 'INTEGER NOT NULL DEFAULT 1',
        'team_image_checked_at': "TEXT NOT NULL DEFAULT ''",
        'extension_json': "TEXT NOT NULL DEFAULT '{}'",
    }
    for name, definition in columns.items():
        if not has_column(conn, 'nba_players', name):
            conn.execute('ALTER TABLE nba_players ADD COLUMN {} {}'.format(name, definition))
    conn.executescript(
        '''
        CREATE TABLE IF NOT EXISTS nba_player_cards (
            card_id TEXT PRIMARY KEY,
            pid TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            season TEXT NOT NULL DEFAULT '',
            series TEXT NOT NULL DEFAULT '',
            variant TEXT NOT NULL DEFAULT '',
            rarity TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 10,
            image_path TEXT NOT NULL DEFAULT '',
            image_filename TEXT NOT NULL DEFAULT '',
            image_url TEXT NOT NULL DEFAULT '',
            image_missing INTEGER NOT NULL DEFAULT 1,
            image_checked_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (pid) REFERENCES nba_players(pid) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_nba_player_cards_pid_order
        ON nba_player_cards(pid, sort_order, created_at, card_id);
        '''
    )
    backfill_default_player_cards(conn)


def row_to_player(row, cards=None):
    if row is None:
        return None
    item = dict(row)
    extension = load_json_object(item.get('extension_json'), {})
    for key in ('age', 'experience', 'height_cm', 'weight_kg'):
        if item.get(key) is not None:
            item[key] = int(item[key])
    for key in ('salary_wan_usd', 'avg_points', 'avg_rebounds', 'avg_assists', 'avg_steals', 'avg_blocks'):
        if item.get(key) is not None:
            item[key] = float(item[key])
    item['source'] = extension.get('source') or 'sina_nba'
    item['extension'] = extension
    item['team'] = {
        'tid': item.get('team_tid') or '',
        'market': item.get('team_market') or '',
        'name': item.get('team_name') or '',
        'full_name': item.get('team_full_name') or '',
        'logo': {
            'filename': item.get('team_image_filename') or '',
            'url': item.get('team_image_url') or '',
            'missing': bool(item.get('team_image_missing')),
            'checked_at': item.get('team_image_checked_at') or '',
        },
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
    legacy_image = {
        'filename': item.get('image_filename') or '',
        'url': item.get('image_url') or '',
        'missing': bool(item.get('image_missing')),
        'checked_at': item.get('image_checked_at') or '',
    }
    item['image'] = default_player_image(cards, legacy_image) if cards is not None else legacy_image
    if cards is not None:
        item['cards'] = cards
    item['avatar'] = {
        'filename': item.get('avatar_filename') or '',
        'url': item.get('avatar_url') or '',
        'missing': bool(item.get('avatar_missing')),
        'checked_at': item.get('avatar_checked_at') or '',
    }
    item.pop('raw_info_json', None)
    item.pop('raw_stats_json', None)
    item.pop('extension_json', None)
    item.pop('image_path', None)
    item.pop('image_filename', None)
    item.pop('image_url', None)
    item.pop('image_missing', None)
    item.pop('image_checked_at', None)
    item.pop('avatar_path', None)
    item.pop('avatar_filename', None)
    item.pop('avatar_url', None)
    item.pop('avatar_missing', None)
    item.pop('avatar_checked_at', None)
    item.pop('team_image_path', None)
    item.pop('team_image_filename', None)
    item.pop('team_image_url', None)
    item.pop('team_image_missing', None)
    item.pop('team_image_checked_at', None)
    return item


def player_asset_from_card(row):
    return {
        'filename': row['image_filename'] or '',
        'url': row['image_url'] or '',
        'missing': bool(row['image_missing']),
        'checked_at': row['image_checked_at'] or '',
    }


def row_to_player_card(row):
    return {
        'cardId': row['card_id'],
        'pid': row['pid'],
        'title': row['title'] or '',
        'season': row['season'] or '',
        'series': row['series'] or '',
        'variant': row['variant'] or '',
        'rarity': row['rarity'] or '',
        'sortOrder': int(row['sort_order']),
        'image': player_asset_from_card(row),
        'created_at': row['created_at'] or '',
        'updated_at': row['updated_at'] or '',
    }


def default_player_image(cards, fallback):
    cards = cards or []
    for card in cards:
        image = card.get('image') or {}
        if image.get('url') and not image.get('missing'):
            return image
    if cards:
        return cards[0].get('image') or fallback
    return fallback


def backfill_default_player_cards(conn):
    now = utcnow_iso()
    conn.execute(
        '''
        INSERT OR IGNORE INTO nba_player_cards (
            card_id, pid, title, season, series, variant, rarity, sort_order,
            image_path, image_filename, image_url, image_missing, image_checked_at,
            created_at, updated_at
        )
        SELECT
            pid || '_default',
            pid,
            'Default Card',
            '',
            'Base',
            'default',
            '',
            10,
            image_path,
            image_filename,
            image_url,
            image_missing,
            image_checked_at,
            COALESCE(NULLIF(created_at, ''), ?),
            COALESCE(NULLIF(updated_at, ''), ?)
        FROM nba_players
        WHERE image_filename != '' OR image_url != '' OR image_checked_at != ''
        ''',
        (now, now),
    )


def normalize_player_pid_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        source = value.split(',')
    else:
        source = value
    if not isinstance(source, list):
        raise ValueError('invalid player pid list')
    seen = set()
    pids = []
    for item in source:
        if not isinstance(item, str):
            raise ValueError('invalid player pid list')
        pid = item.strip()
        if pid and pid not in seen:
            seen.add(pid)
            pids.append(pid)
    return pids


def normalize_player_pid(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError('invalid player pid')
    return value.strip() or None


def normalize_card_id(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError('invalid card id')
    return value.strip() or None


def normalize_card_selection(value):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError('invalid card selection')
    result = {}
    for raw_pid, raw_card_id in value.items():
        if not isinstance(raw_pid, str) or not isinstance(raw_card_id, str):
            raise ValueError('invalid card selection')
        pid = raw_pid.strip()
        card_id = raw_card_id.strip()
        if not pid or not card_id:
            raise ValueError('invalid card selection')
        result[pid] = card_id
    return result


def home_cards_hash(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return 'home_' + hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]


def player_card_render_version(card):
    if card is None:
        return None
    return {
        'cardId': card['card_id'],
        'pid': card['pid'],
        'title': card['title'],
        'season': card['season'],
        'series': card['series'],
        'variant': card['variant'],
        'rarity': card['rarity'],
        'sortOrder': card['sort_order'],
        'image': {
            'filename': card['image_filename'],
            'url': card['image_url'],
            'missing': bool(card['image_missing']),
            'checked_at': card['image_checked_at'],
        },
        'updated_at': card['updated_at'],
    }


def player_render_version(row, cards=None):
    if row is None:
        return None
    extension = load_json_object(row['extension_json'], {})
    return {
        'pid': row['pid'],
        'updated_at': row['updated_at'],
        'chinese_name': row['chinese_name'],
        'english_name': row['english_name'],
        'first_name': row['first_name'],
        'last_name': row['last_name'],
        'first_name_cn': row['first_name_cn'],
        'last_name_cn': row['last_name_cn'],
        'jersey_number': row['jersey_number'],
        'primary_position': row['primary_position'],
        'position': row['position'],
        'team_tid': row['team_tid'],
        'team_market': row['team_market'],
        'team_name': row['team_name'],
        'team_full_name': row['team_full_name'],
        'team_image_filename': row['team_image_filename'],
        'team_image_url': row['team_image_url'],
        'team_image_missing': bool(row['team_image_missing']),
        'birthdate': row['birthdate'],
        'age': row['age'],
        'nation': row['nation'],
        'college': row['college'],
        'experience': row['experience'],
        'draft_year': row['draft_year'],
        'draft_round': row['draft_round'],
        'draft_pick': row['draft_pick'],
        'height_cm': row['height_cm'],
        'weight_kg': row['weight_kg'],
        'wingspan': row['wingspan'],
        'standing_reach': row['standing_reach'],
        'current_salary': row['current_salary'],
        'salary_wan_usd': row['salary_wan_usd'],
        'avg_points': row['avg_points'],
        'avg_rebounds': row['avg_rebounds'],
        'avg_assists': row['avg_assists'],
        'avg_steals': row['avg_steals'],
        'avg_blocks': row['avg_blocks'],
        'extension': extension,
        'image_filename': row['image_filename'],
        'image_url': row['image_url'],
        'image_missing': bool(row['image_missing']),
        'avatar_filename': row['avatar_filename'],
        'avatar_url': row['avatar_url'],
        'avatar_missing': bool(row['avatar_missing']),
        'cards': [
            player_card_render_version(card)
            for card in (cards or [])
        ],
    }


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


def load_json_object(raw, default_value):
    try:
        value = json.loads(raw or '{}')
    except (TypeError, json.JSONDecodeError):
        return dict(default_value)
    if not isinstance(value, dict):
        return dict(default_value)
    return value


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
    spaced = re.sub(r'([a-z])\.([a-z])\.?', r'\1 \2 ', text)
    spaced = spaced.replace("'", ' ').replace('-', ' ')
    variants.add(alnum(spaced))
    variants.add(alnum(re.sub(r'\b(jr|ii|iii|iv)\b', '', spaced)))

    tokens = [token for token in re.split(r'[^a-z0-9]+', spaced) if token]
    add_name_token_variants(tokens, variants)
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


def add_name_token_variants(tokens, variants):
    if len(tokens) < 2:
        return
    suffixes = {'jr', 'ii', 'iii', 'iv'}
    clean_tokens = [token for token in tokens if token not in suffixes]
    if len(clean_tokens) < 2:
        return

    first = clean_tokens[0]
    last = clean_tokens[-1]
    variants.add(first + last)
    if len(clean_tokens) > 2:
        variants.add(first + clean_tokens[1] + last)

    aliases = {
        ('alexandre',): ('alex',),
        ('cameron',): ('cam',),
        ('nah', 'shon'): ('bones',),
    }
    for source, replacements in aliases.items():
        if tuple(clean_tokens[:len(source)]) != source:
            continue
        tail = clean_tokens[len(source):]
        for replacement in replacements:
            variants.add(replacement + ''.join(tail))
            if tail:
                variants.add(replacement + tail[-1])


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


def safe_card_id(value):
    card_id = re.sub(r'[^A-Za-z0-9_-]+', '_', str(value or '')).strip('_')
    return card_id or 'card'


def card_title(season='', series='', variant=''):
    parts = [season, series, variant]
    return ' '.join(part for part in parts if part) or 'Default Card'


def parse_pid_card_filename(filename, pid):
    basename = os.path.basename(str(filename or ''))
    stem, ext = os.path.splitext(basename)
    if ext.lower() not in VALID_PLAYER_CARD_EXTENSIONS:
        return None
    if stem == pid:
        suffix = 'default'
    elif stem.startswith(pid + '_'):
        suffix = stem[len(pid) + 1:]
    else:
        return None

    suffix = suffix.strip('_')
    if not suffix:
        suffix = 'default'
    tokens = [token for token in suffix.split('_') if token]
    if tokens == ['default']:
        return {
            'card_id': safe_card_id(pid + '_default'),
            'title': 'Default Card',
            'season': '',
            'series': 'Base',
            'variant': 'default',
            'rarity': '',
            'sort_order': 10,
        }

    season = tokens[0] if tokens else ''
    variant = tokens[-1] if len(tokens) > 1 else 'default'
    series = ' '.join(tokens[1:-1]) if len(tokens) > 2 else ''
    return {
        'card_id': safe_card_id(stem),
        'title': card_title(season, series, variant),
        'season': season,
        'series': series,
        'variant': variant,
        'rarity': '',
        'sort_order': 20,
    }


def parse_english_card_filename(filename, english_name, pid):
    basename = os.path.basename(str(filename or ''))
    stem, ext = os.path.splitext(basename)
    if ext.lower() not in VALID_PLAYER_CARD_EXTENSIONS:
        return None

    suffix_number = None
    base_stem = stem
    match = re.match(r'^(.+)_([1-9][0-9]*)$', stem)
    if match:
        base_stem = match.group(1)
        suffix_number = int(match.group(2))

    if not image_name_variants(base_stem).intersection(image_name_variants(english_name)):
        return None

    if suffix_number is None:
        return {
            'card_id': safe_card_id(pid + '_default'),
            'title': 'Default Card',
            'season': '',
            'series': 'Base',
            'variant': 'default',
            'rarity': '',
            'sort_order': 10,
        }

    return {
        'card_id': safe_card_id('{}_{}'.format(pid, suffix_number)),
        'title': 'Card {}'.format(suffix_number + 1),
        'season': '',
        'series': 'Base',
        'variant': str(suffix_number),
        'rarity': '',
        'sort_order': (suffix_number + 1) * 10,
    }


def player_card_upload_naming_rule():
    return {
        'preferred': 'English_Name.{ext}, English_Name_1.{ext}, English_Name_2.{ext}',
        'default': 'English_Name.{ext}',
        'numbered': 'English_Name_{n}.{ext}',
        'pidPreferred': '{pid}_{season}_{variant}.{ext}',
        'pidDefault': '{pid}_default.{ext}',
        'extended': '{pid}_{season}_{series}_{variant}.{ext}',
        'notes': [
            'English_Name.{ext} is the default card.',
            'English_Name_1.{ext} is the second card; English_Name_2.{ext} is the third card.',
            'Keep the same base English name used by the existing default card.',
            'The backend cardId remains pid-based internally to avoid duplicate player names colliding.',
        ],
    }


def collect_pid_card_files(image_dir, pids):
    cards_by_pid = {pid: [] for pid in pids}
    if not image_dir or not os.path.isdir(image_dir):
        return cards_by_pid
    for filename in sorted(os.listdir(image_dir)):
        path = os.path.join(image_dir, filename)
        if not os.path.isfile(path):
            continue
        for pid in pids:
            card = parse_pid_card_filename(filename, pid)
            if card:
                card['filename'] = filename
                cards_by_pid[pid].append(card)
                break
    def card_sort_key(card):
        variant = str(card.get('variant') or '').lower()
        variant_rank = {'default': 0, 'base': 1}.get(variant, 2)
        return card['sort_order'], variant_rank, card['filename'], card['card_id']

    for cards in cards_by_pid.values():
        cards.sort(key=card_sort_key)
        has_default = any(card['variant'] == 'default' for card in cards)
        non_default_index = 0
        for card in cards:
            if card['variant'] == 'default':
                card['sort_order'] = 10
            elif card['sort_order'] == 20:
                non_default_index += 1
                card['sort_order'] = (non_default_index + (1 if has_default else 0)) * 10
    return cards_by_pid


def collect_english_card_files(image_dir, rows):
    cards_by_pid = {row['pid']: [] for row in rows}
    if not image_dir or not os.path.isdir(image_dir):
        return cards_by_pid
    for filename in sorted(os.listdir(image_dir)):
        path = os.path.join(image_dir, filename)
        if not os.path.isfile(path):
            continue
        for row in rows:
            card = parse_english_card_filename(filename, row['english_name'], row['pid'])
            if card:
                card['filename'] = filename
                cards_by_pid[row['pid']].append(card)
                break
    for cards in cards_by_pid.values():
        cards.sort(key=lambda card: (card['sort_order'], card['filename'], card['card_id']))
    return cards_by_pid


def player_card_record(row, card, image_dir, url_prefix, now):
    filename = card['filename']
    image_path = os.path.abspath(os.path.join(image_dir, filename))
    image_url = url_prefix.rstrip('/') + '/' + urllib.parse.quote(filename)
    return {
        'card_id': card['card_id'],
        'pid': row['pid'],
        'title': card['title'],
        'season': card['season'],
        'series': card['series'],
        'variant': card['variant'],
        'rarity': card['rarity'],
        'sort_order': card['sort_order'],
        'image_path': image_path,
        'image_filename': filename,
        'image_url': image_url,
        'image_missing': 0,
        'image_checked_at': now,
        'created_at': now,
        'updated_at': now,
    }


def legacy_default_card(row, filename, image_dir, url_prefix, now):
    return player_card_record(
        row,
        {
            'card_id': safe_card_id(row['pid'] + '_default'),
            'title': 'Default Card',
            'season': '',
            'series': 'Base',
            'variant': 'default',
            'rarity': '',
            'sort_order': 10,
            'filename': filename,
        },
        image_dir,
        url_prefix,
        now,
    )


def insert_player_card(conn, record):
    conn.execute(
        '''
        INSERT INTO nba_player_cards (
            card_id, pid, title, season, series, variant, rarity, sort_order,
            image_path, image_filename, image_url, image_missing, image_checked_at,
            created_at, updated_at
        ) VALUES (
            :card_id, :pid, :title, :season, :series, :variant, :rarity, :sort_order,
            :image_path, :image_filename, :image_url, :image_missing, :image_checked_at,
            :created_at, :updated_at
        )
        ON CONFLICT(card_id) DO UPDATE SET
            pid=excluded.pid,
            title=excluded.title,
            season=excluded.season,
            series=excluded.series,
            variant=excluded.variant,
            rarity=excluded.rarity,
            sort_order=excluded.sort_order,
            image_path=excluded.image_path,
            image_filename=excluded.image_filename,
            image_url=excluded.image_url,
            image_missing=excluded.image_missing,
            image_checked_at=excluded.image_checked_at,
            updated_at=excluded.updated_at
        ''',
        record,
    )


def set_player_legacy_image_from_card(conn, pid, card_record, now):
    if card_record:
        conn.execute(
            '''
            UPDATE nba_players
            SET image_path=?, image_filename=?, image_url=?, image_missing=0,
                image_checked_at=?, updated_at=?
            WHERE pid=?
            ''',
            (
                card_record['image_path'],
                card_record['image_filename'],
                card_record['image_url'],
                card_record['image_checked_at'],
                now,
                pid,
            ),
        )
        return
    conn.execute(
        '''
        UPDATE nba_players
        SET image_path='', image_filename='', image_url='', image_missing=1,
            image_checked_at=?, updated_at=?
        WHERE pid=?
        ''',
        (now, now, pid),
    )


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


class Zhibo8ParagraphParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_p = False
        self.in_a = False
        self.current_text = []
        self.current_links = []
        self.link_href = ''
        self.link_text = []
        self.paragraphs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'p':
            self.in_p = True
            self.current_text = []
            self.current_links = []
        elif tag == 'a' and self.in_p:
            self.in_a = True
            self.link_href = attrs.get('href') or ''
            self.link_text = []

    def handle_endtag(self, tag):
        if tag == 'a' and self.in_a:
            text = normalize_whitespace(''.join(self.link_text))
            if text or self.link_href:
                self.current_links.append({
                    'url': self.link_href,
                    'title': text,
                })
            self.in_a = False
            self.link_href = ''
            self.link_text = []
        elif tag == 'p' and self.in_p:
            self.paragraphs.append({
                'text': normalize_whitespace(''.join(self.current_text)),
                'links': list(self.current_links),
            })
            self.in_p = False
            self.current_text = []
            self.current_links = []

    def handle_data(self, data):
        if self.in_p:
            self.current_text.append(data)
        if self.in_a:
            self.link_text.append(data)


def normalize_whitespace(value):
    return re.sub(r'\s+', ' ', str(value or '').replace('\xa0', ' ')).strip()


def fetch_zhibo8_html(url, timeout=DEFAULT_TIMEOUT):
    request = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html,application/xhtml+xml',
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or 'utf-8'
        return response.read().decode(charset, errors='ignore')


def parse_zhibo8_paragraphs(html):
    parser = Zhibo8ParagraphParser()
    parser.feed(html or '')
    return parser.paragraphs


def zhibo8_absolute_url(url):
    if not url:
        return ''
    if url.startswith('//'):
        return 'https:' + url
    return urllib.parse.urljoin(ZHIBO8_2026_ROOKIES_URL, url)


def parse_2026_rookie_summary_line(text):
    match = re.match(r'^(\d+)、(.+?)\s+(\S+)\s+(.+)$', normalize_whitespace(text))
    if not match:
        return None
    pick = to_int(match.group(1))
    if not pick:
        return None
    selection_text = match.group(4).strip()
    return {
        'draft_pick': pick,
        'listed_name': match.group(2).strip(),
        'listed_position': match.group(3).strip(),
        'selection_text': selection_text,
        'selected_team': final_selected_team(selection_text),
    }


def final_selected_team(selection_text):
    text = normalize_whitespace(selection_text)
    trade_targets = re.findall(r'(?:送往|送去|送至|交易去|交易至|交易到|转送|送给|加盟)([\u4e00-\u9fa5A-Za-z0-9]+)', text)
    if trade_targets:
        return cleanup_team_name(trade_targets[-1])
    return cleanup_team_name(re.split(r'[（(]', text, 1)[0])


def cleanup_team_name(value):
    return re.sub(r'[，,。.；;：:、\s].*$', '', str(value or '')).strip()


def parse_2026_rookie_summaries(html):
    paragraphs = parse_zhibo8_paragraphs(html)
    summaries = []
    for index, paragraph in enumerate(paragraphs):
        summary = parse_2026_rookie_summary_line(paragraph['text'])
        if not summary:
            continue
        tag = {}
        for next_paragraph in paragraphs[index + 1:index + 4]:
            if next_paragraph['links']:
                link = next_paragraph['links'][0]
                tag = {
                    'title': link.get('title') or next_paragraph['text'],
                    'url': zhibo8_absolute_url(link.get('url') or ''),
                }
                break
            if parse_2026_rookie_summary_line(next_paragraph['text']):
                break
        summary['tag'] = tag
        summaries.append(summary)
    return summaries


def parse_2026_rookie_detail(html):
    paragraphs = parse_zhibo8_paragraphs(html)
    fields = {}
    stats_text = ''
    previous_label = ''
    for paragraph in paragraphs:
        text = paragraph['text']
        if not text:
            continue
        if '：' in text:
            key, value = text.split('：', 1)
            key = key.strip()
            value = value.strip()
            if key == '数据统计':
                previous_label = key
                if value:
                    stats_text = value
                continue
            if key and value:
                fields[key] = value
                previous_label = ''
                continue
        if previous_label == '数据统计' and not stats_text:
            stats_text = text
            previous_label = ''
    chinese_name, english_name = split_rookie_name(fields.get('姓名', ''))
    university_team = fields.get('大学球队') or fields.get('球队') or ''
    return {
        'chinese_name': chinese_name,
        'english_name': english_name,
        'birthdate': fields.get('出生日期') or '',
        'position': fields.get('位置') or '',
        'university_team': university_team,
        'height': fields.get('身高') or fields.get('裸足身高') or '',
        'weight': fields.get('体重') or '',
        'wingspan': fields.get('臂展') or '',
        'player_template': fields.get('球员模板') or '',
        'stats_text': stats_text,
    }


def split_rookie_name(value):
    value = normalize_whitespace(value)
    match = re.match(r'^(.+?)（(.+?)）$', value)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return value, ''


def parse_metric_cm(value):
    match = re.search(r'（(\d+)米(\d+)）', str(value or ''))
    if match:
        return int(match.group(1)) * 100 + int(match.group(2))
    match = re.search(r'（(\d+)cm）', str(value or ''), re.I)
    if match:
        return int(match.group(1))
    return None


def parse_metric_kg(value):
    match = re.search(r'（(\d+)公斤）', str(value or ''))
    if match:
        return int(match.group(1))
    return None


def rookie_pid(pick, english_name, tag_url):
    source = english_name or tag_url or str(pick)
    safe = re.sub(r'[^a-z0-9]+', '-', strip_accents(source).lower()).strip('-')
    if not safe:
        safe = 'pick-{}'.format(pick)
    return 'rookie-2026-{:02d}-{}'.format(pick, safe[:48])


def build_2026_rookie_record(summary, detail, tag_url):
    now = utcnow_iso()
    chinese_name = detail.get('chinese_name') or summary.get('listed_name') or ''
    english_name = detail.get('english_name') or ''
    english_parts = [part for part in re.split(r'\s+', english_name) if part]
    extension = {
        'source': 'zhibo8_2026_rookies',
        'rookie': {
            'draft_year': 2026,
            'draft_pick': summary['draft_pick'],
            'listed_name': summary.get('listed_name') or '',
            'listed_position': summary.get('listed_position') or '',
            'selection_text': summary.get('selection_text') or '',
            'selected_team': summary.get('selected_team') or '',
            'tag': summary.get('tag') or {},
            'university_team': detail.get('university_team') or '',
            'height': detail.get('height') or '',
            'weight': detail.get('weight') or '',
            'wingspan': detail.get('wingspan') or '',
            'player_template': detail.get('player_template') or '',
            'stats_text': detail.get('stats_text') or '',
        },
    }
    return {
        'pid': rookie_pid(summary['draft_pick'], english_name, tag_url),
        'first_name': english_parts[0] if english_parts else '',
        'last_name': ' '.join(english_parts[1:]) if len(english_parts) > 1 else '',
        'first_name_cn': chinese_name,
        'last_name_cn': '',
        'chinese_name': chinese_name,
        'english_name': english_name,
        'team_tid': ROOKIE_2026_TEAM_TID,
        'team_market': ROOKIE_2026_TEAM_MARKET,
        'team_name': ROOKIE_2026_TEAM_NAME,
        'team_full_name': ROOKIE_2026_TEAM_FULL_NAME,
        'jersey_number': str(summary['draft_pick']),
        'primary_position': detail.get('position') or summary.get('listed_position') or '',
        'position': detail.get('position') or summary.get('listed_position') or '',
        'birthdate': detail.get('birthdate') or '',
        'age': None,
        'nation': '',
        'college': detail.get('university_team') or '',
        'experience': None,
        'draft_year': '2026',
        'draft_round': '1',
        'draft_pick': str(summary['draft_pick']),
        'height_cm': parse_metric_cm(detail.get('height')),
        'weight_kg': parse_metric_kg(detail.get('weight')),
        'wingspan': detail.get('wingspan') or '',
        'standing_reach': '',
        'salary_wan_usd': None,
        'current_salary': '',
        'avg_points': None,
        'avg_rebounds': None,
        'avg_assists': None,
        'avg_steals': None,
        'avg_blocks': None,
        'source_url': tag_url,
        'source_updated_at': now,
        'raw_info_json': json.dumps({'summary': summary, 'detail': detail}, ensure_ascii=False, sort_keys=True),
        'raw_stats_json': '{}',
        'extension_json': json.dumps(extension, ensure_ascii=False, sort_keys=True),
        'created_at': now,
        'updated_at': now,
    }


def collect_2026_rookies(draft_url=ZHIBO8_2026_ROOKIES_URL):
    draft_html = fetch_zhibo8_html(draft_url)
    records = []
    errors = []
    for summary in parse_2026_rookie_summaries(draft_html):
        tag_url = (summary.get('tag') or {}).get('url') or ''
        if not tag_url:
            errors.append({'draft_pick': summary['draft_pick'], 'error': 'missing rookie detail link'})
            continue
        try:
            detail = parse_2026_rookie_detail(fetch_zhibo8_html(tag_url))
            records.append(build_2026_rookie_record(summary, detail, tag_url))
        except Exception as exc:
            errors.append({'draft_pick': summary['draft_pick'], 'url': tag_url, 'error': str(exc)})
    return records, errors


def sync_2026_rookies(conn, draft_url=ZHIBO8_2026_ROOKIES_URL):
    started = time.time()
    records, errors = collect_2026_rookies(draft_url)
    for player in records:
        upsert_player(conn, player)
    conn.commit()
    return {
        'source_url': draft_url,
        'team_full_name': ROOKIE_2026_TEAM_FULL_NAME,
        'requested_count': len(records) + len(errors),
        'succeeded_count': len(records),
        'failed_count': len(errors),
        'errors': errors,
        'elapsed_seconds': round(time.time() - started, 3),
    }


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
        'extension_json': '{}',
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
            source_updated_at, raw_info_json, raw_stats_json, extension_json, created_at, updated_at
        ) VALUES (
            :pid, :first_name, :last_name, :first_name_cn, :last_name_cn, :chinese_name, :english_name,
            :team_tid, :team_market, :team_name, :team_full_name, :jersey_number, :primary_position, :position,
            :birthdate, :age, :nation, :college, :experience, :draft_year, :draft_round, :draft_pick,
            :height_cm, :weight_kg, :wingspan, :standing_reach, :salary_wan_usd, :current_salary,
            :avg_points, :avg_rebounds, :avg_assists, :avg_steals, :avg_blocks, :source_url,
            :source_updated_at, :raw_info_json, :raw_stats_json, :extension_json, :created_at, :updated_at
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
            extension_json=excluded.extension_json,
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


def sync_player_assets(conn, asset_dir, column_prefix, url_prefix):
    image_index, collisions = collect_image_index(asset_dir)
    now = utcnow_iso()
    matched = 0
    missing = []
    path_column = column_prefix + '_path'
    filename_column = column_prefix + '_filename'
    url_column = column_prefix + '_url'
    missing_column = column_prefix + '_missing'
    checked_column = column_prefix + '_checked_at'
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
            image_path = os.path.abspath(os.path.join(asset_dir, filename))
            image_url = url_prefix.rstrip('/') + '/' + urllib.parse.quote(filename)
            conn.execute(
                '''
                UPDATE nba_players
                SET {path_column}=?, {filename_column}=?, {url_column}=?, {missing_column}=0,
                    {checked_column}=?, updated_at=?
                WHERE pid=?
                '''.format(
                    path_column=path_column,
                    filename_column=filename_column,
                    url_column=url_column,
                    missing_column=missing_column,
                    checked_column=checked_column,
                ),
                (image_path, filename, image_url, now, now, row['pid']),
            )
            matched += 1
            continue
        conn.execute(
            '''
            UPDATE nba_players
            SET {path_column}='', {filename_column}='', {url_column}='', {missing_column}=1,
                {checked_column}=?, updated_at=?
            WHERE pid=?
            '''.format(
                path_column=path_column,
                filename_column=filename_column,
                url_column=url_column,
                missing_column=missing_column,
                checked_column=checked_column,
            ),
            (now, now, row['pid']),
        )
        missing.append({
            'pid': row['pid'],
            'chinese_name': row['chinese_name'],
            'english_name': row['english_name'],
        })
    conn.commit()
    asset_count = len(set(image_index.values()))
    result = {
        'total': len(rows),
        'asset_count': asset_count,
        'matched_count': matched,
        'missing_count': len(missing),
        'missing': missing,
        'collisions': [
            {'key': key, 'filenames': sorted(value)}
            for key, value in sorted(collisions.items())
        ],
        'checked_at': now,
    }
    if column_prefix == 'image':
        result['image_count'] = asset_count
    if column_prefix == 'avatar':
        result['avatar_count'] = asset_count
    return result


def sync_player_images(conn, image_dir, url_prefix='/api/nba/card-images'):
    image_index, collisions = collect_image_index(image_dir)
    now = utcnow_iso()
    rows = conn.execute(
        '''
        SELECT pid, chinese_name, english_name
        FROM nba_players
        ORDER BY team_full_name ASC, chinese_name ASC
        '''
    ).fetchall()
    cards_by_pid = collect_pid_card_files(image_dir, [row['pid'] for row in rows])
    english_cards_by_pid = collect_english_card_files(image_dir, rows)
    matched = 0
    card_count = 0
    missing = []

    for row in rows:
        existing_created_at = {
            existing['card_id']: existing['created_at']
            for existing in conn.execute(
                'SELECT card_id, created_at FROM nba_player_cards WHERE pid=?',
                (row['pid'],),
            ).fetchall()
        }
        records = [
            player_card_record(row, card, image_dir, url_prefix, now)
            for card in english_cards_by_pid.get(row['pid'], []) + cards_by_pid.get(row['pid'], [])
        ]
        legacy_filename = match_image_filename(row['english_name'], image_index)
        if legacy_filename and not any(record['image_filename'] == legacy_filename for record in records):
            default_card_id = safe_card_id(row['pid'] + '_default')
            if not any(record['card_id'] == default_card_id for record in records):
                records.insert(0, legacy_default_card(row, legacy_filename, image_dir, url_prefix, now))

        for record in records:
            record['created_at'] = existing_created_at.get(record['card_id'], record['created_at'])
        records.sort(key=lambda record: (record['sort_order'], record['created_at'], record['card_id']))
        conn.execute('DELETE FROM nba_player_cards WHERE pid=?', (row['pid'],))
        for record in records:
            insert_player_card(conn, record)

        first_valid = next((record for record in records if not record['image_missing']), records[0] if records else None)
        set_player_legacy_image_from_card(conn, row['pid'], first_valid, now)

        if records:
            matched += 1
            card_count += len(records)
            continue
        missing.append({
            'pid': row['pid'],
            'chinese_name': row['chinese_name'],
            'english_name': row['english_name'],
        })

    conn.commit()
    asset_count = len(set(image_index.values()))
    return {
        'total': len(rows),
        'asset_count': asset_count,
        'image_count': asset_count,
        'card_count': card_count,
        'matched_count': matched,
        'missing_count': len(missing),
        'missing': missing,
        'collisions': [
            {'key': key, 'filenames': sorted(value)}
            for key, value in sorted(collisions.items())
        ],
        'checked_at': now,
        'namingRule': player_card_upload_naming_rule(),
    }


def sync_player_avatars(conn, avatar_dir, url_prefix='/api/nba/avatars'):
    return sync_player_assets(conn, avatar_dir, 'avatar', url_prefix)


def team_image_search_values(row):
    full_name = row['team_full_name'] or ''
    values = []
    mapped = TEAM_IMAGE_NAMES_BY_FULL_NAME.get(full_name)
    if mapped:
        values.append(mapped)
    values.extend([
        full_name,
        normalize_name(row['team_market'], row['team_name'], ''),
        row['team_name'] or '',
    ])
    return [value for value in values if value]


def match_team_image_filename(row, image_index):
    for value in team_image_search_values(row):
        filename = match_image_filename(value, image_index)
        if filename:
            return filename
    return ''


def sync_team_images(conn, team_image_dir, url_prefix='/api/nba/team-images'):
    image_index, collisions = collect_image_index(team_image_dir)
    now = utcnow_iso()
    matched = 0
    affected_players = 0
    missing = []
    rows = conn.execute(
        '''
        SELECT team_tid, team_market, team_name, team_full_name, COUNT(*) AS player_count
        FROM nba_players
        WHERE team_tid!=''
        GROUP BY team_tid, team_market, team_name, team_full_name
        ORDER BY team_full_name ASC
        '''
    ).fetchall()
    for row in rows:
        filename = match_team_image_filename(row, image_index)
        if filename:
            image_path = os.path.abspath(os.path.join(team_image_dir, filename))
            image_url = url_prefix.rstrip('/') + '/' + urllib.parse.quote(filename)
            cursor = conn.execute(
                '''
                UPDATE nba_players
                SET team_image_path=?, team_image_filename=?, team_image_url=?, team_image_missing=0,
                    team_image_checked_at=?, updated_at=?
                WHERE team_tid=?
                ''',
                (image_path, filename, image_url, now, now, row['team_tid']),
            )
            matched += 1
            affected_players += cursor.rowcount
            continue
        conn.execute(
            '''
            UPDATE nba_players
            SET team_image_path='', team_image_filename='', team_image_url='', team_image_missing=1,
                team_image_checked_at=?, updated_at=?
            WHERE team_tid=?
            ''',
            (now, now, row['team_tid']),
        )
        missing.append({
            'team_tid': row['team_tid'],
            'team_market': row['team_market'],
            'team_name': row['team_name'],
            'team_full_name': row['team_full_name'],
            'player_count': row['player_count'],
        })
    conn.commit()
    asset_count = len(set(image_index.values()))
    return {
        'total': len(rows),
        'asset_count': asset_count,
        'team_image_count': asset_count,
        'matched_count': matched,
        'missing_count': len(missing),
        'affected_player_count': affected_players,
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


def get_player_card_rows_by_pids(conn, pids):
    pids = normalize_player_pid_list(pids)
    if not pids:
        return {}
    placeholders = ','.join('?' for _ in pids)
    rows = conn.execute(
        '''
        SELECT *
        FROM nba_player_cards
        WHERE pid IN ({})
        ORDER BY pid ASC, sort_order ASC, created_at ASC, card_id ASC
        '''.format(placeholders),
        pids,
    ).fetchall()
    cards_by_pid = {pid: [] for pid in pids}
    for row in rows:
        cards_by_pid.setdefault(row['pid'], []).append(row)
    return cards_by_pid


def get_player_cards(conn, pid):
    return [
        row_to_player_card(row)
        for row in get_player_card_rows_by_pids(conn, [pid]).get(pid, [])
    ]


def list_filter_options(conn):
    team_rows = conn.execute(
        '''
        SELECT team_tid, team_market, team_name, team_full_name, COUNT(*) AS player_count,
               MAX(team_image_filename) AS team_image_filename,
               MAX(team_image_url) AS team_image_url,
               MIN(team_image_missing) AS team_image_missing,
               MAX(team_image_checked_at) AS team_image_checked_at
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
                'logo': {
                    'filename': row['team_image_filename'] or '',
                    'url': row['team_image_url'] or '',
                    'missing': bool(row['team_image_missing']),
                    'checked_at': row['team_image_checked_at'] or '',
                },
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
    if not row:
        return None
    return row_to_player(row, get_player_cards(conn, pid))


def get_player_rows_by_pids(conn, pids):
    pids = normalize_player_pid_list(pids)
    if not pids:
        return {}
    placeholders = ','.join('?' for _ in pids)
    rows = conn.execute(
        'SELECT * FROM nba_players WHERE pid IN ({})'.format(placeholders),
        pids,
    ).fetchall()
    return {row['pid']: row for row in rows}


def home_cards_metadata(conn, app, config, config_updated_at):
    config = config or {}
    pids = normalize_player_pid_list(config.get('associated_home_player_pid'))
    current_pid = normalize_player_pid(config.get('current_home_player_pid'))
    current_card_id = normalize_card_id(config.get('current_home_card_id'))
    card_selection = normalize_card_selection(config.get('home_player_card_selection'))
    player_rows = get_player_rows_by_pids(conn, pids)
    card_rows = get_player_card_rows_by_pids(conn, pids)
    ordered_versions = [
        player_render_version(player_rows.get(pid), card_rows.get(pid, []))
        for pid in pids
    ]
    updated_values = [
        player_rows[pid]['updated_at']
        for pid in pids
        if pid in player_rows and player_rows[pid]['updated_at']
    ]
    card_updated_values = [
        card['updated_at']
        for pid in pids
        for card in card_rows.get(pid, [])
        if card['updated_at']
    ]
    players_updated_at = max(updated_values) if updated_values else None
    cards_updated_at = max(card_updated_values) if card_updated_values else None
    data_version = home_cards_hash({
        'scope': 'homeCards',
        'app': app,
        'pids': pids,
        'currentPid': current_pid,
        'currentCardId': current_card_id,
        'cardSelection': card_selection,
        'configUpdatedAt': config_updated_at,
        'playersUpdatedAt': players_updated_at,
        'cardsUpdatedAt': cards_updated_at,
        # Include render fingerprints so non-max player changes and missing-state changes
        # cannot be hidden behind an unchanged aggregate timestamp.
        'players': ordered_versions,
    })
    return {
        'pids': pids,
        'currentPid': current_pid,
        'currentCardId': current_card_id,
        'cardSelection': card_selection,
        'configUpdatedAt': config_updated_at,
        'playersUpdatedAt': players_updated_at,
        'cardsUpdatedAt': cards_updated_at,
        'dataVersion': data_version,
    }


def list_players_batch(conn, pids):
    pids = normalize_player_pid_list(pids)
    if len(pids) > MAX_BATCH_PLAYER_PIDS:
        raise ValueError('too many pids')
    player_rows = get_player_rows_by_pids(conn, pids)
    card_rows = get_player_card_rows_by_pids(conn, pids)
    items = [
        row_to_player(player_rows[pid], [
            row_to_player_card(card)
            for card in card_rows.get(pid, [])
        ])
        for pid in pids
        if pid in player_rows
    ]
    missing_pids = [
        pid
        for pid in pids
        if pid not in player_rows
    ]
    data_version = home_cards_hash({
        'scope': 'playersBatch',
        'pids': pids,
        'players': [
            player_render_version(player_rows.get(pid), card_rows.get(pid, []))
            for pid in pids
        ],
    })
    return {
        'items': items,
        'missingPids': missing_pids,
        'dataVersion': data_version,
    }


def list_missing_images(conn):
    return list_missing_assets(conn, 'image')


def list_missing_avatars(conn):
    return list_missing_assets(conn, 'avatar')


def list_missing_team_images(conn):
    rows = conn.execute(
        '''
        SELECT team_tid, team_market, team_name, team_full_name, COUNT(*) AS player_count
        FROM nba_players
        WHERE team_tid!='' AND team_image_missing=1
        GROUP BY team_tid, team_market, team_name, team_full_name
        ORDER BY team_full_name ASC
        '''
    ).fetchall()
    return [dict(row) for row in rows]


def list_missing_assets(conn, column_prefix):
    rows = conn.execute(
        '''
        SELECT pid, chinese_name, english_name, team_full_name
        FROM nba_players
        WHERE {missing_column}=1
        ORDER BY team_full_name ASC, chinese_name ASC
        '''.format(missing_column=column_prefix + '_missing')
    ).fetchall()
    return [dict(row) for row in rows]


def nba_sync_token():
    return os.environ.get('NBA_SYNC_TOKEN', '').strip()
