"""SalarySwish salary-cap collection and Mini Program read models."""

import concurrent.futures
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime
from html.parser import HTMLParser


SALARYSWISH_BASE_URL = 'https://www.salaryswish.com'
SALARYSWISH_HOME_URL = SALARYSWISH_BASE_URL + '/'
SALARYSWISH_TIMEOUT = 20
SALARYSWISH_DEFAULT_CONCURRENCY = 4
SALARYSWISH_MAX_CONCURRENCY = 8

TEAM_INFO_BY_SLUG = {
    'hawks': ('Atlanta Hawks', '亚特兰大老鹰', 'ATL'),
    'celtics': ('Boston Celtics', '波士顿凯尔特人', 'BOS'),
    'nets': ('Brooklyn Nets', '布鲁克林篮网', 'BKN'),
    'hornets': ('Charlotte Hornets', '夏洛特黄蜂', 'CHA'),
    'bulls': ('Chicago Bulls', '芝加哥公牛', 'CHI'),
    'cavaliers': ('Cleveland Cavaliers', '克利夫兰骑士', 'CLE'),
    'mavericks': ('Dallas Mavericks', '达拉斯独行侠', 'DAL'),
    'nuggets': ('Denver Nuggets', '丹佛掘金', 'DEN'),
    'pistons': ('Detroit Pistons', '底特律活塞', 'DET'),
    'warriors': ('Golden State Warriors', '金州勇士', 'GSW'),
    'rockets': ('Houston Rockets', '休斯顿火箭', 'HOU'),
    'pacers': ('Indiana Pacers', '印第安纳步行者', 'IND'),
    'clippers': ('LA Clippers', '洛杉矶快船', 'LAC'),
    'lakers': ('Los Angeles Lakers', '洛杉矶湖人', 'LAL'),
    'grizzlies': ('Memphis Grizzlies', '孟菲斯灰熊', 'MEM'),
    'heat': ('Miami Heat', '迈阿密热火', 'MIA'),
    'bucks': ('Milwaukee Bucks', '密尔沃基雄鹿', 'MIL'),
    'timberwolves': ('Minnesota Timberwolves', '明尼苏达森林狼', 'MIN'),
    'pelicans': ('New Orleans Pelicans', '新奥尔良鹈鹕', 'NOP'),
    'knicks': ('New York Knicks', '纽约尼克斯', 'NYK'),
    'thunder': ('Oklahoma City Thunder', '俄克拉荷马城雷霆', 'OKC'),
    'magic': ('Orlando Magic', '奥兰多魔术', 'ORL'),
    'sixers': ('Philadelphia 76ers', '费城76人', 'PHI'),
    'suns': ('Phoenix Suns', '菲尼克斯太阳', 'PHX'),
    'trailblazers': ('Portland Trail Blazers', '波特兰开拓者', 'POR'),
    'kings': ('Sacramento Kings', '萨克拉门托国王', 'SAC'),
    'spurs': ('San Antonio Spurs', '圣安东尼奥马刺', 'SAS'),
    'raptors': ('Toronto Raptors', '多伦多猛龙', 'TOR'),
    'jazz': ('Utah Jazz', '犹他爵士', 'UTA'),
    'wizards': ('Washington Wizards', '华盛顿奇才', 'WAS'),
}

TEAM_CN_BY_EN = {
    team_en: team_cn
    for team_en, team_cn, _abbr in TEAM_INFO_BY_SLUG.values()
}
TEAM_CN_BY_EN.update({'Los Angeles Clippers': '洛杉矶快船'})

TEAM_SLUG_ALIASES = {
    '76ers': 'sixers',
    'trail-blazers': 'trailblazers',
}

SUMMARY_LABELS = {
    'CAP HIT': ('cap_hit', '工资帽占用'),
    'CAP ROOM': ('cap_room', '薪资空间'),
    'TEAM SALARY': ('team_salary', '球队薪资'),
    'TEAM SALARY ROOM': ('team_salary_room', '球队薪资空间'),
    'LUXURY TAX ROOM': ('luxury_tax_room', '奢侈税空间'),
    '1ST APRON ROOM': ('first_apron_room', '第一土豪线空间'),
    '2ND APRON ROOM': ('second_apron_room', '第二土豪线空间'),
    'HARD CAPPED': ('hard_capped', '硬帽限制'),
}

STATUS_CN = {
    'Active List': '活跃名单',
    'Buyout': '买断',
    'Disabled List': '伤病名单',
    'Hold': '占位',
    'Inactive List': '非活跃名单',
    'Training Camp and Exhibit 10': '训练营与 Exhibit 10',
    'Minors/G-League': '发展联盟/小联盟',
    '120% RSC Hold': '120% 新秀合同占位',
    'RFA': '受限制自由球员',
    'UFA': '完全自由球员',
    'FA Cap Hold': '自由球员占位',
}

SECTION_TITLE_CN = {
    'Active': '现役',
    'Inactive': '非活跃名单',
    'Training Camp and Exhibit 10': '训练营与 Exhibit 10',
    'Minors/G-League': '发展联盟/小联盟',
    '1st Rd Picks': '首轮签',
    '2nd Rd Picks': '次轮签',
    'RFAs': '受限制自由球员',
    'UFAs': '完全自由球员',
    'FA Cap Hold': '自由球员占位',
    'Buyout': '买断',
    'Disabled': '伤病特例',
    'Waivers': '裁员',
}

ACQUIRED_CN = {
    'Draft': '选秀',
    'Signed': '签约',
    'Trade': '交易',
}

TERMS_CN = {
    'Max': '顶薪',
    'MLE': '中产特例',
    'RSC': '新秀规模合同',
    'Two-Way': '双向合同',
}

POSITION_CN = {
    'PG': '控卫',
    'SG': '分卫',
    'SF': '小前锋',
    'PF': '大前锋',
    'C': '中锋',
}

BIRD_RIGHTS_CN = {
    'Bird': '伯德权',
    'Early-Bird': '早鸟权',
    'Non-Bird': '非鸟权',
}

SIGNING_EXCEPTION_CN = {
    'Bi-Annual': '双年特例',
    'Mid-Level': '中产特例',
}

HOME_SNAPSHOT_COLUMNS = {
    'Team': 'team',
    'Roster Size': 'roster_size',
    'Two-Ways': 'two_ways',
    'Cap Hit': 'cap_hit',
    'Cap Room': 'cap_room',
    'Luxury Room': 'luxury_room',
    '1st Apron Rm': 'first_apron_room',
    '2nd Apron Rm': 'second_apron_room',
    'Hard Cap': 'hard_cap',
}


def salaryswish_utcnow_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat()


def normalize_whitespace(value):
    return re.sub(r'\s+', ' ', str(value or '').replace('\xa0', ' ')).strip()


def strip_tags(value):
    text = re.sub(r'<[^>]+>', '', str(value or ''))
    return normalize_whitespace(text)


def strip_accents(value):
    return ''.join(
        char
        for char in unicodedata.normalize('NFKD', str(value or ''))
        if not unicodedata.combining(char)
    )


