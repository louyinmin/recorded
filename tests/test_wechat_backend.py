import importlib
import json
import os
import sqlite3
import tempfile
import unittest


class WeChatBackendTestCase(unittest.TestCase):
    def setUp(self):
        self.base_dir = tempfile.mkdtemp(prefix='wechat-backend-test-')
        self.db_path = os.path.join(self.base_dir, 'data.db')
        self.life_db_path = os.path.join(self.base_dir, 'life.db')
        self.nba_db_path = os.path.join(self.base_dir, 'nba.db')
        self.wechat_db_path = os.path.join(self.base_dir, 'wechat.db')
        os.environ['RECORDED_BASE_DIR'] = self.base_dir
        os.environ['RECORDED_DB_PATH'] = self.db_path
        os.environ['LIFE_DB_PATH'] = self.life_db_path
        os.environ['NBA_DB_PATH'] = self.nba_db_path
        os.environ['WECHAT_DB_PATH'] = self.wechat_db_path
        os.environ.pop('WECHAT_MINIPROGRAM_APPID', None)
        os.environ.pop('WECHAT_MINIPROGRAM_SECRET', None)
        os.environ['WECHAT_MINIPROGRAM_NBA_APPID'] = 'nba-appid'
        os.environ['WECHAT_MINIPROGRAM_NBA_SECRET'] = 'nba-secret'
        os.environ['WECHAT_MINIPROGRAM_TIMING_APPID'] = 'timing-appid'
        os.environ['WECHAT_MINIPROGRAM_TIMING_SECRET'] = 'timing-secret'

        self.app_module = importlib.import_module('app')
        self.app_module = importlib.reload(self.app_module)
        self.app_module.init_db()
        self.client = self.app_module.app.test_client()

    def patch_code_exchange(self, handler):
        import wechat_backend.service as service
        import wechat_backend.routes as routes

        original_service = service.exchange_wechat_code
        original_routes = routes.exchange_wechat_code
        service.exchange_wechat_code = handler
        routes.exchange_wechat_code = handler
        self.addCleanup(lambda: setattr(service, 'exchange_wechat_code', original_service))
        self.addCleanup(lambda: setattr(routes, 'exchange_wechat_code', original_routes))

    def insert_nba_player(self, pid, updated_at, chinese_name='测试球员', english_name='Test Player'):
        conn = sqlite3.connect(self.nba_db_path)
        try:
            conn.execute(
                '''
                INSERT INTO nba_players (pid, chinese_name, english_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (pid, chinese_name, english_name, updated_at, updated_at),
            )
            conn.commit()
        finally:
            conn.close()

    def test_session_requires_code(self):
        response = self.client.post('/api/wechat/session', json={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'code is required'})

    def test_session_creates_stable_user_without_returning_session_key(self):
        calls = []

        def fake_exchange(appid, secret, code):
            calls.append((appid, secret, code))
            return {
                'openid': 'openid-123',
                'unionid': 'unionid-456',
                'session_key': 'do-not-return',
            }

        self.patch_code_exchange(fake_exchange)

        first = self.client.post('/api/wechat/session', json={'app': 'nba', 'code': 'code-one'})
        second = self.client.post('/api/wechat/session', json={'app': 'nba', 'code': 'code-two'})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        first_payload = first.get_json()
        second_payload = second.get_json()
        self.assertEqual(first_payload['userId'], second_payload['userId'])
        self.assertEqual(first_payload['openid'], 'openid-123')
        self.assertEqual(first_payload['unionid'], 'unionid-456')
        self.assertEqual(first_payload['app'], 'nba')
        self.assertIn('sessionToken', first_payload)
        self.assertIn('expiresAt', first_payload)
        self.assertNotIn('session_key', first_payload)
        self.assertEqual(calls[0], ('nba-appid', 'nba-secret', 'code-one'))

        conn = sqlite3.connect(self.wechat_db_path)
        try:
            row_count = conn.execute('SELECT COUNT(*) FROM wechat_users').fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(row_count, 1)

    def test_session_maps_wechat_error_to_unauthorized(self):
        from wechat_backend.service import WeChatCodeExchangeError

        def fake_exchange(appid, secret, code):
            raise WeChatCodeExchangeError(40029)

        self.patch_code_exchange(fake_exchange)

        response = self.client.post('/api/wechat/session', json={'app': 'timing', 'code': 'bad-code'})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {
            'message': 'wechat code2Session failed',
            'errcode': 40029,
        })

    def test_session_requires_configured_secret(self):
        os.environ['WECHAT_MINIPROGRAM_NBA_SECRET'] = ''
        self.app_module = importlib.reload(self.app_module)
        self.client = self.app_module.app.test_client()

        response = self.client.post('/api/nba/wechat/session', json={'code': 'code-one'})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json(), {'message': 'wechat credentials are not configured'})

    def test_generic_session_requires_project_after_code_is_present(self):
        response = self.client.post('/api/wechat/session', json={'code': 'code-one'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'wechat project is required'})

    def test_project_scoped_routes_use_project_credentials_and_identity_scope(self):
        calls = []

        def fake_exchange(appid, secret, code):
            calls.append((appid, secret, code))
            return {
                'openid': 'shared-openid',
                'unionid': '',
            }

        self.patch_code_exchange(fake_exchange)

        nba = self.client.post('/api/nba/wechat/session', json={'code': 'nba-code'})
        timing = self.client.post('/api/timing/wechat/session', json={'code': 'timing-code'})

        self.assertEqual(nba.status_code, 200)
        self.assertEqual(timing.status_code, 200)
        nba_payload = nba.get_json()
        timing_payload = timing.get_json()
        self.assertEqual(calls, [
            ('nba-appid', 'nba-secret', 'nba-code'),
            ('timing-appid', 'timing-secret', 'timing-code'),
        ])
        self.assertEqual(nba_payload['app'], 'nba')
        self.assertEqual(timing_payload['app'], 'timing')
        self.assertNotEqual(nba_payload['userId'], timing_payload['userId'])

        cross_project = self.client.get(
            '/api/timing/plan-config',
            headers={'Authorization': 'Bearer ' + nba_payload['sessionToken']},
        )
        self.assertEqual(cross_project.status_code, 401)
        self.assertEqual(cross_project.get_json(), {'message': 'unauthorized'})

        conn = sqlite3.connect(self.wechat_db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                'SELECT project, wechat_openid FROM wechat_users ORDER BY project'
            ).fetchall()
        finally:
            conn.close()
        self.assertEqual([dict(row) for row in rows], [
            {'project': 'nba', 'wechat_openid': 'shared-openid'},
            {'project': 'timing', 'wechat_openid': 'shared-openid'},
        ])

    def test_wechat_user_schema_migration_preserves_config_and_scopes_openid(self):
        from wechat_backend.service import init_wechat_db

        db_path = os.path.join(self.base_dir, 'legacy-wechat.db')
        conn = sqlite3.connect(db_path)
        try:
            conn.execute('PRAGMA foreign_keys=ON')
            conn.executescript(
                '''
                CREATE TABLE wechat_users (
                    id TEXT PRIMARY KEY,
                    wechat_openid TEXT UNIQUE NOT NULL,
                    wechat_unionid TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_login_at TEXT NOT NULL
                );
                CREATE TABLE user_configs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    app TEXT NOT NULL,
                    config_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES wechat_users(id) ON DELETE CASCADE,
                    UNIQUE (user_id, app)
                );
                INSERT INTO wechat_users (
                    id, wechat_openid, wechat_unionid, created_at, updated_at, last_login_at
                ) VALUES (
                    'wx_legacy', 'shared-openid', NULL,
                    '2026-06-19T00:00:00', '2026-06-19T00:00:00', '2026-06-19T00:00:00'
                );
                INSERT INTO user_configs (
                    id, user_id, app, config_json, created_at, updated_at
                ) VALUES (
                    'ucfg_legacy', 'wx_legacy', 'nba', '{}',
                    '2026-06-19T00:00:00', '2026-06-19T00:00:00'
                );
                '''
            )
            conn.commit()
        finally:
            conn.close()

        init_wechat_db(db_path)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            legacy_user = conn.execute(
                'SELECT id, project, wechat_openid FROM wechat_users WHERE id=?',
                ('wx_legacy',),
            ).fetchone()
            config_count = conn.execute(
                'SELECT COUNT(*) FROM user_configs WHERE user_id=?',
                ('wx_legacy',),
            ).fetchone()[0]
            conn.execute(
                '''
                INSERT INTO wechat_users (
                    id, project, wechat_openid, created_at, updated_at, last_login_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    'wx_timing',
                    'timing',
                    'shared-openid',
                    '2026-06-19T00:00:00',
                    '2026-06-19T00:00:00',
                    '2026-06-19T00:00:00',
                ),
            )
            conn.commit()
        finally:
            conn.close()

        self.assertEqual(dict(legacy_user), {
            'id': 'wx_legacy',
            'project': 'nba',
            'wechat_openid': 'shared-openid',
        })
        self.assertEqual(config_count, 1)

    def test_nba_user_config_requires_session_and_persists_per_wechat_user(self):
        def fake_exchange(appid, secret, code):
            return {
                'openid': 'openid-' + code,
                'unionid': '',
            }

        self.patch_code_exchange(fake_exchange)

        session = self.client.post('/api/nba/wechat/session', json={'code': 'one'})
        self.assertEqual(session.status_code, 200)
        session_payload = session.get_json()
        self.assertEqual(session_payload['app'], 'nba')
        token = session_payload['sessionToken']

        unauthorized = self.client.get('/api/nba/user-config')
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(unauthorized.get_json(), {'message': 'unauthorized'})

        default_config = self.client.get(
            '/api/nba/user-config',
            headers={'Authorization': 'Bearer ' + token},
        )
        self.assertEqual(default_config.status_code, 200)
        self.assertEqual(default_config.get_json()['config'], {
            'associated_home_player_pid': [],
            'current_home_player_pid': None,
            'search_default_player_pid': [],
        })

        updated = self.client.patch(
            '/api/nba/user-config',
            json={
                'config': {
                    'associated_home_player_pid': [' player-a ', '', 'player-b', 'player-a'],
                    'current_home_player_pid': ' player-b ',
                    'search_default_player_pid': ['p1', '', 'p2', 'p1', '  p3  '],
                },
            },
            headers={'Authorization': 'Bearer ' + token},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()['config'], {
            'associated_home_player_pid': ['player-a', 'player-b'],
            'current_home_player_pid': 'player-b',
            'search_default_player_pid': ['p1', 'p2', 'p3'],
        })
        conn = sqlite3.connect(self.wechat_db_path)
        conn.row_factory = sqlite3.Row
        try:
            stored = conn.execute(
                '''
                SELECT config_json
                FROM user_configs
                WHERE user_id=? AND app='nba'
                ''',
                (session_payload['userId'],),
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(json.loads(stored['config_json'])['associated_home_player_pid'], ['player-a', 'player-b'])

        second_session = self.client.post('/api/nba/wechat/session', json={'code': 'two'})
        second_token = second_session.get_json()['sessionToken']
        isolated = self.client.get(
            '/api/nba/user-config',
            headers={'Authorization': 'Bearer ' + second_token},
        )
        self.assertEqual(isolated.get_json()['config'], {
            'associated_home_player_pid': [],
            'current_home_player_pid': None,
            'search_default_player_pid': [],
        })

        invalid = self.client.patch(
            '/api/nba/user-config',
            json={'config': {'unknown': True}},
            headers={'Authorization': 'Bearer ' + token},
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.get_json(), {'message': 'invalid nba user config'})

    def test_nba_user_config_returns_home_cards_metadata_and_version(self):
        def fake_exchange(appid, secret, code):
            return {
                'openid': 'home-cache-openid',
                'unionid': '',
            }

        self.patch_code_exchange(fake_exchange)
        self.insert_nba_player('player-a', '2026-06-20T08:20:00', '球员A', 'Player A')
        self.insert_nba_player('player-b', '2026-06-20T08:30:00', '球员B', 'Player B')

        session = self.client.post('/api/nba/wechat/session', json={'code': 'home-cache'})
        token = session.get_json()['sessionToken']
        headers = {'Authorization': 'Bearer ' + token}

        default_config = self.client.get('/api/nba/user-config', headers=headers)
        self.assertEqual(default_config.status_code, 200)
        default_home_cards = default_config.get_json()['homeCards']
        self.assertEqual(default_home_cards['pids'], [])
        self.assertIsNone(default_home_cards['currentPid'])
        self.assertIsNone(default_home_cards['configUpdatedAt'])
        self.assertIsNone(default_home_cards['playersUpdatedAt'])
        self.assertTrue(default_home_cards['dataVersion'].startswith('home_'))

        updated = self.client.patch(
            '/api/nba/user-config',
            json={'config': {
                'associated_home_player_pid': ['player-a', 'player-b'],
                'current_home_player_pid': 'player-b',
            }},
            headers=headers,
        )
        self.assertEqual(updated.status_code, 200)

        response = self.client.get('/api/nba/user-config', headers=headers)
        payload = response.get_json()
        home_cards = payload['homeCards']
        self.assertEqual(home_cards['pids'], ['player-a', 'player-b'])
        self.assertEqual(home_cards['currentPid'], 'player-b')
        self.assertEqual(home_cards['configUpdatedAt'], payload['updatedAt'])
        self.assertEqual(home_cards['playersUpdatedAt'], '2026-06-20T08:30:00')

        repeat = self.client.get('/api/nba/user-config', headers=headers)
        self.assertEqual(repeat.get_json()['homeCards']['dataVersion'], home_cards['dataVersion'])

        current_changed = self.client.patch(
            '/api/nba/user-config',
            json={'config': {'current_home_player_pid': 'player-a'}},
            headers=headers,
        )
        self.assertNotEqual(
            current_changed.get_json()['homeCards']['dataVersion'],
            home_cards['dataVersion'],
        )

        conn = sqlite3.connect(self.nba_db_path)
        try:
            conn.execute(
                "UPDATE nba_players SET jersey_number='8', updated_at='2026-06-20T09:00:00' WHERE pid='player-a'"
            )
            conn.commit()
        finally:
            conn.close()

        player_changed = self.client.get('/api/nba/user-config', headers=headers).get_json()['homeCards']
        self.assertEqual(player_changed['playersUpdatedAt'], '2026-06-20T09:00:00')
        self.assertNotEqual(player_changed['dataVersion'], current_changed.get_json()['homeCards']['dataVersion'])

    def test_nba_user_config_reads_legacy_home_player_string_as_list(self):
        def fake_exchange(appid, secret, code):
            return {
                'openid': 'legacy-openid',
                'unionid': '',
            }

        self.patch_code_exchange(fake_exchange)

        session = self.client.post('/api/nba/wechat/session', json={'code': 'legacy'})
        self.assertEqual(session.status_code, 200)
        session_payload = session.get_json()
        token = session_payload['sessionToken']

        conn = sqlite3.connect(self.wechat_db_path)
        try:
            conn.execute(
                '''
                INSERT INTO user_configs (id, user_id, app, config_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    'ucfg_legacy_nba',
                    session_payload['userId'],
                    'nba',
                    json.dumps({
                        'associated_home_player_pid': 'old-home-player',
                        'search_default_player_pid': ['p1'],
                    }),
                    '2026-06-19T00:00:00',
                    '2026-06-19T00:00:00',
                ),
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(
            '/api/nba/user-config',
            headers={'Authorization': 'Bearer ' + token},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['config'], {
            'associated_home_player_pid': ['old-home-player'],
            'current_home_player_pid': None,
            'search_default_player_pid': ['p1'],
        })

        updated = self.client.patch(
            '/api/nba/user-config',
            json={'config': {'associated_home_player_pid': ['new-home-player']}},
            headers={'Authorization': 'Bearer ' + token},
        )
        self.assertEqual(updated.status_code, 200)

        conn = sqlite3.connect(self.wechat_db_path)
        try:
            stored = conn.execute(
                'SELECT config_json FROM user_configs WHERE id=?',
                ('ucfg_legacy_nba',),
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(json.loads(stored)['associated_home_player_pid'], ['new-home-player'])

    def test_timing_plan_config_crud_and_version_conflicts(self):
        def fake_exchange(appid, secret, code):
            return {
                'openid': 'timing-openid',
                'unionid': '',
            }

        self.patch_code_exchange(fake_exchange)

        session = self.client.post('/api/timing/wechat/session', json={'code': 'timing'})
        self.assertEqual(session.status_code, 200)
        session_payload = session.get_json()
        self.assertEqual(session_payload['app'], 'timing')
        headers = {'Authorization': 'Bearer ' + session_payload['sessionToken']}

        initial = self.client.get('/api/timing/plan-config', headers=headers)
        self.assertEqual(initial.status_code, 200)
        initial_payload = initial.get_json()
        self.assertEqual(initial_payload['version'], 0)
        self.assertEqual(initial_payload['config']['defaultTaskDurations']['homework'], 1800)
        self.assertEqual(initial_payload['config']['customPlans'], [])

        duration = self.client.patch(
            '/api/timing/plan-config/default-task-duration',
            json={'defaultTaskKey': 'homework', 'durationSeconds': 2400, 'version': 0},
            headers=headers,
        )
        self.assertEqual(duration.status_code, 200)
        duration_payload = duration.get_json()
        self.assertEqual(duration_payload['version'], 1)
        self.assertEqual(duration_payload['config']['defaultTaskDurations']['homework'], 2400)

        stale = self.client.patch(
            '/api/timing/plan-config/default-task-duration',
            json={'defaultTaskKey': 'look_far', 'durationSeconds': 600, 'version': 0},
            headers=headers,
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.get_json(), {'message': 'config version conflict', 'version': 1})

        created = self.client.post(
            '/api/timing/plan-config/custom-plans',
            json={'name': 'Read book', 'durationSeconds': 1800, 'taskType': 'study', 'order': 0, 'version': 1},
            headers=headers,
        )
        self.assertEqual(created.status_code, 200)
        created_payload = created.get_json()
        self.assertEqual(created_payload['version'], 2)
        plan_id = created_payload['plan']['id']
        self.assertEqual(created_payload['plan']['enabled'], True)

        updated = self.client.put(
            '/api/timing/plan-config/custom-plans/' + plan_id,
            json={'name': 'Read more', 'durationSeconds': 2400, 'taskType': 'relax', 'order': 1, 'enabled': False, 'version': 2},
            headers=headers,
        )
        self.assertEqual(updated.status_code, 200)
        updated_payload = updated.get_json()
        self.assertEqual(updated_payload['version'], 3)
        self.assertEqual(updated_payload['plan']['name'], 'Read more')
        self.assertEqual(updated_payload['plan']['enabled'], False)

        deleted = self.client.delete(
            '/api/timing/plan-config/custom-plans/' + plan_id,
            json={'version': 3},
            headers=headers,
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.get_json()['version'], 4)

        final = self.client.get('/api/timing/plan-config', headers=headers)
        self.assertEqual(final.status_code, 200)
        self.assertEqual(final.get_json()['config']['customPlans'], [])


if __name__ == '__main__':
    unittest.main()
