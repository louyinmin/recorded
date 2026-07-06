import importlib
import os
import sqlite3
import tempfile
import unittest


PLAYER_PID = 'a537047d-c29f-4dfe-99b0-3bac4e258dc7'
SECOND_PID = 'c4475a2b-157d-45b4-ac0e-f5462ebcc8c9'
ROOKIE_DRAFT_URL = 'https://news.zhibo8.com/nba/2026-06-24/6a3b1f07f33eenative.htm'
ROOKIE_DETAIL_URL = 'https://news.zhibo8.com/nba/2026-05-27/6a1136ff7b2c0native.htm'
ROOKIE_OKORIE_DETAIL_URL = 'https://news.zhibo8.com/nba/2026-06-20/6a36504ce6c0fnative.htm'


def player_info(
    pid=PLAYER_PID,
    first_name='Luke',
    last_name='Kennard',
    first_name_cn='卢克',
    last_name_cn='肯纳德',
    position='后卫',
    team_tid='583ecae2-fb46-11e1-82cb-f4ce4684ea4c',
    team_market='洛杉矶',
    team_name='湖人',
):
    return {
        'result': {
            'status': {'code': 0, 'msg': 'player info'},
            'timestamp': 'Fri Jun 12 17:39:21 +0800 2026',
            'data': {
                'pid': pid,
                'first_name': first_name,
                'first_name_cn': first_name_cn,
                'last_name': last_name,
                'last_name_cn': last_name_cn,
                'primary_position': position,
                'jersey_number': 10,
                'birthdate': '1996-06-24',
                'age': 29,
                'experience': 8,
                'college': '杜克大学',
                'centimeter': 196,
                'kilo': 93,
                'nation': '美国',
                'wingspan': '196cm',
                'reach': '250cm',
                'salary': 1100,
                'draft_year': '2017',
                'draft_round': '1',
                'draft_pick': '12',
                'tid': team_tid,
                'team_name': team_name,
                'team_market': team_market,
            },
        },
    }


def player_leaders():
    return {
        'result': {
            'status': {'code': 0, 'msg': 'player item leaders'},
            'timestamp': 'Fri Jun 12 17:39:21 +0800 2026',
            'data': {
                'reg': {
                    'average': [
                        {'item': 'points', 'score': 8.4, 'rank': 155},
                        {'item': 'rebounds', 'score': 2.3, 'rank': 205},
                        {'item': 'assists', 'score': 2.2, 'rank': 114},
                        {'item': 'steals', 'score': 0.7, 'rank': 136},
                        {'item': 'blocks', 'score': 0.1, 'rank': 201},
                    ],
                },
            },
        },
    }


def team_rosters():
    return {
        'result': {
            'status': {'code': 0, 'msg': 'all team roster'},
            'data': {
                'league': {'season': 2025},
                'teams': [
                    {
                        'team': {
                            'market': 'Los Angeles',
                            'market_cn': '洛杉矶',
                            'name': 'Lakers',
                            'name_cn': '湖人',
                            'tid': '583ecae2-fb46-11e1-82cb-f4ce4684ea4c',
                        },
                        'players': [],
                    },
                ],
            },
        },
    }


def team_roster():
    return {
        'result': {
            'status': {'code': 0, 'msg': 'team season roster'},
            'data': {
                'team': {'season': '2025', 'name': '湖人', 'tid': '583ecae2-fb46-11e1-82cb-f4ce4684ea4c'},
                'roster': [
                    {'pid': PLAYER_PID, 'first_name': 'Luke', 'last_name': 'Kennard'},
                    {'pid': SECOND_PID, 'first_name': 'Jalen', 'last_name': 'Johnson'},
                ],
            },
        },
    }


def fake_sina_json(params, timeout=20):
    key = (params.get('s'), params.get('a'))
    if key == ('player', 'info'):
        if params.get('pid') == SECOND_PID:
            return player_info(
                SECOND_PID,
                'Jalen',
                'Johnson',
                '杰伦',
                '约翰逊',
                position='前锋',
                team_tid='583ecb8f-fb46-11e1-82cb-f4ce4684ea4c',
                team_market='亚特兰大',
                team_name='老鹰',
            )
        return player_info()
    if key == ('leaders', 'player'):
        return player_leaders()
    if key == ('team', 'rosters'):
        return team_rosters()
    if key == ('team', 'roster'):
        return team_roster()
    raise AssertionError('unexpected Sina params: {}'.format(params))


def rookie_draft_html():
    return '''
    <html><body>
      <p><strong>首轮汇总如下：</strong></p>
      <p>1、AJ·迪班萨 前锋 奇才</p>
      <p><a href="{}">模板麦迪的超强得分手！迪班萨依靠犀利进攻 锁定大年状元席位？</a></p>
      <p>17、埃布卡·奥科里 后卫 雷霆（来自76人）摘下之后交易去灰熊，再送往活塞</p>
      <p><a href="{}">斯坦福跑车！奥科里：力压布泽尔夺ACC得分王 模板马克西/施罗德</a></p>
    </body></html>
    '''.format(ROOKIE_DETAIL_URL, ROOKIE_OKORIE_DETAIL_URL)