def stable_id(*parts):
    raw = '|'.join(str(part or '') for part in parts)
    value = re.sub(r'[^A-Za-z0-9_-]+', '_', raw).strip('_')
    return value[:220] or 'salaryswish'


def to_int(value):
    if value in (None, ''):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def canonical_team_slug(slug):
    value = normalize_whitespace(slug).lower()
    return TEAM_SLUG_ALIASES.get(value, value)


def team_info(slug, fallback_name=''):
    canonical_slug = canonical_team_slug(slug)
    info = TEAM_INFO_BY_SLUG.get(canonical_slug)
    if info:
        return {
            'slug': canonical_slug,
            'name_en': info[0],
            'name_cn': info[1],
            'abbr': info[2],
        }
    return {
        'slug': canonical_slug,
        'name_en': fallback_name,
        'name_cn': TEAM_CN_BY_EN.get(fallback_name, fallback_name),
        'abbr': '',
    }


def split_count_limit(value):
    match = re.match(r'^\s*(\d+)\s*/\s*(\d+)\s*$', str(value or ''))
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def money_values(value):
    return re.findall(r'-?\$[0-9,]+', str(value or ''))


def unique_preserve_order(values):
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def normalize_name_key(value):
    text = strip_accents(value).lower()
    return re.sub(r'[^a-z0-9]+', '', text)


def salaryswish_player_name_to_english(value):
    text = normalize_whitespace(value)
    if not text or text.upper() == 'TOTAL':
        return ''
    text = re.sub(r'\s*\([^)]*\)\s*', ' ', text).strip()
    if ',' not in text:
        return normalize_whitespace(text)
    last, first = [normalize_whitespace(part) for part in text.split(',', 1)]
    return normalize_whitespace(first + ' ' + last)


def translate_positions(value):
    tokens = [token.strip() for token in str(value or '').split(',') if token.strip()]
    return ', '.join(POSITION_CN.get(token, token) for token in tokens)


def translate_value(value, mapping):
    return mapping.get(value, value)


def hard_cap_cn(value):
    if value == 'No':
        return '否'
    if value == 'Yes':
        return '是'
    return value


def draft_pick_status_cn(status):
    return {
        'owned': '持有',
        'in_contention': '互换/待定',
        'traded_away': '已交易走',
    }.get(status, status)


def extract_slug_from_url(url):
    match = re.search(r'/teams/([^/?#]+)', str(url or ''))
    return canonical_team_slug(match.group(1)) if match else ''


def source_url_for_slug(slug):
    return SALARYSWISH_BASE_URL + '/teams/' + canonical_team_slug(slug)


class SalarySwishHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = None
        self.current_row = None
        self.current_cell = None
        self.current_link = None
        self.current_pick = None
        self.pick_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table':
            self.current_table = {'attrs': attrs, 'rows': []}
            self.tables.append(self.current_table)
        elif tag == 'tr' and self.current_table is not None:
            self.current_row = {'attrs': attrs, 'cells': []}
            self.current_table['rows'].append(self.current_row)
        elif tag in ('th', 'td') and self.current_row is not None:
            self.current_cell = {
                'tag': tag,
                'attrs': attrs,
                'text_parts': [],
                'text': '',
                'links': [],
                'images': [],
                'class_tokens': [],
                'titles': [],
                'pick_blocks': [],
            }
            self.current_row['cells'].append(self.current_cell)
        elif tag == 'a' and self.current_cell is not None:
            self.current_link = {'href': attrs.get('href', ''), 'text_parts': [], 'text': ''}
        elif tag == 'img' and self.current_cell is not None:
            image = {
                'src': attrs.get('src', ''),
                'alt': attrs.get('alt', ''),
                'title': attrs.get('title', ''),
            }
            self.current_cell['images'].append(image)
            if getattr(self, 'current_pick', None) is not None:
                self.current_pick['images'].append(image)

        if self.current_cell is not None:
            self._capture_cell_metadata(tag, attrs)

    def handle_endtag(self, tag):
        if tag == 'a' and self.current_link is not None and self.current_cell is not None:
            self.current_link['text'] = normalize_whitespace(''.join(self.current_link['text_parts']))
            link = {
                'href': self.current_link['href'],
                'text': self.current_link['text'],
            }
            self.current_cell['links'].append(link)
            if getattr(self, 'current_pick', None) is not None:
                self.current_pick['links'].append(link)
            self.current_link = None
        elif tag in ('th', 'td') and self.current_cell is not None:
            self.current_cell['text'] = normalize_whitespace(''.join(self.current_cell['text_parts']))
            self.current_cell.pop('text_parts', None)
            self.current_cell = None
        elif tag == 'tr':
            self.current_row = None
        elif tag == 'table':
            self.current_table = None
        self._close_pick_block(tag)

    def handle_data(self, data):
        if self.current_cell is not None:
            self.current_cell['text_parts'].append(data)
        if self.current_link is not None:
            self.current_link['text_parts'].append(data)

    def _capture_cell_metadata(self, tag, attrs):
        class_tokens = (attrs.get('class') or '').split()
        title = normalize_whitespace(attrs.get('title') or '')
        if class_tokens:
            self.current_cell['class_tokens'].extend(class_tokens)
        if title:
            self.current_cell['titles'].append(title)

        starts_pick = tag == 'div' and ('q' in class_tokens or 'd_pick' in class_tokens)
        if getattr(self, 'current_pick', None) is None and starts_pick:
            self.current_pick = {
                'class_tokens': [],
                'titles': [],
                'links': [],
                'images': [],
            }
            self.pick_depth = 0
        if getattr(self, 'current_pick', None) is not None:
            if tag != 'img':
                self.pick_depth += 1
            if class_tokens:
                self.current_pick['class_tokens'].extend(class_tokens)
            if title:
                self.current_pick['titles'].append(title)

    def _close_pick_block(self, tag):
        if getattr(self, 'current_pick', None) is None or tag == 'img':
            return
        self.pick_depth -= 1
        if self.pick_depth <= 0:
            if self.current_cell is not None:
                self.current_cell['pick_blocks'].append(self.current_pick)
            self.current_pick = None
            self.pick_depth = 0


def parse_tables(html):
    parser = SalarySwishHTMLParser()
    parser.feed(html or '')
    return parser.tables


def table_by_id(tables, table_id):
    for table in tables:
        if table['attrs'].get('id') == table_id:
            return table
    return None


def tables_by_class(tables, class_name):
    return [
        table for table in tables
        if class_name in (table['attrs'].get('class') or '').split()
    ]


def fetch_salaryswish_html(url, timeout=SALARYSWISH_TIMEOUT):
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


