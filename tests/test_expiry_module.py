import importlib
import os
import tempfile
import unittest


class ExpiryModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.base_dir = tempfile.mkdtemp(prefix='expiry-test-')
        self.db_path = os.path.join(self.base_dir, 'data.db')
        os.environ['RECORDED_BASE_DIR'] = self.base_dir
        os.environ['RECORDED_DB_PATH'] = self.db_path

        if 'app' in globals():
            pass
        self.app_module = importlib.import_module('app')
        self.app_module = importlib.reload(self.app_module)
        self.app_module.init_db()

        from expiry_backend.service import ensure_initial_admin

        info = ensure_initial_admin(self.db_path, self.base_dir)
        self.admin_username = info['username']
        self.admin_password = info['password']
        self.client = self.app_module.app.test_client()

    def login(self, username, password):
        response = self.client.post('/api/expiry/auth/login', json={
            'username': username,
            'password': password,
        })
        self.assertEqual(response.status_code, 200)
        return response.get_json()['token']

    def auth_headers(self, token):
        return {'Authorization': 'Bearer ' + token}

    def test_admin_can_create_and_manage_resources(self):
        token = self.login(self.admin_username, self.admin_password)
        response = self.client.post('/api/expiry/resources', headers=self.auth_headers(token), json={
            'name': 'GPT Plus',
            'provider': 'OpenAI',
            'category': 'AI',
            'resource_type': 'subscription',
            'billing_cycle': 'monthly',
            'amount': 20,
            'start_date': '2026-04-01',
            'next_due_date': '2026-04-30',
            'auto_renew': True,
            'notify_offsets': '30,7,1',
        })
        self.assertEqual(response.status_code, 201)
        resource_id = response.get_json()['id']

        dashboard = self.client.get('/api/expiry/dashboard', headers=self.auth_headers(token))
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(len(dashboard.get_json()['resources']), 1)

        stop_resp = self.client.post(
            '/api/expiry/resources/{}/stop'.format(resource_id),
            headers=self.auth_headers(token),
        )
        self.assertEqual(stop_resp.status_code, 200)

        detail = self.client.get(
            '/api/expiry/resources/{}'.format(resource_id),
            headers=self.auth_headers(token),
        )
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()['manual_status'], 'stopped')

    def test_user_isolation_and_admin_guard(self):
        admin_token = self.login(self.admin_username, self.admin_password)
        created = self.client.post('/api/expiry/admin/users', headers=self.auth_headers(admin_token), json={
            'username': 'alice',
            'password': 'alice123',
            'email': 'alice@example.com',
            'role': 'user',
        })
        self.assertEqual(created.status_code, 201)

        user_token = self.login('alice', 'alice123')

        resource = self.client.post('/api/expiry/resources', headers=self.auth_headers(user_token), json={
            'name': 'YouTube Premium',
            'provider': 'Google',
            'category': '视频',
            'resource_type': 'subscription',
            'billing_cycle': 'monthly',
            'amount': 22,
            'next_due_date': '2026-05-01',
            'auto_renew': False,
        })
        self.assertEqual(resource.status_code, 201)
        resource_id = resource.get_json()['id']

        admin_view = self.client.get(
            '/api/expiry/resources/{}'.format(resource_id),
            headers=self.auth_headers(admin_token),
        )
        self.assertEqual(admin_view.status_code, 404)

        forbidden = self.client.get('/api/expiry/admin/users', headers=self.auth_headers(user_token))
        self.assertEqual(forbidden.status_code, 403)

    def test_email_settings_support_oauth_mode(self):
        token = self.login(self.admin_username, self.admin_password)
        save_resp = self.client.put('/api/expiry/settings/email', headers=self.auth_headers(token), json={
            'auth_mode': 'microsoft_oauth2',
            'smtp_host': 'smtp-mail.outlook.com',
            'smtp_port': 587,
            'smtp_username': 'alice@example.com',
            'smtp_security': 'starttls',
            'from_email': 'alice@example.com',
            'from_name': 'Expiry Radar',
            'oauth_tenant_id': 'common',
            'oauth_client_id': 'client-id-demo',
            'oauth_client_secret': 'client-secret-demo',
            'oauth_refresh_token': 'refresh-token-demo',
            'enabled': True,
        })
        self.assertEqual(save_resp.status_code, 200)

        email_settings = self.client.get('/api/expiry/settings/email', headers=self.auth_headers(token))
        self.assertEqual(email_settings.status_code, 200)
        payload = email_settings.get_json()
        self.assertEqual(payload['auth_mode'], 'microsoft_oauth2')
        self.assertEqual(payload['oauth_tenant_id'], 'common')
        self.assertEqual(payload['oauth_client_id'], 'client-id-demo')
        self.assertTrue(payload['oauth_client_secret_configured'])
        self.assertTrue(payload['oauth_refresh_token_configured'])


if __name__ == '__main__':
    unittest.main()
