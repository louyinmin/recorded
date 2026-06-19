import importlib
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
        os.environ['WECHAT_MINIPROGRAM_APPID'] = 'test-appid'
        os.environ['WECHAT_MINIPROGRAM_SECRET'] = 'test-secret'

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

        first = self.client.post('/api/wechat/session', json={'code': 'code-one'})
        second = self.client.post('/api/wechat/session', json={'code': 'code-two'})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        first_payload = first.get_json()
        second_payload = second.get_json()
        self.assertEqual(first_payload['userId'], second_payload['userId'])
        self.assertEqual(first_payload['openid'], 'openid-123')
        self.assertEqual(first_payload['unionid'], 'unionid-456')
        self.assertIn('sessionToken', first_payload)
        self.assertIn('expiresAt', first_payload)
        self.assertNotIn('session_key', first_payload)
        self.assertEqual(calls[0], ('test-appid', 'test-secret', 'code-one'))

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

        response = self.client.post('/api/wechat/session', json={'code': 'bad-code'})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {
            'message': 'wechat code2Session failed',
            'errcode': 40029,
        })

    def test_session_requires_configured_secret(self):
        os.environ['WECHAT_MINIPROGRAM_SECRET'] = ''
        self.app_module = importlib.reload(self.app_module)
        self.client = self.app_module.app.test_client()

        response = self.client.post('/api/wechat/session', json={'code': 'code-one'})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json(), {'message': 'wechat credentials are not configured'})

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
            'associated_home_player_pid': None,
            'search_default_player_pid': [],
        })

        updated = self.client.patch(
            '/api/nba/user-config',
            json={
                'config': {
                    'associated_home_player_pid': ' player-a ',
                    'search_default_player_pid': ['p1', '', 'p2', 'p1', '  p3  '],
                },
            },
            headers={'Authorization': 'Bearer ' + token},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()['config'], {
            'associated_home_player_pid': 'player-a',
            'search_default_player_pid': ['p1', 'p2', 'p3'],
        })

        second_session = self.client.post('/api/nba/wechat/session', json={'code': 'two'})
        second_token = second_session.get_json()['sessionToken']
        isolated = self.client.get(
            '/api/nba/user-config',
            headers={'Authorization': 'Bearer ' + second_token},
        )
        self.assertEqual(isolated.get_json()['config'], {
            'associated_home_player_pid': None,
            'search_default_player_pid': [],
        })

        invalid = self.client.patch(
            '/api/nba/user-config',
            json={'config': {'unknown': True}},
            headers={'Authorization': 'Bearer ' + token},
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.get_json(), {'message': 'invalid nba user config'})

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