def parse_salaryswish_home(html, fetched_at=None):
    fetched_at = fetched_at or salaryswish_utcnow_iso()
    tables = parse_tables(html)
    table = table_by_id(tables, 'sw_homepage__table')
    if not table or not table.get('rows'):
        return {'season': '', 'teams': []}

    season_match = re.search(r'([0-9]{4}-[0-9]{2})\s+SALARY CAP', html or '', re.I)
    season = season_match.group(1) if season_match else ''
    headers = [cell['text'] for cell in table['rows'][0]['cells']]
    teams = []
    for sort_order, row in enumerate(table['rows'][1:], start=1):
        cells = row.get('cells') or []
        if not cells:
            continue
        first_link = (cells[0].get('links') or [{}])[0]
        slug = extract_slug_from_url(first_link.get('href'))
        if not slug:
            continue
        info = team_info(slug)
        item = {
            'season': season,
            'team_slug': slug,
            'team_name_en': info['name_en'],
            'team_name_cn': info['name_cn'],
            'team_abbr': info['abbr'],
            'sort_order': sort_order,
            'fetched_at': fetched_at,
            'source_url': source_url_for_slug(slug),
            'raw_cells_json': json.dumps([cell['text'] for cell in cells], ensure_ascii=False),
        }
        for index, header in enumerate(headers):
            key = HOME_SNAPSHOT_COLUMNS.get(header)
            if not key or index >= len(cells):
                continue
            item[key] = cells[index]['text']
        roster_count, roster_limit = split_count_limit(item.get('roster_size'))
        two_way_count, two_way_limit = split_count_limit(item.get('two_ways'))
        item.update({
            'roster_count': roster_count,
            'roster_limit': roster_limit,
            'two_way_count': two_way_count,
            'two_way_limit': two_way_limit,
            'hard_cap_cn': hard_cap_cn(item.get('hard_cap') or ''),
        })
        teams.append(item)
    return {'season': season, 'teams': teams}


def parse_summary(html, slug, season, fetched_at):
    slug = canonical_team_slug(slug)
    info = team_info(slug)
    heading = re.search(r'<h1[^>]*>(.*?)</h1>', html or '', re.I | re.S)
    team_name_en = strip_tags(heading.group(1)) if heading else info['name_en']
    info = team_info(slug, team_name_en)
    summary = {
        'team_slug': slug,
        'team_name_en': info['name_en'] or team_name_en,
        'team_name_cn': info['name_cn'],
        'team_abbr': info['abbr'],
        'season': season,
        'source_url': source_url_for_slug(slug),
        'fetched_at': fetched_at,
    }
    for label, (key, label_cn) in SUMMARY_LABELS.items():
        pattern = r'<h5[^>]*>\s*{}.*?:\s*<span[^>]*>(.*?)</span>\s*</h5>'.format(re.escape(label))
        match = re.search(pattern, html or '', re.I | re.S)
        value = strip_tags(match.group(1)) if match else ''
        summary[key] = value
        summary[key + '_cn_label'] = label_cn
    summary['hard_capped_cn'] = hard_cap_cn(summary.get('hard_capped') or '')

    roster_match = re.search(r'ROSTER SIZE:\s*<span[^>]*>([^<]+)</span>', html or '', re.I | re.S)
    two_way_match = re.search(r'TWO-WAY CONTRACTS:\s*([^<]+)</div>', html or '', re.I | re.S)
    summary['roster_size'] = strip_tags(roster_match.group(1)) if roster_match else ''
    summary['two_way_contracts'] = strip_tags(two_way_match.group(1)) if two_way_match else ''
    summary['roster_count'], summary['roster_limit'] = split_count_limit(summary['roster_size'])
    summary['two_way_count'], summary['two_way_limit'] = split_count_limit(summary['two_way_contracts'])

    executive = re.search(r'HEAD EXECUTIVE:\s*<a[^>]*>(.*?)</a>', html or '', re.I | re.S)
    coach = re.search(r'HEAD COACH:\s*<a[^>]*>(.*?)</a>', html or '', re.I | re.S)
    summary['head_executive'] = strip_tags(executive.group(1)) if executive else ''
    summary['head_coach'] = strip_tags(coach.group(1)) if coach else ''
    return summary


def parse_signing_exceptions(html, slug, season, fetched_at):
    results = []
    pattern = (
        r'<span class="progress_list_text">\s*<a[^>]*>\s*<strong>(.*?)</strong>\s*</a>'
        r'\s*(.*?)\s*</span>\s*<span[^>]*style="width:([^"]*)"'
    )
    for sort_order, match in enumerate(re.finditer(pattern, html or '', re.I | re.S), start=1):
        name_en = strip_tags(match.group(1)).rstrip(':')
        text = strip_tags(match.group(2))
        amounts = money_values(text)
        remaining = amounts[0] if amounts else ''
        total = amounts[1] if len(amounts) > 1 else ''
        results.append({
            'exception_id': stable_id(slug, season, name_en),
            'team_slug': slug,
            'season': season,
            'name_en': name_en,
            'name_cn': SIGNING_EXCEPTION_CN.get(name_en, name_en),
            'remaining': remaining,
            'total': total,
            'display_text': '{}: {}'.format(name_en, text).strip(),
            'display_text_cn': '{}：{}'.format(SIGNING_EXCEPTION_CN.get(name_en, name_en), text).strip(),
            'used_percent': match.group(3).strip(),
            'sort_order': sort_order,
            'fetched_at': fetched_at,
        })
    return results


def contract_section_key(title):
    base = re.sub(r'\([^)]*\)', '', title or '').strip()
    return re.sub(r'[^a-z0-9]+', '_', base.lower()).strip('_') or 'section'


def parse_section_title(title):
    match = re.match(r'^(.*?)\s*\((\d+)\s*-\s*([^)]+)\)', title or '')
    if not match:
        return title, None, ''
    return normalize_whitespace(match.group(1)), to_int(match.group(2)), normalize_whitespace(match.group(3))


def parse_contract_cell(cell):
    text = cell.get('text') or ''
    amounts = unique_preserve_order(money_values(text))
    option_match = re.match(r'^\s*([PT])\s*-?\$', text)
    free_agent = ''
    if 'UFA' in text:
        free_agent = 'UFA'
    elif 'RFA' in text:
        free_agent = 'RFA'
    rights = ''
    unconfirmed = False
    for image in cell.get('images') or []:
        alt = image.get('alt') or ''
        if alt in BIRD_RIGHTS_CN:
            rights = alt
        if alt == 'Unconfirmed Information':
            unconfirmed = True
    return {
        'raw': text,
        'value': amounts[0] if amounts else '',
        'amounts': amounts,
        'option': option_match.group(1) if option_match else '',
        'freeAgentStatus': free_agent,
        'freeAgentStatusCn': STATUS_CN.get(free_agent, free_agent),
        'birdRights': rights,
        'birdRightsCn': BIRD_RIGHTS_CN.get(rights, rights),
        'unconfirmed': unconfirmed,
    }


def player_link(cells):
    if not cells:
        return {}
    for link in cells[0].get('links') or []:
        if '/players/' in link.get('href', ''):
            return link
    return {}