def rookie_detail_html():
    return '''
    <html><body>
      <p><strong>姓名：</strong>AJ·迪班萨（AJ Dybantsa）</p>
      <p><strong>出生日期：</strong>2007年1月29日</p>
      <p><strong>位置：</strong>小前锋</p>
      <p><strong>球队：</strong>杨百翰大学</p>
      <p><strong>身高：</strong>6尺9（2米06）</p>
      <p><strong>体重：</strong>217磅（98公斤）</p>
      <p><strong>臂展：</strong>7尺1（2米16）</p>
      <p><strong>球员模板：</strong>安东尼/麦迪/保罗·乔治</p>
      <p><strong>顺位预测：</strong>状元</p>
      <p><strong>数据统计：</strong></p>
      <p>迪班萨大一赛季为球队出战了35场比赛，场均34.8分钟，可以得到25.5分6.8篮板3.7助攻1.1抢断。</p>
    </body></html>
    '''


def rookie_okorie_detail_html():
    return '''
    <html><body>
      <p><strong>姓名：</strong>埃布卡·奥科里（Ebuka Okorie）</p>
      <p><strong>出生日期：</strong>2007年4月10日</p>
      <p><strong>位置：</strong>控卫</p>
      <p><strong>球队：</strong>斯坦福大学（大一）</p>
      <p><strong>裸足身高：</strong>6尺1（1米86）</p>
      <p><strong>体重：</strong>186磅（84公斤）</p>
      <p><strong>臂展：</strong>6尺8（2米03）</p>
      <p><strong>球员模板：</strong>马克西/施罗德/雷吉·杰克逊</p>
      <p><strong>数据统计：</strong></p>
      <p>2025-26赛季，奥科里为斯坦福大学出战31场比赛，场均登场35.1分钟得到23.2分3.6篮板3.6助攻。</p>
      <p><strong>顺位预测：</strong>首轮中后段</p>
    </body></html>
    '''


def salaryswish_home_html():
    return '''
    <html><body>
      <h1>2026-27 SALARY CAP</h1>
      <table id="sw_homepage__table">
        <tr>
          <th>Team</th><th>Roster Size</th><th>Two-Ways</th><th>Cap Hit</th>
          <th>Cap Room</th><th>Luxury Room</th><th>1st Apron Rm</th><th>2nd Apron Rm</th><th>Hard Cap</th>
        </tr>
        <tr>
          <td><a href="/teams/lakers">Los Angeles LakersLAL</a></td>
          <td>19/21</td><td>3/3</td><td>$194,139,108</td><td>-$29,178,108</td>
          <td>$6,288,892</td><td>$14,875,892</td><td>$27,546,892</td><td>-</td>
        </tr>
      </table>
    </body></html>
    '''


def salaryswish_lakers_html():
    return '''
    <html><body>
      <h1 class="c">LOS ANGELES LAKERS</h1>
      <div class="c">
        <h5>CAP HIT : <span>$194,139,108</span></h5>
        <h5>CAP ROOM : <span>-$29,178,108</span></h5>
        <h5>TEAM SALARY : <span>$325,260,191</span></h5>
        <h5>TEAM SALARY ROOM : <span>-$160,299,191</span></h5>
        <h5>LUXURY TAX ROOM : <span>$6,288,892</span></h5>
        <h5>1ST APRON ROOM : <span>$14,875,892</span></h5>
        <h5>2ND APRON ROOM : <span>$27,546,892</span></h5>
        <h5>HARD CAPPED : <span><a href="/hard-cap-tracker">No</a></span></h5>
      </div>
      <div class="mb10">
        <div>ROSTER SIZE: <span>19/21</span></div>
        <div>TWO-WAY CONTRACTS: 3/3</div>
      </div>
      <div>HEAD EXECUTIVE: <a href="/staff/rob-pelinka">Rob Pelinka</a></div>
      <div>HEAD COACH: <a href="/staff/jj-redick">J.J. Redick</a></div>
      <div id="team_progress_list">
        <span class="progress_list_text"><a href="/bi-annual-exception"><strong>Bi-Annual:</strong></a> $0 of $0 remaining</span><span style="width:100%"></span>
        <span class="progress_list_text"><a href="/mid-level-exception"><strong>Mid-Level:</strong></a> $5,775,707 of $15,044,000 remaining</span><span style="width:61%"></span>
      </div>
      <table id="sw_table__tradeExptn_tm">
        <tr><th>Player</th><th>Exception</th><th>Used</th><th>Remaining</th><th>Start Date</th><th>End Date</th></tr>
        <tr>
          <td><a href="/players/luke-kennard">Kennard, Luke</a></td>
          <td><a href="/trades/466">$500,000</a></td><td>$0</td><td>$500,000</td>
          <td>Feb 5, 2026</td><td>Feb 5, 2027</td>
        </tr>
      </table>
      <table id="sw_teamProfile__draftTable">
        <tr><th>Draft</th><th>2027</th></tr>
        <tr>
          <td>Round 1</td>
          <td><a href="/draft/2027?pick=14"></a><img alt="Logo of the Los Angeles Lakers" src="lakers.svg"></td>
        </tr>
      </table>
      <table class="sw_teamProfileRosterSection__table">
        <tr>
          <th>Active (1 - $188,691,232)</th><th>Status</th><th>Acquired</th><th>Age</th><th>Pos</th><th>Terms</th>
          <th>2026-27</th><th>2027-28</th>
        </tr>
        <tr>
          <td><a href="/players/luke-kennard">Kennard, Luke</a></td><td>Active List</td><td>Trade</td><td>29</td><td>SG</td><td>MLE</td>
          <td>$11,000,000$11,000,000$0</td>
          <td><a href="/bird-rights-calculator/luke-kennard"></a><img alt="Bird" src="bird.svg">UFA</td>
        </tr>
        <tr>
          <td>TOTAL</td><td></td><td></td><td></td><td></td><td></td><td>$11,000,000</td><td></td>
        </tr>
      </table>
      <table class="sw_teamProfileRosterSection__table">
        <tr>
          <th>1st Rd Picks (1 - $3,315,360)</th><th>Status</th><th>Acquired</th><th>Age</th><th>Pos</th><th>Terms</th>
          <th>2026-27</th><th>2027-28</th>
        </tr>
        <tr>
          <td><a href="/players/cameron-carr">Carr, Cameron</a></td><td>120% RSC Hold</td><td></td><td>21</td><td>SG</td><td></td>
          <td>$3,315,360</td><td></td>
        </tr>
      </table>
      <table class="sw_teamProfileRosterSection__table">
        <tr>
          <th>Buyout (1 - $1,000,000)</th><th>Status</th><th>Acquired</th><th>Age</th><th>Pos</th><th>Terms</th>
          <th>2026-27</th><th>2027-28</th>
        </tr>
        <tr>
          <td><a href="/players/example-buyout">Buyout, Example</a></td><td>Buyout</td><td></td><td>30</td><td>SF</td><td></td>
          <td>$1,000,000</td><td></td>
        </tr>
      </table>
    </body></html>
    '''


