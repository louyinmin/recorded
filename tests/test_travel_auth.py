import importlib
import os
import tempfile
import unittest


class TravelAuthIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.base_dir = tempfile.mkdtemp(prefix='travel-auth-test-')
        self.db_path = os.path.join(self.base_dir, 'data.db')
        os.environ['RECORDED_BASE_DIR'] = self.base_dir
        os.environ['RECORDED_DB_PATH'] = self.db_path

        self.app_module = importlib.import_module('app')
        self.app_module = importlib.reload(self.app_module)
        self.app_module.init_db()

        from expiry_backend.service import ensure_initial_admin

        info = ensure_initial_admin(self.db_path, self.base_dir)
        self.admin_username = info['username']
        self.admin_password = info['password']
        self.client = self.app_module.app.test_client()

    def travel_login(self, username, password):
        response = self.client.post('/api/login', json={
            'username': username,
            'password': password,
        })
        self.assertEqual(response.status_code, 200)
        return response.get_json()['token']

    def expiry_login(self, username, password):
        response = self.client.post('/api/expiry/auth/login', json={
            'username': username,
            'password': password,
        })
        self.assertEqual(response.status_code, 200)
        return response.get_json()['token']

    def auth_headers(self, token):
        return {'Authorization': 'Bearer ' + token}

    def create_expiry_user(self, admin_token, username, password):
        response = self.client.post('/api/expiry/admin/users', headers=self.auth_headers(admin_token), json={
            'username': username,
            'password': password,
            'email': '{}@example.com'.format(username),
            'role': 'user',
        })
        self.assertEqual(response.status_code, 201)

    def test_travel_login_uses_expiry_accounts(self):
        token = self.travel_login(self.admin_username, self.admin_password)
        response = self.client.get('/api/categories', headers=self.auth_headers(token))
        self.assertEqual(response.status_code, 200)
        names = [item['name'] for item in response.get_json()]
        self.assertIn('住宿', names)

    def test_travel_data_isolated_per_user(self):
        admin_token = self.expiry_login(self.admin_username, self.admin_password)
        self.create_expiry_user(admin_token, 'alice', 'alice123')

        lou_token = self.travel_login(self.admin_username, self.admin_password)
        alice_token = self.travel_login('alice', 'alice123')

        created = self.client.post('/api/trips', headers=self.auth_headers(lou_token), json={
            'name': '东京周末',
            'startDate': '2026-04-01',
            'endDate': '2026-04-03',
            'note': '仅 lou 可见',
        })
        self.assertEqual(created.status_code, 201)
        trip_id = created.get_json()['id']

        record = self.client.post('/api/trips/{}/records'.format(trip_id), headers=self.auth_headers(lou_token), json={
            'category': '住宿',
            'amount': 499,
            'payer': 'lou',
            'date': '2026-04-01',
        })
        self.assertEqual(record.status_code, 201)

        alice_trips = self.client.get('/api/trips', headers=self.auth_headers(alice_token))
        self.assertEqual(alice_trips.status_code, 200)
        self.assertEqual(alice_trips.get_json(), [])

        alice_trip_view = self.client.get('/api/trips/{}'.format(trip_id), headers=self.auth_headers(alice_token))
        self.assertEqual(alice_trip_view.status_code, 404)

        lou_payers = self.client.get('/api/payers', headers=self.auth_headers(lou_token)).get_json()
        alice_payers = self.client.get('/api/payers', headers=self.auth_headers(alice_token)).get_json()
        self.assertTrue(any(item['name'] == 'lou' for item in lou_payers))
        self.assertFalse(any(item['name'] == 'lou' for item in alice_payers))

    def test_travel_password_change_is_disabled(self):
        token = self.travel_login(self.admin_username, self.admin_password)
        response = self.client.post('/api/password', headers=self.auth_headers(token), json={
            'oldPassword': self.admin_password,
            'newPassword': 'newpass123',
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn('续费雷达设置页', response.get_json()['error'])

        expiry_login = self.client.post('/api/expiry/auth/login', json={
            'username': self.admin_username,
            'password': self.admin_password,
        })
        self.assertEqual(expiry_login.status_code, 200)


if __name__ == '__main__':
    unittest.main()