def parse_roster_tables(tables, slug, season, fetched_at):
    rows = []
    roster_tables = tables_by_class(tables, 'sw_teamProfileRosterSection__table')
    for table_index, table in enumerate(roster_tables):
        table_rows = table.get('rows') or []
        if not table_rows:
            continue
        header_cells = table_rows[0].get('cells') or []
        if len(header_cells) < 7:
            continue
        headers = [cell['text'] for cell in header_cells]
        section_title = headers[0]
        section_title_en, section_count, section_amount = parse_section_title(section_title)
        section_key = contract_section_key(section_title_en)
        season_headers = headers[6:]
        for row_index, row in enumerate(table_rows[1:], start=1):
            cells = row.get('cells') or []
            if len(cells) < 6:
                continue
            raw_player_name = cells[0]['text']
            row_type = 'total' if raw_player_name.upper() == 'TOTAL' else 'player'
            link = player_link(cells)
            player_slug = os.path.basename(link.get('href', '')).strip('/') if link else ''
            english_name = salaryswish_player_name_to_english(raw_player_name)
            age = to_int(cells[3]['text'])
            terms_en = cells[5]['text']
            season_cells = []
            for header, cell in zip(season_headers, cells[6:]):
                parsed = parse_contract_cell(cell)
                parsed['season'] = header
                season_cells.append(parsed)
            free_agent = next((item['freeAgentStatus'] for item in season_cells if item['freeAgentStatus']), '')
            bird_rights = next((item['birdRights'] for item in season_cells if item['birdRights']), '')
            row_id = stable_id(slug, season, section_key, row_type, player_slug or english_name or row_index, row_index)
            rows.append({
                'row_id': row_id,
                'team_slug': slug,
                'season': season,
                'section_key': section_key,
                'section_title_en': section_title_en,
                'section_title_cn': translate_value(section_title_en, SECTION_TITLE_CN),
                'section_count': section_count,
                'section_amount': section_amount,
                'row_type': row_type,
                'player_slug': player_slug,
                'salaryswish_player_url': urllib.parse.urljoin(SALARYSWISH_BASE_URL, link.get('href', '')) if link else '',
                'player_name_raw': raw_player_name,
                'player_name_en': english_name,
                'player_name_cn': '',
                'player_pid': '',
                'status_en': cells[1]['text'],
                'status_cn': translate_value(cells[1]['text'], STATUS_CN),
                'acquired_en': cells[2]['text'],
                'acquired_cn': translate_value(cells[2]['text'], ACQUIRED_CN),
                'age': age,
                'positions_en': cells[4]['text'],
                'positions_cn': translate_positions(cells[4]['text']),
                'terms_en': terms_en,
                'terms_cn': translate_value(terms_en, TERMS_CN),
                'free_agent_status': free_agent,
                'free_agent_status_cn': translate_value(free_agent, STATUS_CN),
                'bird_rights_en': bird_rights,
                'bird_rights_cn': translate_value(bird_rights, BIRD_RIGHTS_CN),
                'is_unconfirmed': 1 if any(item['unconfirmed'] for item in season_cells) else 0,
                'season_salaries_json': json.dumps(season_cells, ensure_ascii=False),
                'raw_cells_json': json.dumps([cell['text'] for cell in cells], ensure_ascii=False),
                'sort_order': table_index * 1000 + row_index,
                'fetched_at': fetched_at,
                'source_url': source_url_for_slug(slug),
            })
    return rows


def parse_trade_exceptions(tables, slug, season, fetched_at):
    table = table_by_id(tables, 'sw_table__tradeExptn_tm')
    if not table:
        return []
    rows = []
    for sort_order, row in enumerate((table.get('rows') or [])[1:], start=1):
        cells = row.get('cells') or []
        if len(cells) < 6:
            continue
        link = player_link(cells)
        name_en = salaryswish_player_name_to_english(cells[0]['text'])
        trade_url = ''
        if len(cells[1].get('links') or []) > 0:
            trade_url = urllib.parse.urljoin(SALARYSWISH_BASE_URL, cells[1]['links'][0]['href'])
        rows.append({
            'exception_id': stable_id(slug, season, name_en, cells[4]['text'], cells[5]['text']),
            'team_slug': slug,
            'season': season,
            'player_name_en': name_en,
            'player_name_cn': '',
            'player_pid': '',
            'player_slug': os.path.basename(link.get('href', '')).strip('/') if link else '',
            'salaryswish_player_url': urllib.parse.urljoin(SALARYSWISH_BASE_URL, link.get('href', '')) if link else '',
            'exception_amount': cells[1]['text'],
            'used': cells[2]['text'],
            'remaining': cells[3]['text'],
            'start_date': cells[4]['text'],
            'end_date': cells[5]['text'],
            'trade_url': trade_url,
            'sort_order': sort_order,
            'fetched_at': fetched_at,
        })
    return rows


def team_name_from_logo_alt(alt):
    match = re.match(r'Logo of the (.*)', alt or '')
    return match.group(1) if match else ''


def draft_pick_status(pick_block):
    titles = ' '.join(pick_block.get('titles') or []).lower()
    classes = set(pick_block.get('class_tokens') or [])
    if 'd_pick_traded' in classes or 'pick traded away' in titles:
        return 'traded_away'
    if 'sw_teamProfile__draftPick_inContention' in classes or 'in contention' in titles:
        return 'in_contention'
    return 'owned'


def draft_asset_from_pick_block(pick_block, image_index=0):
    images = pick_block.get('images') or []
    if image_index >= len(images):
        return None
    image = images[image_index]
    links = pick_block.get('links') or []
    team_en = team_name_from_logo_alt(image.get('alt'))
    status = draft_pick_status(pick_block)
    note = '; '.join(unique_preserve_order(pick_block.get('titles') or []))
    return {
        'teamNameEn': team_en,
        'teamNameCn': TEAM_CN_BY_EN.get(team_en, team_en),
        'logo': image.get('src') or '',
        'draftUrl': urllib.parse.urljoin(SALARYSWISH_BASE_URL, links[image_index]['href'])
        if image_index < len(links) else '',
        'ownershipStatus': status,
        'ownershipStatusCn': draft_pick_status_cn(status),
        'isOwned': status == 'owned',
        'isInContention': status == 'in_contention',
        'isTradedAway': status == 'traded_away',
        'note': note,
    }