class NbaBackendTestCase(unittest.TestCase):
    def setUp(self):
        self.base_dir = tempfile.mkdtemp(prefix='nba-backend-test-')
        self.db_path = os.path.join(self.base_dir, 'data.db')
        self.life_db_path = os.path.join(self.base_dir, 'life.db')
        self.nba_db_path = os.path.join(self.base_dir, 'nba.db')
        self.nba_image_dir = os.path.join(self.base_dir, 'nba_images')
        self.nba_avatar_dir = os.path.join(self.base_dir, 'nba_avatar')
        self.nba_team_image_dir = os.path.join(self.base_dir, 'nba_team_images')
        os.makedirs(self.nba_image_dir)
        os.makedirs(self.nba_avatar_dir)
        os.makedirs(self.nba_team_image_dir)
        with open(os.path.join(self.nba_image_dir, 'Luke_Kennard.jpg'), 'wb') as handle:
            handle.write(b'fake-jpg')
        with open(os.path.join(self.nba_avatar_dir, 'Luke_Kennard.png'), 'wb') as handle:
            handle.write(b'fake-png')
        with open(os.path.join(self.nba_team_image_dir, 'Los_Angeles_Lakers.png'), 'wb') as handle:
            handle.write(b'fake-team-png')
        os.environ['RECORDED_BASE_DIR'] = self.base_dir
        os.environ['RECORDED_DB_PATH'] = self.db_path
        os.environ['LIFE_DB_PATH'] = self.life_db_path
        os.environ['NBA_DB_PATH'] = self.nba_db_path
        os.environ['NBA_IMAGE_DIR'] = self.nba_image_dir
        os.environ['NBA_AVATAR_DIR'] = self.nba_avatar_dir
        os.environ['NBA_TEAM_IMAGE_DIR'] = self.nba_team_image_dir
        os.environ.pop('NBA_SYNC_TOKEN', None)

        self.app_module = importlib.import_module('app')
        self.app_module = importlib.reload(self.app_module)
        self.app_module.init_db()
        self.client = self.app_module.app.test_client()

    def patch_sina_fetch(self):
        import nba_backend.service as service

        original = service.fetch_sina_json
        service.fetch_sina_json = fake_sina_json
        self.addCleanup(lambda: setattr(service, 'fetch_sina_json', original))

    def patch_zhibo8_fetch(self):
        import nba_backend.service as service

        pages = {
            ROOKIE_DRAFT_URL: rookie_draft_html(),
            ROOKIE_DETAIL_URL: rookie_detail_html(),
            ROOKIE_OKORIE_DETAIL_URL: rookie_okorie_detail_html(),
        }

        def fake_fetch(url, timeout=20):
            if url not in pages:
                raise AssertionError('unexpected Zhibo8 URL: {}'.format(url))
            return pages[url]

        original = service.fetch_zhibo8_html
        service.fetch_zhibo8_html = fake_fetch
        self.addCleanup(lambda: setattr(service, 'fetch_zhibo8_html', original))

    def patch_salaryswish_fetch(self):
        import nba_backend.salaryswish as salaryswish

        pages = {
            'https://www.salaryswish.com/': salaryswish_home_html(),
            'https://www.salaryswish.com/teams/lakers': salaryswish_lakers_html(),
        }

        def fake_fetch(url, timeout=20):
            if url not in pages:
                raise AssertionError('unexpected SalarySwish URL: {}'.format(url))
            return pages[url]

        original = salaryswish.fetch_salaryswish_html
        salaryswish.fetch_salaryswish_html = fake_fetch
        self.addCleanup(lambda: setattr(salaryswish, 'fetch_salaryswish_html', original))

    def test_asset_name_matching_handles_short_names_and_middle_names(self):
        from nba_backend.service import collect_image_index, match_image_filename

        filenames = [
            'Alex_Sarr.png',
            'Cam_Whitmore.png',
            'Olivier_Maxence_Prosper.png',
            'Yves_Missi.png',
            'Bones_Hyland.png',
        ]
        for filename in filenames:
            with open(os.path.join(self.nba_avatar_dir, filename), 'wb') as handle:
                handle.write(b'fake-png')
        image_index, collisions = collect_image_index(self.nba_avatar_dir)

        self.assertEqual(collisions, {})
        self.assertEqual(match_image_filename('Alexandre Sarr', image_index), 'Alex_Sarr.png')
        self.assertEqual(match_image_filename('Cameron Whitmore', image_index), 'Cam_Whitmore.png')
        self.assertEqual(
            match_image_filename('Olivier-Maxence Gaetan Prosper', image_index),
            'Olivier_Maxence_Prosper.png',
        )
        self.assertEqual(match_image_filename('Yves Thierry Ouwe Missi', image_index), 'Yves_Missi.png')
        self.assertEqual(match_image_filename("Nah'Shon Hyland", image_index), 'Bones_Hyland.png')

    def test_2026_rookie_summary_uses_final_traded_team(self):
        from nba_backend.service import parse_2026_rookie_summaries

        summaries = parse_2026_rookie_summaries(rookie_draft_html())
        by_pick = {item['draft_pick']: item for item in summaries}

        self.assertEqual(by_pick[1]['selected_team'], '奇才')
        self.assertEqual(by_pick[17]['selected_team'], '活塞')
        self.assertEqual(by_pick[17]['selection_text'], '雷霆（来自76人）摘下之后交易去灰熊，再送往活塞')

    def test_sync_2026_rookies_adds_rookie_team_and_extension_fields(self):
        self.patch_zhibo8_fetch()

        response = self.client.post('/api/nba/sync/rookies-2026')

        self.assertEqual(response.status_code, 200)
        result = response.get_json()['result']
        self.assertEqual(result['succeeded_count'], 2)
        self.assertEqual(result['failed_count'], 0)

        filters = self.client.get('/api/nba/filters')
        self.assertEqual(filters.status_code, 200)
        teams = {item['full_name']: item for item in filters.get_json()['teams']}
        self.assertIn('2026 新秀', teams)
        self.assertEqual(teams['2026 新秀']['player_count'], 2)

        listed = self.client.get('/api/nba/players?team=2026%20%E6%96%B0%E7%A7%80')
        self.assertEqual(listed.status_code, 200)
        payload = listed.get_json()
        self.assertEqual(payload['total'], 2)
        player = next(item for item in payload['items'] if item['chinese_name'] == 'AJ·迪班萨')
        self.assertEqual(player['source'], 'zhibo8_2026_rookies')
        self.assertEqual(player['team']['full_name'], '2026 新秀')
        self.assertEqual(player['profile']['draft_pick'], '1')
        self.assertEqual(player['profile']['college'], '杨百翰大学')
        self.assertEqual(player['profile']['height_cm'], 206)
        self.assertEqual(player['profile']['weight_kg'], 98)
        self.assertEqual(player['extension']['rookie']['selected_team'], '奇才')
        self.assertEqual(player['extension']['rookie']['university_team'], '杨百翰大学')
        self.assertEqual(player['extension']['rookie']['tag']['title'], '模板麦迪的超强得分手！迪班萨依靠犀利进攻 锁定大年状元席位？')
        self.assertNotIn('顺位预测', player['extension']['rookie'])

        okorie = next(item for item in payload['items'] if item['chinese_name'] == '埃布卡·奥科里')
        self.assertEqual(okorie['extension']['rookie']['selected_team'], '活塞')
        self.assertEqual(okorie['extension']['rookie']['selection_text'], '雷霆（来自76人）摘下之后交易去灰熊，再送往活塞')

        images = self.client.post('/api/nba/sync/images')
        avatars = self.client.post('/api/nba/sync/avatars')
        self.assertEqual(images.status_code, 200)
        self.assertEqual(avatars.status_code, 200)
        missing_images = {item['english_name'] for item in self.client.get('/api/nba/images/missing').get_json()['items']}
        missing_avatars = {item['english_name'] for item in self.client.get('/api/nba/avatars/missing').get_json()['items']}
        self.assertIn('AJ Dybantsa', missing_images)
        self.assertIn('AJ Dybantsa', missing_avatars)

    def test_sync_single_player_collects_expected_fields(self):
        self.patch_sina_fetch()
        response = self.client.post('/api/nba/sync/player', json={'pid': PLAYER_PID})
        self.assertEqual(response.status_code, 200)
        player = response.get_json()['player']
        self.assertEqual(player['chinese_name'], '卢克-肯纳德')
        self.assertEqual(player['english_name'], 'Luke Kennard')
        self.assertEqual(player['team']['full_name'], '洛杉矶湖人')
        self.assertEqual(player['jersey_number'], '10')
        self.assertEqual(player['primary_position'], '后卫')
        self.assertEqual(player['profile']['birthdate'], '1996-06-24')
        self.assertEqual(player['profile']['age'], 29)
        self.assertEqual(player['profile']['nation'], '美国')
        self.assertEqual(player['profile']['college'], '杜克大学')
        self.assertEqual(player['profile']['experience'], 8)
        self.assertEqual(player['profile']['draft_year'], '2017')
        self.assertEqual(player['profile']['draft_round'], '1')
        self.assertEqual(player['profile']['draft_pick'], '12')
        self.assertEqual(player['profile']['height_cm'], 196)
        self.assertEqual(player['profile']['weight_kg'], 93)
        self.assertEqual(player['profile']['wingspan'], '196cm')
        self.assertEqual(player['profile']['standing_reach'], '250cm')
        self.assertEqual(player['profile']['current_salary'], '1100万美元')
        self.assertEqual(player['stats']['avg_points'], 8.4)
        self.assertEqual(player['stats']['avg_rebounds'], 2.3)
        self.assertEqual(player['stats']['avg_assists'], 2.2)
        self.assertEqual(player['stats']['avg_steals'], 0.7)
        self.assertEqual(player['stats']['avg_blocks'], 0.1)

        detail = self.client.get('/api/nba/players/{}'.format(PLAYER_PID))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()['source'], 'sina_nba')

    def test_sync_salaryswish_collects_team_salary_data_for_miniprogram(self):
        self.patch_sina_fetch()
        self.patch_salaryswish_fetch()
        synced_player = self.client.post('/api/nba/sync/player', json={'pid': PLAYER_PID})
        self.assertEqual(synced_player.status_code, 200)

        synced = self.client.post('/api/nba/sync/salaryswish', json={'teamSlug': 'lakers', 'concurrency': 1})

        self.assertEqual(synced.status_code, 200)
        result = synced.get_json()['result']
        self.assertEqual(result['season'], '2026-27')
        self.assertEqual(result['succeeded_count'], 1)
        self.assertEqual(result['failed_count'], 0)

        teams = self.client.get('/api/nba/salaryswish/teams')
        self.assertEqual(teams.status_code, 200)
        team = teams.get_json()['items'][0]
        self.assertEqual(team['teamNameCn'], '洛杉矶湖人')
        self.assertEqual(team['capHit'], '$194,139,108')
        self.assertEqual(team['rosterSize']['count'], 19)

        detail = self.client.get('/api/nba/salaryswish/teams/lakers')
        self.assertEqual(detail.status_code, 200)
        payload = detail.get_json()
        self.assertEqual(payload['summary']['hardCappedCn'], '否')
        self.assertEqual(payload['summary']['headCoach'], 'J.J. Redick')
        self.assertEqual(payload['signingExceptions'][1]['nameCn'], '中产特例')
        self.assertEqual(payload['tradeExceptions'][0]['playerNameCn'], '卢克-肯纳德')
        self.assertEqual(payload['draftAssets'][0]['assets'][0]['teamNameCn'], '洛杉矶湖人')

        active = payload['rosterSections'][0]
        self.assertEqual(active['titleCn'], '现役')
        contract = active['items'][0]
        self.assertEqual(contract['playerNameEn'], 'Luke Kennard')
        self.assertEqual(contract['playerNameCn'], '卢克-肯纳德')
        self.assertEqual(contract['playerPid'], PLAYER_PID)
        self.assertEqual(contract['statusCn'], '活跃名单')
        self.assertEqual(contract['acquiredCn'], '交易')
        self.assertEqual(contract['positionsCn'], '分卫')
        self.assertEqual(contract['termsCn'], '中产特例')
        self.assertEqual(contract['seasonSalaries'][0]['value'], '$11,000,000')
        self.assertEqual(contract['seasonSalaries'][1]['freeAgentStatusCn'], '完全自由球员')
        sections_by_key = {section['sectionKey']: section for section in payload['rosterSections']}
        self.assertEqual(sections_by_key['1st_rd_picks']['titleCn'], '首轮签')
        self.assertEqual(sections_by_key['buyout']['titleCn'], '买断')
        self.assertEqual(sections_by_key['buyout']['items'][0]['statusCn'], '买断')

    def test_sync_salaryswish_rejects_string_team_slugs(self):
        response = self.client.post('/api/nba/sync/salaryswish', json={'teamSlugs': 'lakers'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'teamSlugs must be an array of team slugs'})

    def test_sync_salaryswish_rejects_non_string_team_slug_items(self):
        response = self.client.post('/api/nba/sync/salaryswish', json={'teamSlugs': [123]})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'teamSlugs must contain only strings'})

    def test_sync_salaryswish_rejects_non_string_single_team_slug(self):
        response = self.client.post('/api/nba/sync/salaryswish', json={'teamSlug': 123})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'teamSlug must be a string'})

    def test_list_players_supports_search_after_batch_sync(self):
        self.patch_sina_fetch()
        response = self.client.post('/api/nba/sync', json={'limitTeams': 1, 'concurrency': 2})
        self.assertEqual(response.status_code, 200)
        result = response.get_json()['result']
        self.assertEqual(result['requested_count'], 2)
        self.assertEqual(result['succeeded_count'], 2)
        self.assertEqual(result['failed_count'], 0)

        listed = self.client.get('/api/nba/players?q=卢克')
        self.assertEqual(listed.status_code, 200)
        payload = listed.get_json()
        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['items'][0]['pid'], PLAYER_PID)

    def test_players_batch_returns_details_in_request_order_with_version(self):
        self.patch_sina_fetch()
        response = self.client.post('/api/nba/sync', json={'limitTeams': 1, 'concurrency': 2})
        self.assertEqual(response.status_code, 200)

        batch = self.client.get(
            '/api/nba/players/batch?pids={0},missing-player,{1},{0}'.format(PLAYER_PID, SECOND_PID)
        )

        self.assertEqual(batch.status_code, 200)
        payload = batch.get_json()
        self.assertEqual([item['pid'] for item in payload['items']], [PLAYER_PID, SECOND_PID])
        self.assertEqual(payload['missingPids'], ['missing-player'])
        self.assertTrue(payload['dataVersion'].startswith('home_'))
        self.assertEqual(payload['items'][0]['team']['full_name'], '洛杉矶湖人')
        self.assertEqual(payload['items'][1]['profile']['draft_year'], '2017')

        repeat = self.client.get(
            '/api/nba/players/batch?pids={0},missing-player,{1},{0}'.format(PLAYER_PID, SECOND_PID)
        )
        self.assertEqual(repeat.status_code, 200)
        self.assertEqual(repeat.get_json()['dataVersion'], payload['dataVersion'])

        conn = sqlite3.connect(self.nba_db_path)
        try:
            conn.execute(
                "UPDATE nba_players SET jersey_number='11', updated_at='2026-06-20T08:30:00' WHERE pid=?",
                (SECOND_PID,),
            )
            conn.commit()
        finally:
            conn.close()

        changed = self.client.get('/api/nba/players/batch?pids={},{}'.format(PLAYER_PID, SECOND_PID))
        self.assertNotEqual(changed.get_json()['dataVersion'], payload['dataVersion'])

    def test_players_batch_rejects_too_many_pids(self):
        pids = ','.join('player-{}'.format(index) for index in range(51))

        response = self.client.get('/api/nba/players/batch?pids=' + pids)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'too many pids', 'limit': 50})

    def test_players_support_team_position_filters_and_name_search(self):
        self.patch_sina_fetch()
        response = self.client.post('/api/nba/sync', json={'limitTeams': 1, 'concurrency': 2})
        self.assertEqual(response.status_code, 200)

        by_team = self.client.get('/api/nba/players?team=老鹰')
        self.assertEqual(by_team.status_code, 200)
        by_team_payload = by_team.get_json()
        self.assertEqual(by_team_payload['total'], 1)
        self.assertEqual(by_team_payload['items'][0]['pid'], SECOND_PID)

        by_team_tid = self.client.get('/api/nba/players?teamTid=583ecae2-fb46-11e1-82cb-f4ce4684ea4c')
        self.assertEqual(by_team_tid.status_code, 200)
        self.assertEqual(by_team_tid.get_json()['items'][0]['pid'], PLAYER_PID)

        by_position = self.client.get('/api/nba/players?position=前锋')
        self.assertEqual(by_position.status_code, 200)
        self.assertEqual(by_position.get_json()['items'][0]['pid'], SECOND_PID)

        chinese_search = self.client.get('/api/nba/players/search?q=卢克')
        self.assertEqual(chinese_search.status_code, 200)
        self.assertEqual(chinese_search.get_json()['items'][0]['pid'], PLAYER_PID)

        english_search = self.client.get('/api/nba/players/search?q=Jalen')
        self.assertEqual(english_search.status_code, 200)
        self.assertEqual(english_search.get_json()['items'][0]['pid'], SECOND_PID)

        filters = self.client.get('/api/nba/filters')
        self.assertEqual(filters.status_code, 200)
        payload = filters.get_json()
        teams = {item['full_name'] for item in payload['teams']}
        positions = {item['position'] for item in payload['positions']}
        self.assertIn('洛杉矶湖人', teams)
        self.assertIn('亚特兰大老鹰', teams)
        self.assertIn('后卫', positions)
        self.assertIn('前锋', positions)

    def test_sync_images_links_cards_and_marks_missing(self):
        self.patch_sina_fetch()
        synced = self.client.post('/api/nba/sync', json={'limitTeams': 1, 'concurrency': 2})
        self.assertEqual(synced.status_code, 200)

        images = self.client.post('/api/nba/sync/images')
        self.assertEqual(images.status_code, 200)
        result = images.get_json()['result']
        self.assertEqual(result['matched_count'], 1)
        self.assertEqual(result['missing_count'], 1)
        self.assertEqual(result['missing'][0]['pid'], SECOND_PID)

        detail = self.client.get('/api/nba/players/{}'.format(PLAYER_PID))
        self.assertEqual(detail.status_code, 200)
        image = detail.get_json()['image']
        self.assertFalse(image['missing'])
        self.assertEqual(image['filename'], 'Luke_Kennard.jpg')
        self.assertEqual(image['url'], '/api/nba/card-images/Luke_Kennard.jpg')
        self.assertNotIn('path', image)
        self.assertNotIn('image_path', detail.get_json())
        cards = detail.get_json()['cards']
        self.assertEqual([card['cardId'] for card in cards], [PLAYER_PID + '_default'])
        self.assertEqual(cards[0]['image']['filename'], 'Luke_Kennard.jpg')

        missing = self.client.get('/api/nba/images/missing')
        self.assertEqual(missing.status_code, 200)
        self.assertEqual(missing.get_json()['items'][0]['pid'], SECOND_PID)

    def test_sync_images_supports_numbered_english_name_cards(self):
        self.patch_sina_fetch()
        synced = self.client.post('/api/nba/sync', json={'limitTeams': 1, 'concurrency': 2})
        self.assertEqual(synced.status_code, 200)
        with open(os.path.join(self.nba_image_dir, 'Luke_Kennard_1.jpg'), 'wb') as handle:
            handle.write(b'second-card')
        with open(os.path.join(self.nba_image_dir, 'Luke_Kennard_2.jpg'), 'wb') as handle:
            handle.write(b'third-card')

        images = self.client.post('/api/nba/sync/images')
        self.assertEqual(images.status_code, 200)
        result = images.get_json()['result']
        self.assertEqual(result['matched_count'], 1)
        self.assertEqual(result['card_count'], 3)
        self.assertEqual(result['namingRule']['preferred'], 'English_Name.{ext}, English_Name_1.{ext}, English_Name_2.{ext}')

        detail = self.client.get('/api/nba/players/{}'.format(PLAYER_PID))
        self.assertEqual(detail.status_code, 200)
        cards = detail.get_json()['cards']
        self.assertEqual(
            [card['cardId'] for card in cards],
            [PLAYER_PID + '_default', PLAYER_PID + '_1', PLAYER_PID + '_2'],
        )
        self.assertEqual([card['sortOrder'] for card in cards], [10, 20, 30])
        self.assertEqual(
            [card['image']['filename'] for card in cards],
            ['Luke_Kennard.jpg', 'Luke_Kennard_1.jpg', 'Luke_Kennard_2.jpg'],
        )
        self.assertEqual(detail.get_json()['image']['filename'], 'Luke_Kennard.jpg')

    def test_sync_images_supports_multiple_pid_named_cards(self):
        self.patch_sina_fetch()
        synced = self.client.post('/api/nba/sync', json={'limitTeams': 1, 'concurrency': 2})
        self.assertEqual(synced.status_code, 200)
        os.remove(os.path.join(self.nba_image_dir, 'Luke_Kennard.jpg'))
        with open(os.path.join(self.nba_image_dir, PLAYER_PID + '_2024_base.jpg'), 'wb') as handle:
            handle.write(b'base-card')
        with open(os.path.join(self.nba_image_dir, PLAYER_PID + '_2024_alt.jpg'), 'wb') as handle:
            handle.write(b'alt-card')

        images = self.client.post('/api/nba/sync/images')
        self.assertEqual(images.status_code, 200)
        result = images.get_json()['result']
        self.assertEqual(result['matched_count'], 1)
        self.assertEqual(result['card_count'], 2)
        self.assertEqual(result['namingRule']['pidPreferred'], '{pid}_{season}_{variant}.{ext}')

        detail = self.client.get('/api/nba/players/{}'.format(PLAYER_PID))
        self.assertEqual(detail.status_code, 200)
        detail_payload = detail.get_json()
        self.assertEqual(
            [card['cardId'] for card in detail_payload['cards']],
            [PLAYER_PID + '_2024_base', PLAYER_PID + '_2024_alt'],
        )
        self.assertEqual([card['sortOrder'] for card in detail_payload['cards']], [10, 20])
        self.assertEqual(detail_payload['image']['filename'], PLAYER_PID + '_2024_base.jpg')

        cards = self.client.get('/api/nba/players/{}/cards'.format(PLAYER_PID))
        self.assertEqual(cards.status_code, 200)
        self.assertEqual(len(cards.get_json()['items']), 2)

        batch = self.client.get('/api/nba/players/batch?pids={}'.format(PLAYER_PID))
        self.assertEqual(batch.status_code, 200)
        self.assertEqual(len(batch.get_json()['items'][0]['cards']), 2)

        image = self.client.get('/api/nba/card-images/' + PLAYER_PID + '_2024_base.jpg')
        try:
            self.assertEqual(image.status_code, 200)
            self.assertEqual(image.data, b'base-card')
        finally:
            image.close()

    def test_sync_avatars_links_headshots_and_marks_missing(self):
        self.patch_sina_fetch()
        synced = self.client.post('/api/nba/sync', json={'limitTeams': 1, 'concurrency': 2})
        self.assertEqual(synced.status_code, 200)

        avatars = self.client.post('/api/nba/sync/avatars')
        self.assertEqual(avatars.status_code, 200)
        result = avatars.get_json()['result']
        self.assertEqual(result['matched_count'], 1)
        self.assertEqual(result['missing_count'], 1)
        self.assertEqual(result['missing'][0]['pid'], SECOND_PID)

        detail = self.client.get('/api/nba/players/{}'.format(PLAYER_PID))
        self.assertEqual(detail.status_code, 200)
        avatar = detail.get_json()['avatar']
        self.assertFalse(avatar['missing'])
        self.assertEqual(avatar['filename'], 'Luke_Kennard.png')
        self.assertEqual(avatar['url'], '/api/nba/avatars/Luke_Kennard.png')
        self.assertNotIn('path', avatar)
        self.assertNotIn('avatar_path', detail.get_json())

        missing = self.client.get('/api/nba/avatars/missing')
        self.assertEqual(missing.status_code, 200)
        self.assertEqual(missing.get_json()['items'][0]['pid'], SECOND_PID)

    def test_sync_avatars_ignores_request_avatar_dir(self):
        self.patch_sina_fetch()
        synced = self.client.post('/api/nba/sync/player', json={'pid': PLAYER_PID})
        self.assertEqual(synced.status_code, 200)

        other_dir = os.path.join(self.base_dir, 'other_avatars')
        os.makedirs(other_dir)
        with open(os.path.join(other_dir, 'Jalen_Johnson.png'), 'wb') as handle:
            handle.write(b'wrong-dir')

        avatars = self.client.post('/api/nba/sync/avatars', json={'avatarDir': other_dir})
        self.assertEqual(avatars.status_code, 200)
        self.assertNotIn('avatar_dir', avatars.get_json()['result'])

        detail = self.client.get('/api/nba/players/{}'.format(PLAYER_PID))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()['avatar']['filename'], 'Luke_Kennard.png')

        conn = sqlite3.connect(self.nba_db_path)
        try:
            row = conn.execute('SELECT avatar_path FROM nba_players WHERE pid=?', (PLAYER_PID,)).fetchone()
            self.assertTrue(row[0].startswith(self.nba_avatar_dir))
        finally:
            conn.close()

    def test_sync_team_images_links_logos_and_marks_missing(self):
        self.patch_sina_fetch()
        synced = self.client.post('/api/nba/sync', json={'limitTeams': 1, 'concurrency': 2})
        self.assertEqual(synced.status_code, 200)

        logos = self.client.post('/api/nba/sync/team-images')
        self.assertEqual(logos.status_code, 200)
        result = logos.get_json()['result']
        self.assertEqual(result['matched_count'], 1)
        self.assertEqual(result['missing_count'], 1)
        self.assertEqual(result['missing'][0]['team_full_name'], '亚特兰大老鹰')

        detail = self.client.get('/api/nba/players/{}'.format(PLAYER_PID))
        self.assertEqual(detail.status_code, 200)
        logo = detail.get_json()['team']['logo']
        self.assertFalse(logo['missing'])
        self.assertEqual(logo['filename'], 'Los_Angeles_Lakers.png')
        self.assertEqual(logo['url'], '/api/nba/team-images/Los_Angeles_Lakers.png')
        self.assertNotIn('path', logo)
        self.assertNotIn('team_image_path', detail.get_json())

        filters = self.client.get('/api/nba/filters')
        self.assertEqual(filters.status_code, 200)
        teams = {item['full_name']: item for item in filters.get_json()['teams']}
        self.assertEqual(teams['洛杉矶湖人']['logo']['filename'], 'Los_Angeles_Lakers.png')

        image = self.client.get('/api/nba/team-images/Los_Angeles_Lakers.png')
        try:
            self.assertEqual(image.status_code, 200)
            self.assertEqual(image.data, b'fake-team-png')
        finally:
            image.close()

        missing = self.client.get('/api/nba/team-images/missing')
        self.assertEqual(missing.status_code, 200)
        self.assertEqual(missing.get_json()['items'][0]['team_full_name'], '亚特兰大老鹰')

    def test_sync_team_images_ignores_request_team_image_dir(self):
        self.patch_sina_fetch()
        synced = self.client.post('/api/nba/sync/player', json={'pid': PLAYER_PID})
        self.assertEqual(synced.status_code, 200)

        other_dir = os.path.join(self.base_dir, 'other_team_images')
        os.makedirs(other_dir)
        with open(os.path.join(other_dir, 'Atlanta_Hawks.png'), 'wb') as handle:
            handle.write(b'wrong-dir')

        logos = self.client.post('/api/nba/sync/team-images', json={'teamImageDir': other_dir})
        self.assertEqual(logos.status_code, 200)
        self.assertNotIn('team_image_dir', logos.get_json()['result'])

        detail = self.client.get('/api/nba/players/{}'.format(PLAYER_PID))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()['team']['logo']['filename'], 'Los_Angeles_Lakers.png')

        conn = sqlite3.connect(self.nba_db_path)
        try:
            row = conn.execute('SELECT team_image_path FROM nba_players WHERE pid=?', (PLAYER_PID,)).fetchone()
            self.assertTrue(row[0].startswith(self.nba_team_image_dir))
        finally:
            conn.close()

    def test_sync_images_ignores_request_image_dir(self):
        self.patch_sina_fetch()
        synced = self.client.post('/api/nba/sync/player', json={'pid': PLAYER_PID})
        self.assertEqual(synced.status_code, 200)

        other_dir = os.path.join(self.base_dir, 'other_images')
        os.makedirs(other_dir)
        with open(os.path.join(other_dir, 'Jalen_Johnson.jpg'), 'wb') as handle:
            handle.write(b'wrong-dir')

        images = self.client.post('/api/nba/sync/images', json={'imageDir': other_dir})
        self.assertEqual(images.status_code, 200)
        self.assertNotIn('image_dir', images.get_json()['result'])

        detail = self.client.get('/api/nba/players/{}'.format(PLAYER_PID))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()['image']['filename'], 'Luke_Kennard.jpg')

        conn = sqlite3.connect(self.nba_db_path)
        try:
            row = conn.execute('SELECT image_path FROM nba_players WHERE pid=?', (PLAYER_PID,)).fetchone()
            self.assertTrue(row[0].startswith(self.nba_image_dir))
        finally:
            conn.close()

    def test_sync_token_is_required_when_configured(self):
        os.environ['NBA_SYNC_TOKEN'] = 'secret-token'
        self.patch_sina_fetch()
        forbidden = self.client.post('/api/nba/sync/player', json={'pid': PLAYER_PID})
        allowed = self.client.post(
            '/api/nba/sync/player',
            headers={'X-NBA-Sync-Token': 'secret-token'},
            json={'pid': PLAYER_PID},
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(allowed.status_code, 200)
