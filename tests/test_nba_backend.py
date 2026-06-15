import importlib
import os
import sqlite3
import tempfile
import unittest


PLAYER_PID = 'a537047d-c29f-4dfe-99b0-3bac4e258dc7'
SECOND_PID = 'c4475a2b-157d-45b4-ac0e-f5462ebcc8c9'


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


class NbaBackendTestCase(unittest.TestCase):
    def setUp(self):
        self.base_dir = tempfile.mkdtemp(prefix='nba-backend-test-')
        self.db_path = os.path.join(self.base_dir, 'data.db')
        self.life_db_path = os.path.join(self.base_dir, 'life.db')
        self.nba_db_path = os.path.join(self.base_dir, 'nba.db')
        self.nba_image_dir = os.path.join(self.base_dir, 'nba_images')
        os.makedirs(self.nba_image_dir)
        with open(os.path.join(self.nba_image_dir, 'Luke_Kennard.jpg'), 'wb') as handle:
            handle.write(b'fake-jpg')
        os.environ['RECORDED_BASE_DIR'] = self.base_dir
        os.environ['RECORDED_DB_PATH'] = self.db_path
        os.environ['LIFE_DB_PATH'] = self.life_db_path
        os.environ['NBA_DB_PATH'] = self.nba_db_path
        os.environ['NBA_IMAGE_DIR'] = self.nba_image_dir
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
        self.assertEqual(image['url'], '/api/nba/images/Luke_Kennard.jpg')
        self.assertNotIn('path', image)
        self.assertNotIn('image_path', detail.get_json())

        missing = self.client.get('/api/nba/images/missing')
        self.assertEqual(missing.status_code, 200)
        self.assertEqual(missing.get_json()['items'][0]['pid'], SECOND_PID)

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