def parse_draft_assets(tables, slug, season, fetched_at):
    table = table_by_id(tables, 'sw_teamProfile__draftTable')
    if not table or not table.get('rows'):
        return []
    headers = [cell['text'] for cell in table['rows'][0]['cells']]
    rows = []
    for row in (table.get('rows') or [])[1:]:
        cells = row.get('cells') or []
        if len(cells) < 2:
            continue
        round_label = cells[0]['text']
        round_number = to_int(round_label.replace('Round', '').strip())
        for index, cell in enumerate(cells[1:], start=1):
            draft_year = headers[index] if index < len(headers) else ''
            assets = []
            pick_blocks = cell.get('pick_blocks') or []
            for pick_block in pick_blocks:
                for image_index, _image in enumerate(pick_block.get('images') or []):
                    asset = draft_asset_from_pick_block(pick_block, image_index)
                    if asset:
                        assets.append(asset)
            if not pick_blocks:
                links = cell.get('links') or []
                images = cell.get('images') or []
                for image_index, image in enumerate(images):
                    team_en = team_name_from_logo_alt(image.get('alt'))
                    assets.append({
                        'teamNameEn': team_en,
                        'teamNameCn': TEAM_CN_BY_EN.get(team_en, team_en),
                        'logo': image.get('src') or '',
                        'draftUrl': urllib.parse.urljoin(SALARYSWISH_BASE_URL, links[image_index]['href'])
                        if image_index < len(links) else '',
                        'ownershipStatus': 'owned',
                        'ownershipStatusCn': draft_pick_status_cn('owned'),
                        'isOwned': True,
                        'isInContention': False,
                        'isTradedAway': False,
                        'note': '',
                    })
            rows.append({
                'asset_id': stable_id(slug, season, round_label, draft_year),
                'team_slug': slug,
                'season': season,
                'draft_year': draft_year,
                'round_label_en': round_label,
                'round_label_cn': '第{}轮'.format(round_number) if round_number else round_label,
                'round_number': round_number,
                'assets_json': json.dumps(assets, ensure_ascii=False),
                'sort_order': (round_number or 0) * 100 + index,
                'fetched_at': fetched_at,
            })
    return rows


def parse_salaryswish_team_page(html, slug, season='', fetched_at=None):
    fetched_at = fetched_at or salaryswish_utcnow_iso()
    tables = parse_tables(html)
    roster_tables = tables_by_class(tables, 'sw_teamProfileRosterSection__table')
    if roster_tables and roster_tables[0].get('rows'):
        headers = [cell['text'] for cell in roster_tables[0]['rows'][0]['cells']]
        year_headers = [header for header in headers if re.match(r'^\d{4}-\d{2}$', header)]
        if year_headers and not season:
            season = year_headers[0]
    summary = parse_summary(html, slug, season, fetched_at)
    return {
        'summary': summary,
        'signing_exceptions': parse_signing_exceptions(html, slug, season, fetched_at),
        'trade_exceptions': parse_trade_exceptions(tables, slug, season, fetched_at),
        'draft_assets': parse_draft_assets(tables, slug, season, fetched_at),
        'contract_rows': parse_roster_tables(tables, slug, season, fetched_at),
    }


def salaryswish_player_lookup(conn):
    rows = conn.execute(
        '''
        SELECT pid, chinese_name, english_name
        FROM nba_players
        WHERE english_name!=''
        '''
    ).fetchall()
    lookup = {}
    for row in rows:
        key = normalize_name_key(row['english_name'])
        if key:
            lookup[key] = {
                'pid': row['pid'],
                'chinese_name': row['chinese_name'] or '',
                'english_name': row['english_name'] or '',
            }
    return lookup


def attach_player_matches(parsed, lookup):
    for collection_name in ('contract_rows', 'trade_exceptions'):
        for item in parsed.get(collection_name) or []:
            name = item.get('player_name_en') or ''
            match = lookup.get(normalize_name_key(name))
            if match:
                item['player_pid'] = match['pid']
                item['player_name_cn'] = match['chinese_name'] or name
            elif name:
                item['player_name_cn'] = name
    return parsed


def ensure_salaryswish_schema(conn):
    conn.executescript(
        '''
        CREATE TABLE IF NOT EXISTS nba_salaryswish_team_caps (
            team_slug TEXT PRIMARY KEY,
            season TEXT NOT NULL DEFAULT '',
            team_name_en TEXT NOT NULL DEFAULT '',
            team_name_cn TEXT NOT NULL DEFAULT '',
            team_abbr TEXT NOT NULL DEFAULT '',
            roster_size TEXT NOT NULL DEFAULT '',
            roster_count INTEGER,
            roster_limit INTEGER,
            two_ways TEXT NOT NULL DEFAULT '',
            two_way_count INTEGER,
            two_way_limit INTEGER,
            cap_hit TEXT NOT NULL DEFAULT '',
            cap_room TEXT NOT NULL DEFAULT '',
            luxury_room TEXT NOT NULL DEFAULT '',
            first_apron_room TEXT NOT NULL DEFAULT '',
            second_apron_room TEXT NOT NULL DEFAULT '',
            hard_cap TEXT NOT NULL DEFAULT '',
            hard_cap_cn TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            source_url TEXT NOT NULL DEFAULT '',
            raw_cells_json TEXT NOT NULL DEFAULT '[]',
            fetched_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS nba_salaryswish_team_summaries (
            team_slug TEXT PRIMARY KEY,
            season TEXT NOT NULL DEFAULT '',
            team_name_en TEXT NOT NULL DEFAULT '',
            team_name_cn TEXT NOT NULL DEFAULT '',
            team_abbr TEXT NOT NULL DEFAULT '',
            cap_hit TEXT NOT NULL DEFAULT '',
            cap_room TEXT NOT NULL DEFAULT '',
            team_salary TEXT NOT NULL DEFAULT '',
            team_salary_room TEXT NOT NULL DEFAULT '',
            luxury_tax_room TEXT NOT NULL DEFAULT '',
            first_apron_room TEXT NOT NULL DEFAULT '',
            second_apron_room TEXT NOT NULL DEFAULT '',
            hard_capped TEXT NOT NULL DEFAULT '',
            hard_capped_cn TEXT NOT NULL DEFAULT '',
            roster_size TEXT NOT NULL DEFAULT '',
            roster_count INTEGER,
            roster_limit INTEGER,
            two_way_contracts TEXT NOT NULL DEFAULT '',
            two_way_count INTEGER,
            two_way_limit INTEGER,
            head_executive TEXT NOT NULL DEFAULT '',
            head_coach TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            fetched_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS nba_salaryswish_signing_exceptions (
            exception_id TEXT PRIMARY KEY,
            team_slug TEXT NOT NULL,
            season TEXT NOT NULL DEFAULT '',
            name_en TEXT NOT NULL DEFAULT '',
            name_cn TEXT NOT NULL DEFAULT '',
            remaining TEXT NOT NULL DEFAULT '',
            total TEXT NOT NULL DEFAULT '',
            display_text TEXT NOT NULL DEFAULT '',
            display_text_cn TEXT NOT NULL DEFAULT '',
            used_percent TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            fetched_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS nba_salaryswish_trade_exceptions (
            exception_id TEXT PRIMARY KEY,
            team_slug TEXT NOT NULL,
            season TEXT NOT NULL DEFAULT '',
            player_name_en TEXT NOT NULL DEFAULT '',
            player_name_cn TEXT NOT NULL DEFAULT '',
            player_pid TEXT NOT NULL DEFAULT '',
            player_slug TEXT NOT NULL DEFAULT '',
            salaryswish_player_url TEXT NOT NULL DEFAULT '',
            exception_amount TEXT NOT NULL DEFAULT '',
            used TEXT NOT NULL DEFAULT '',
            remaining TEXT NOT NULL DEFAULT '',
            start_date TEXT NOT NULL DEFAULT '',
            end_date TEXT NOT NULL DEFAULT '',
            trade_url TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            fetched_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS nba_salaryswish_draft_assets (
            asset_id TEXT PRIMARY KEY,
            team_slug TEXT NOT NULL,
            season TEXT NOT NULL DEFAULT '',
            draft_year TEXT NOT NULL DEFAULT '',
            round_label_en TEXT NOT NULL DEFAULT '',
            round_label_cn TEXT NOT NULL DEFAULT '',
            round_number INTEGER,
            assets_json TEXT NOT NULL DEFAULT '[]',
            sort_order INTEGER NOT NULL DEFAULT 0,
            fetched_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS nba_salaryswish_contract_rows (
            row_id TEXT PRIMARY KEY,
            team_slug TEXT NOT NULL,
            season TEXT NOT NULL DEFAULT '',
            section_key TEXT NOT NULL DEFAULT '',
            section_title_en TEXT NOT NULL DEFAULT '',
            section_title_cn TEXT NOT NULL DEFAULT '',
            section_count INTEGER,
            section_amount TEXT NOT NULL DEFAULT '',
            row_type TEXT NOT NULL DEFAULT '',
            player_slug TEXT NOT NULL DEFAULT '',
            salaryswish_player_url TEXT NOT NULL DEFAULT '',
            player_name_raw TEXT NOT NULL DEFAULT '',
            player_name_en TEXT NOT NULL DEFAULT '',
            player_name_cn TEXT NOT NULL DEFAULT '',
            player_pid TEXT NOT NULL DEFAULT '',
            status_en TEXT NOT NULL DEFAULT '',
            status_cn TEXT NOT NULL DEFAULT '',
            acquired_en TEXT NOT NULL DEFAULT '',
            acquired_cn TEXT NOT NULL DEFAULT '',
            age INTEGER,
            positions_en TEXT NOT NULL DEFAULT '',
            positions_cn TEXT NOT NULL DEFAULT '',
            terms_en TEXT NOT NULL DEFAULT '',
            terms_cn TEXT NOT NULL DEFAULT '',
            free_agent_status TEXT NOT NULL DEFAULT '',
            free_agent_status_cn TEXT NOT NULL DEFAULT '',
            bird_rights_en TEXT NOT NULL DEFAULT '',
            bird_rights_cn TEXT NOT NULL DEFAULT '',
            is_unconfirmed INTEGER NOT NULL DEFAULT 0,
            season_salaries_json TEXT NOT NULL DEFAULT '[]',
            raw_cells_json TEXT NOT NULL DEFAULT '[]',
            sort_order INTEGER NOT NULL DEFAULT 0,
            source_url TEXT NOT NULL DEFAULT '',
            fetched_at TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_salaryswish_contract_team
        ON nba_salaryswish_contract_rows(team_slug, season, sort_order);

        CREATE INDEX IF NOT EXISTS idx_salaryswish_contract_player
        ON nba_salaryswish_contract_rows(player_pid);
        '''
    )


