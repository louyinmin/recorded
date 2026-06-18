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


if __name__ == '__main__':
    unittest.main()