def upsert_home_caps(conn, home):
    now = salaryswish_utcnow_iso()
    for item in home.get('teams') or []:
        existing = conn.execute(
            'SELECT created_at FROM nba_salaryswish_team_caps WHERE team_slug=?',
            (item['team_slug'],),
        ).fetchone()
        values = dict(item)
        values['created_at'] = existing['created_at'] if existing else now
        values['updated_at'] = now
        conn.execute(
            '''
            INSERT INTO nba_salaryswish_team_caps (
                team_slug, season, team_name_en, team_name_cn, team_abbr,
                roster_size, roster_count, roster_limit, two_ways, two_way_count, two_way_limit,
                cap_hit, cap_room, luxury_room, first_apron_room, second_apron_room,
                hard_cap, hard_cap_cn, sort_order, source_url, raw_cells_json,
                fetched_at, created_at, updated_at
            ) VALUES (
                :team_slug, :season, :team_name_en, :team_name_cn, :team_abbr,
                :roster_size, :roster_count, :roster_limit, :two_ways, :two_way_count, :two_way_limit,
                :cap_hit, :cap_room, :luxury_room, :first_apron_room, :second_apron_room,
                :hard_cap, :hard_cap_cn, :sort_order, :source_url, :raw_cells_json,
                :fetched_at, :created_at, :updated_at
            )
            ON CONFLICT(team_slug) DO UPDATE SET
                season=excluded.season,
                team_name_en=excluded.team_name_en,
                team_name_cn=excluded.team_name_cn,
                team_abbr=excluded.team_abbr,
                roster_size=excluded.roster_size,
                roster_count=excluded.roster_count,
                roster_limit=excluded.roster_limit,
                two_ways=excluded.two_ways,
                two_way_count=excluded.two_way_count,
                two_way_limit=excluded.two_way_limit,
                cap_hit=excluded.cap_hit,
                cap_room=excluded.cap_room,
                luxury_room=excluded.luxury_room,
                first_apron_room=excluded.first_apron_room,
                second_apron_room=excluded.second_apron_room,
                hard_cap=excluded.hard_cap,
                hard_cap_cn=excluded.hard_cap_cn,
                sort_order=excluded.sort_order,
                source_url=excluded.source_url,
                raw_cells_json=excluded.raw_cells_json,
                fetched_at=excluded.fetched_at,
                updated_at=excluded.updated_at
            ''',
            values,
        )


def replace_team_detail(conn, parsed):
    now = salaryswish_utcnow_iso()
    summary = dict(parsed['summary'])
    slug = summary['team_slug']
    season = summary.get('season') or ''
    existing = conn.execute(
        'SELECT created_at FROM nba_salaryswish_team_summaries WHERE team_slug=?',
        (slug,),
    ).fetchone()
    summary['created_at'] = existing['created_at'] if existing else now
    summary['updated_at'] = now
    conn.execute(
        '''
        INSERT INTO nba_salaryswish_team_summaries (
            team_slug, season, team_name_en, team_name_cn, team_abbr,
            cap_hit, cap_room, team_salary, team_salary_room, luxury_tax_room,
            first_apron_room, second_apron_room, hard_capped, hard_capped_cn,
            roster_size, roster_count, roster_limit, two_way_contracts, two_way_count,
            two_way_limit, head_executive, head_coach, source_url, fetched_at,
            created_at, updated_at
        ) VALUES (
            :team_slug, :season, :team_name_en, :team_name_cn, :team_abbr,
            :cap_hit, :cap_room, :team_salary, :team_salary_room, :luxury_tax_room,
            :first_apron_room, :second_apron_room, :hard_capped, :hard_capped_cn,
            :roster_size, :roster_count, :roster_limit, :two_way_contracts, :two_way_count,
            :two_way_limit, :head_executive, :head_coach, :source_url, :fetched_at,
            :created_at, :updated_at
        )
        ON CONFLICT(team_slug) DO UPDATE SET
            season=excluded.season,
            team_name_en=excluded.team_name_en,
            team_name_cn=excluded.team_name_cn,
            team_abbr=excluded.team_abbr,
            cap_hit=excluded.cap_hit,
            cap_room=excluded.cap_room,
            team_salary=excluded.team_salary,
            team_salary_room=excluded.team_salary_room,
            luxury_tax_room=excluded.luxury_tax_room,
            first_apron_room=excluded.first_apron_room,
            second_apron_room=excluded.second_apron_room,
            hard_capped=excluded.hard_capped,
            hard_capped_cn=excluded.hard_capped_cn,
            roster_size=excluded.roster_size,
            roster_count=excluded.roster_count,
            roster_limit=excluded.roster_limit,
            two_way_contracts=excluded.two_way_contracts,
            two_way_count=excluded.two_way_count,
            two_way_limit=excluded.two_way_limit,
            head_executive=excluded.head_executive,
            head_coach=excluded.head_coach,
            source_url=excluded.source_url,
            fetched_at=excluded.fetched_at,
            updated_at=excluded.updated_at
        ''',
        summary,
    )

    for table in (
        'nba_salaryswish_signing_exceptions',
        'nba_salaryswish_trade_exceptions',
        'nba_salaryswish_draft_assets',
        'nba_salaryswish_contract_rows',
    ):
        conn.execute('DELETE FROM {} WHERE team_slug=?'.format(table), (slug,))

    for item in parsed.get('signing_exceptions') or []:
        conn.execute(
            '''
            INSERT INTO nba_salaryswish_signing_exceptions (
                exception_id, team_slug, season, name_en, name_cn, remaining, total,
                display_text, display_text_cn, used_percent, sort_order, fetched_at
            ) VALUES (
                :exception_id, :team_slug, :season, :name_en, :name_cn, :remaining, :total,
                :display_text, :display_text_cn, :used_percent, :sort_order, :fetched_at
            )
            ''',
            item,
        )
    for item in parsed.get('trade_exceptions') or []:
        conn.execute(
            '''
            INSERT INTO nba_salaryswish_trade_exceptions (
                exception_id, team_slug, season, player_name_en, player_name_cn, player_pid,
                player_slug, salaryswish_player_url, exception_amount, used, remaining,
                start_date, end_date, trade_url, sort_order, fetched_at
            ) VALUES (
                :exception_id, :team_slug, :season, :player_name_en, :player_name_cn, :player_pid,
                :player_slug, :salaryswish_player_url, :exception_amount, :used, :remaining,
                :start_date, :end_date, :trade_url, :sort_order, :fetched_at
            )
            ''',
            item,
        )
    for item in parsed.get('draft_assets') or []:
        conn.execute(
            '''
            INSERT INTO nba_salaryswish_draft_assets (
                asset_id, team_slug, season, draft_year, round_label_en, round_label_cn,
                round_number, assets_json, sort_order, fetched_at
            ) VALUES (
                :asset_id, :team_slug, :season, :draft_year, :round_label_en, :round_label_cn,
                :round_number, :assets_json, :sort_order, :fetched_at
            )
            ''',
            item,
        )
    for item in parsed.get('contract_rows') or []:
        conn.execute(
            '''
            INSERT INTO nba_salaryswish_contract_rows (
                row_id, team_slug, season, section_key, section_title_en, section_title_cn,
                section_count, section_amount, row_type, player_slug, salaryswish_player_url,
                player_name_raw, player_name_en, player_name_cn, player_pid, status_en,
                status_cn, acquired_en, acquired_cn, age, positions_en, positions_cn,
                terms_en, terms_cn, free_agent_status, free_agent_status_cn,
                bird_rights_en, bird_rights_cn, is_unconfirmed, season_salaries_json,
                raw_cells_json, sort_order, source_url, fetched_at
            ) VALUES (
                :row_id, :team_slug, :season, :section_key, :section_title_en, :section_title_cn,
                :section_count, :section_amount, :row_type, :player_slug, :salaryswish_player_url,
                :player_name_raw, :player_name_en, :player_name_cn, :player_pid, :status_en,
                :status_cn, :acquired_en, :acquired_cn, :age, :positions_en, :positions_cn,
                :terms_en, :terms_cn, :free_agent_status, :free_agent_status_cn,
                :bird_rights_en, :bird_rights_cn, :is_unconfirmed, :season_salaries_json,
                :raw_cells_json, :sort_order, :source_url, :fetched_at
            )
            ''',
            item,
        )
    return {'team_slug': slug, 'season': season}


def collect_salaryswish_team(slug, season=''):
    slug = canonical_team_slug(slug)
    html = fetch_salaryswish_html(source_url_for_slug(slug))
    return parse_salaryswish_team_page(html, slug, season=season)


def sync_salaryswish(conn, team_slugs=None, concurrency=SALARYSWISH_DEFAULT_CONCURRENCY):
    ensure_salaryswish_schema(conn)
    fetched_at = salaryswish_utcnow_iso()
    home_html = fetch_salaryswish_html(SALARYSWISH_HOME_URL)
    home = parse_salaryswish_home(home_html, fetched_at=fetched_at)
    upsert_home_caps(conn, home)
    all_slugs = [item['team_slug'] for item in home.get('teams') or []] or sorted(TEAM_INFO_BY_SLUG)
    requested = [
        canonical_team_slug(slug.strip())
        for slug in (team_slugs or all_slugs)
        if slug and slug.strip()
    ]
    if not requested:
        requested = all_slugs
    requested = list(dict.fromkeys(requested))
    season = home.get('season') or ''
    concurrency = max(1, min(to_int(concurrency) or SALARYSWISH_DEFAULT_CONCURRENCY, SALARYSWISH_MAX_CONCURRENCY))
    lookup = salaryswish_player_lookup(conn)
    errors = []
    collected = []
    started = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_slug = {
            executor.submit(collect_salaryswish_team, slug, season): slug
            for slug in requested
        }
        for future in concurrent.futures.as_completed(future_to_slug):
            slug = future_to_slug[future]
            try:
                parsed = attach_player_matches(future.result(), lookup)
                collected.append(parsed)
            except Exception as exc:
                errors.append({'teamSlug': slug, 'error': str(exc)})
    for parsed in collected:
        replace_team_detail(conn, parsed)
    conn.commit()
    return {
        'season': season,
        'requested_count': len(requested),
        'succeeded_count': len(collected),
        'failed_count': len(errors),
        'errors': errors,
        'home_team_count': len(home.get('teams') or []),
        'elapsed_seconds': round(time.time() - started, 3),
        'fetched_at': fetched_at,
    }


def load_json_list(raw):
    try:
        value = json.loads(raw or '[]')
    except (TypeError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


def row_to_salaryswish_team(row):
    return {
        'teamSlug': row['team_slug'],
        'season': row['season'] or '',
        'teamNameEn': row['team_name_en'] or '',
        'teamNameCn': row['team_name_cn'] or '',
        'teamAbbr': row['team_abbr'] or '',
        'capHit': row['cap_hit'] or '',
        'capRoom': row['cap_room'] or '',
        'luxuryRoom': row['luxury_room'] or '',
        'firstApronRoom': row['first_apron_room'] or '',
        'secondApronRoom': row['second_apron_room'] or '',
        'hardCap': row['hard_cap'] or '',
        'hardCapCn': row['hard_cap_cn'] or '',
        'rosterSize': {
            'display': row['roster_size'] or '',
            'count': row['roster_count'],
            'limit': row['roster_limit'],
        },
        'twoWays': {
            'display': row['two_ways'] or '',
            'count': row['two_way_count'],
            'limit': row['two_way_limit'],
        },
        'sourceUrl': row['source_url'] or '',
        'fetchedAt': row['fetched_at'] or '',
        'updatedAt': row['updated_at'] or '',
    }


def list_salaryswish_teams(conn):
    rows = conn.execute(
        '''
        SELECT *
        FROM nba_salaryswish_team_caps
        ORDER BY sort_order ASC, team_name_en ASC
        '''
    ).fetchall()
    return [row_to_salaryswish_team(row) for row in rows]


def row_to_summary(row):
    if not row:
        return None
    return {
        'teamSlug': row['team_slug'],
        'season': row['season'] or '',
        'teamNameEn': row['team_name_en'] or '',
        'teamNameCn': row['team_name_cn'] or '',
        'teamAbbr': row['team_abbr'] or '',
        'capHit': row['cap_hit'] or '',
        'capRoom': row['cap_room'] or '',
        'teamSalary': row['team_salary'] or '',
        'teamSalaryRoom': row['team_salary_room'] or '',
        'luxuryTaxRoom': row['luxury_tax_room'] or '',
        'firstApronRoom': row['first_apron_room'] or '',
        'secondApronRoom': row['second_apron_room'] or '',
        'hardCapped': row['hard_capped'] or '',
        'hardCappedCn': row['hard_capped_cn'] or '',
        'rosterSize': {
            'display': row['roster_size'] or '',
            'count': row['roster_count'],
            'limit': row['roster_limit'],
        },
        'twoWayContracts': {
            'display': row['two_way_contracts'] or '',
            'count': row['two_way_count'],
            'limit': row['two_way_limit'],
        },
        'headExecutive': row['head_executive'] or '',
        'headCoach': row['head_coach'] or '',
        'sourceUrl': row['source_url'] or '',
        'fetchedAt': row['fetched_at'] or '',
        'updatedAt': row['updated_at'] or '',
    }


def row_to_contract(row):
    return {
        'rowId': row['row_id'],
        'rowType': row['row_type'] or '',
        'playerSlug': row['player_slug'] or '',
        'salaryswishPlayerUrl': row['salaryswish_player_url'] or '',
        'playerNameRaw': row['player_name_raw'] or '',
        'playerNameEn': row['player_name_en'] or '',
        'playerNameCn': row['player_name_cn'] or '',
        'playerPid': row['player_pid'] or '',
        'statusEn': row['status_en'] or '',
        'statusCn': row['status_cn'] or '',
        'acquiredEn': row['acquired_en'] or '',
        'acquiredCn': row['acquired_cn'] or '',
        'age': row['age'],
        'positionsEn': row['positions_en'] or '',
        'positionsCn': row['positions_cn'] or '',
        'termsEn': row['terms_en'] or '',
        'termsCn': row['terms_cn'] or '',
        'freeAgentStatus': row['free_agent_status'] or '',
        'freeAgentStatusCn': row['free_agent_status_cn'] or '',
        'birdRightsEn': row['bird_rights_en'] or '',
        'birdRightsCn': row['bird_rights_cn'] or '',
        'isUnconfirmed': bool(row['is_unconfirmed']),
        'seasonSalaries': load_json_list(row['season_salaries_json']),
        'sortOrder': row['sort_order'],
    }


def grouped_contract_sections(rows):
    sections = []
    by_key = {}
    for row in rows:
        key = row['section_key']
        section = by_key.get(key)
        if not section:
            section = {
                'sectionKey': key,
                'titleEn': row['section_title_en'] or '',
                'titleCn': row['section_title_cn'] or '',
                'count': row['section_count'],
                'amount': row['section_amount'] or '',
                'items': [],
            }
            by_key[key] = section
            sections.append(section)
        section['items'].append(row_to_contract(row))
    return sections


def row_to_trade_exception(row):
    return {
        'playerNameEn': row['player_name_en'] or '',
        'playerNameCn': row['player_name_cn'] or '',
        'playerPid': row['player_pid'] or '',
        'playerSlug': row['player_slug'] or '',
        'salaryswishPlayerUrl': row['salaryswish_player_url'] or '',
        'exception': row['exception_amount'] or '',
        'used': row['used'] or '',
        'remaining': row['remaining'] or '',
        'startDate': row['start_date'] or '',
        'endDate': row['end_date'] or '',
        'tradeUrl': row['trade_url'] or '',
    }


def row_to_signing_exception(row):
    return {
        'nameEn': row['name_en'] or '',
        'nameCn': row['name_cn'] or '',
        'remaining': row['remaining'] or '',
        'total': row['total'] or '',
        'displayText': row['display_text'] or '',
        'displayTextCn': row['display_text_cn'] or '',
        'usedPercent': row['used_percent'] or '',
    }


def row_to_draft_asset(row):
    assets = load_json_list(row['assets_json'])
    return {
        'draftYear': row['draft_year'] or '',
        'roundLabelEn': row['round_label_en'] or '',
        'roundLabelCn': row['round_label_cn'] or '',
        'roundNumber': row['round_number'],
        'assets': assets,
        'ownedAssets': [asset for asset in assets if asset.get('isOwned')],
        'contentionAssets': [asset for asset in assets if asset.get('isInContention')],
        'tradedAwayAssets': [asset for asset in assets if asset.get('isTradedAway')],
    }


def get_salaryswish_team(conn, team_slug):
    team_slug = canonical_team_slug(team_slug)
    summary = conn.execute(
        'SELECT * FROM nba_salaryswish_team_summaries WHERE team_slug=?',
        (team_slug,),
    ).fetchone()
    if not summary:
        return None
    signing = conn.execute(
        '''
        SELECT * FROM nba_salaryswish_signing_exceptions
        WHERE team_slug=?
        ORDER BY sort_order ASC, name_en ASC
        ''',
        (team_slug,),
    ).fetchall()
    trades = conn.execute(
        '''
        SELECT * FROM nba_salaryswish_trade_exceptions
        WHERE team_slug=?
        ORDER BY sort_order ASC
        ''',
        (team_slug,),
    ).fetchall()
    draft = conn.execute(
        '''
        SELECT * FROM nba_salaryswish_draft_assets
        WHERE team_slug=?
        ORDER BY sort_order ASC
        ''',
        (team_slug,),
    ).fetchall()
    contracts = conn.execute(
        '''
        SELECT * FROM nba_salaryswish_contract_rows
        WHERE team_slug=?
        ORDER BY sort_order ASC
        ''',
        (team_slug,),
    ).fetchall()
    updated_values = [summary['updated_at'], summary['fetched_at']]
    return {
        'summary': row_to_summary(summary),
        'signingExceptions': [row_to_signing_exception(row) for row in signing],
        'tradeExceptions': [row_to_trade_exception(row) for row in trades],
        'draftAssets': [row_to_draft_asset(row) for row in draft],
        'rosterSections': grouped_contract_sections(contracts),
        'updatedAt': max(value for value in updated_values if value) if any(updated_values) else '',
    }
