import importlib
import io
import os
import sqlite3
import tempfile
import unittest


class LifeBackendTestCase(unittest.TestCase):
    def setUp(self):
        self.base_dir = tempfile.mkdtemp(prefix='life-backend-test-')
        self.db_path = os.path.join(self.base_dir, 'data.db')
        self.life_db_path = os.path.join(self.base_dir, 'life.db')
        os.environ['RECORDED_BASE_DIR'] = self.base_dir
        os.environ['RECORDED_DB_PATH'] = self.db_path
        os.environ['LIFE_DB_PATH'] = self.life_db_path

        self.app_module = importlib.import_module('app')
        self.app_module = importlib.reload(self.app_module)
        self.app_module.init_db()
        self.client = self.app_module.app.test_client()

    def login(self, email='admin', password='OOoo0000'):
        resp = self.client.post('/api/life/auth/login', json={
            'email': email,
            'password': password,
        })
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        return payload['token']

    def headers(self, token):
        return {'Authorization': 'Bearer ' + token}

    def test_seed_accounts_login_by_account_name(self):
        admin_login = self.client.post('/api/life/auth/login', json={
            'account': 'admin',
            'password': 'OOoo0000',
        })
        self.assertEqual(admin_login.status_code, 200)
        self.assertEqual(admin_login.get_json()['user']['role'], 'admin')

        user_login = self.client.post('/api/life/auth/login', json={
            'account': 'xyc',
            'password': '654321',
        })
        self.assertEqual(user_login.status_code, 200)
        user = user_login.get_json()['user']
        self.assertEqual(user['role'], 'user')
        self.assertEqual(user['username'], 'xyc')

    def test_auth_and_crud_isolation(self):
        admin_token = self.login()
        create_user = self.client.post('/api/life/admin/users', headers=self.headers(admin_token), json={
            'name': 'Alice',
            'email': 'alice@example.com',
            'password': 'alice123',
            'role': 'user',
            'avatar': 'Q2',
        })
        self.assertEqual(create_user.status_code, 201)

        alice_login = self.client.post('/api/life/auth/login', json={
            'email': 'alice@example.com',
            'password': 'alice123',
        })
        self.assertEqual(alice_login.status_code, 200)
        alice_token = alice_login.get_json()['token']

        created = self.client.post('/api/life/decisions', headers=self.headers(admin_token), json={
            'id': 'd100',
            'title': '是否接受新 Offer',
            'status': '待复盘',
            'date': '2026-05-01'
        })
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.get_json()['item']['reviewDate'], '2026-11-01')

        admin_list = self.client.get('/api/life/decisions', headers=self.headers(admin_token))
        self.assertEqual(admin_list.status_code, 200)
        self.assertEqual(len(admin_list.get_json()['items']), 1)

        alice_list = self.client.get('/api/life/decisions', headers=self.headers(alice_token))
        self.assertEqual(alice_list.status_code, 200)
        self.assertEqual(alice_list.get_json()['items'], [])

    def test_mock_mode_and_snapshot(self):
        token = self.login()
        resp = self.client.put('/api/life/snapshot/moments', headers=self.headers(token), json={
            'mode': 'mock',
            'items': [{'id': 'm100', 'title': 'mock'}]
        })
        self.assertEqual(resp.status_code, 200)

        mock_list = self.client.get('/api/life/moments?mode=mock', headers=self.headers(token))
        self.assertEqual(mock_list.status_code, 200)
        self.assertEqual(len(mock_list.get_json()['items']), 1)

        real_list = self.client.get('/api/life/moments', headers=self.headers(token))
        self.assertEqual(real_list.status_code, 200)
        self.assertEqual(real_list.get_json()['items'], [])

    def test_mock_bootstrap_seeds_server_side_fixture(self):
        token = self.login()
        bootstrap = self.client.get('/api/life/bootstrap?mock=1', headers=self.headers(token))
        self.assertEqual(bootstrap.status_code, 200)
        payload = bootstrap.get_json()
        self.assertEqual(payload['mode'], 'mock')
        self.assertGreaterEqual(len(payload['data']['moments']), 1)
        self.assertEqual(payload['data']['moments'][0]['dataScope'], 'server_mock_fixture')
        self.assertTrue(payload['data']['moments'][0]['isTestData'])
        self.assertGreaterEqual(len(payload['data']['resources']), 1)
        decision_titles = [item['title'] for item in payload['data']['decisions']]
        self.assertIn('是否换工作？', decision_titles)
        decision_item = [item for item in payload['data']['decisions'] if item['title'] == '是否换工作？'][0]
        self.assertEqual(decision_item['status'], '待复盘')
        self.assertEqual(decision_item['category'], '职业发展')
        axis_items = payload['data']['axis']
        self.assertGreaterEqual(len(axis_items), 16)
        axis_types = set([item['type'] for item in axis_items])
        self.assertEqual(axis_types, set(['旅行', '项目', '健康', '关系']))
        axis_years = set([item['year'] for item in axis_items])
        self.assertEqual(axis_years, set(['2026', '2025', '2024', '2023']))
        mood_items = payload['data']['moods']
        self.assertEqual(len(mood_items), 14)
        mood_dates = set([item['date'] for item in mood_items])
        self.assertEqual(len(mood_dates), 14)
        mood_feelings = set([item['feeling'] for item in mood_items])
        self.assertGreaterEqual(len(mood_feelings), 8)
        mood_weather = set([item['weather'] for item in mood_items])
        self.assertGreaterEqual(len(mood_weather), 5)
        wish_items = payload['data']['wishes']
        wish_statuses = [item.get('status') for item in wish_items]
        self.assertIn('可以决定', wish_statuses)
        self.assertIn('已放弃', wish_statuses)
        self.assertIn('已实现', wish_statuses)
        watch_items = payload['data']['watch']
        watch_years = set([item.get('year') for item in watch_items])
        self.assertIn(2024, watch_years)
        self.assertIn(2025, watch_years)
        self.assertIn(2026, watch_years)
        relationship_items = payload['data']['relationships']
        self.assertGreaterEqual(len(relationship_items), 7)
        relationship_groups = set([item.get('group') for item in relationship_items])
        self.assertIn('家人', relationship_groups)
        self.assertIn('朋友', relationship_groups)
        self.assertIn('同事', relationship_groups)

        real_bootstrap = self.client.get('/api/life/bootstrap', headers=self.headers(token))
        self.assertEqual(real_bootstrap.status_code, 200)
        self.assertEqual(real_bootstrap.get_json()['data']['moments'], [])

    def test_mock_bootstrap_backfills_fixture_when_fixture_rows_exist(self):
        token = self.login()
        seeded = self.client.get('/api/life/bootstrap?mock=1', headers=self.headers(token))
        self.assertEqual(seeded.status_code, 200)
        self.assertEqual(len(seeded.get_json()['data']['moods']), 14)

        conn = sqlite3.connect(self.life_db_path)
        try:
            admin_id = conn.execute("SELECT id FROM life_users WHERE username='admin' LIMIT 1").fetchone()[0]
            conn.execute(
                "DELETE FROM life_mood_records WHERE user_id=? AND is_mock=1 AND id='mock-mood-14'",
                (admin_id,),
            )
            conn.commit()
        finally:
            conn.close()

        refreshed = self.client.get('/api/life/bootstrap?mock=1', headers=self.headers(token))
        self.assertEqual(refreshed.status_code, 200)
        mood_ids = [item['id'] for item in refreshed.get_json()['data']['moods']]
        self.assertIn('mock-mood-14', mood_ids)
        self.assertEqual(len(mood_ids), 14)

    def test_sync_bridge_rows_do_not_block_mock_fixture_backfill(self):
        token = self.login()
        bridge = self.client.put('/api/life/storage/life_relationships_v1', headers=self.headers(token), json={
            'mode': 'mock',
            'value': {'added': [{'id': 'legacy-r1', 'name': 'Legacy relation'}], 'edits': {}, 'deleted': []}
        })
        self.assertEqual(bridge.status_code, 200)

        refreshed = self.client.get('/api/life/bootstrap?mock=1', headers=self.headers(token))
        self.assertEqual(refreshed.status_code, 200)
        relationships = refreshed.get_json()['data']['relationships']
        names = [item.get('name') for item in relationships]
        self.assertIn('Legacy relation', names)
        self.assertIn('妈妈', names)
        self.assertIn('陈昊', names)
        scopes = set([item.get('dataScope') for item in relationships])
        self.assertIn('sync_bridge_test', scopes)
        self.assertIn('server_mock_fixture', scopes)

    def test_sync_bridge_storage_migrates_to_test_module_partition(self):
        token = self.login()
        seeded = self.client.get('/api/life/bootstrap?mock=1', headers=self.headers(token))
        self.assertEqual(seeded.status_code, 200)
        self.assertGreaterEqual(len(seeded.get_json()['data']['moments']), 1)

        bridge = self.client.put('/api/life/storage/life_moments_v1', headers=self.headers(token), json={
            'mode': 'mock',
            'value': [{'id': 'legacy-1', 'title': 'Legacy bridge item'}]
        })
        self.assertEqual(bridge.status_code, 200)

        production = self.client.get('/api/life/moments', headers=self.headers(token))
        self.assertEqual(production.status_code, 200)
        self.assertEqual(production.get_json()['items'], [])

        mock_module = self.client.get('/api/life/moments?mock=1', headers=self.headers(token))
        self.assertEqual(mock_module.status_code, 200)
        items = mock_module.get_json()['items']
        legacy_items = [item for item in items if item.get('title') == 'Legacy bridge item']
        self.assertEqual(len(legacy_items), 1)
        self.assertEqual(legacy_items[0]['originalId'], 'legacy-1')
        self.assertTrue(legacy_items[0]['isTestData'])
        self.assertEqual(legacy_items[0]['dataTag'], 'test')
        self.assertEqual(legacy_items[0]['dataScope'], 'sync_bridge_test')
        self.assertTrue([item for item in items if item.get('dataScope') == 'server_mock_fixture'])

    def test_bootstrap_uses_module_data_for_direct_mode(self):
        token = self.login()
        created = self.client.post('/api/life/moments', headers=self.headers(token), json={
            'id': 'prod-1',
            'title': 'Production module item'
        })
        self.assertEqual(created.status_code, 201)
        bridge = self.client.put('/api/life/storage/life_moments_v1', headers=self.headers(token), json={
            'value': [{'id': 'legacy-1', 'title': 'Legacy bridge item'}]
        })
        self.assertEqual(bridge.status_code, 200)

        bootstrap = self.client.get('/api/life/bootstrap', headers=self.headers(token))
        self.assertEqual(bootstrap.status_code, 200)
        moments = bootstrap.get_json()['data']['moments']
        self.assertEqual(len(moments), 1)
        self.assertEqual(moments[0]['id'], 'prod-1')
        self.assertEqual(moments[0]['title'], 'Production module item')

    def test_watch_module_api_is_available(self):
        token = self.login()
        created = self.client.post('/api/life/watch', headers=self.headers(token), json={
            'id': 'watch-1',
            'title': 'Module-backed movie',
            'date': '2026-05-25'
        })
        self.assertEqual(created.status_code, 201)

        listed = self.client.get('/api/life/watch', headers=self.headers(token))
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.get_json()['items'][0]['id'], 'watch-1')

    def test_sync_bridge_migrates_all_navigation_modules(self):
        token = self.login()
        module_payloads = [
            ('life_axis_milestones_v1', 'axis', {'added': [{'id': 'a-local-1', 'title': 'axis-migrated'}], 'edits': {}, 'deleted': []}),
            ('life_decisions_v1', 'decisions', [{'id': 'd-local-1', 'title': 'decision-migrated', 'date': '2026-05-25'}]),
            ('life_mood_records_v1', 'moods', {'added': [{'id': 'mood-1', 'date': '2026-05-25', 'year': 2026, 'month': 4, 'day': 25, 'score': 80}], 'edits': {}, 'deleted': []}),
            ('life_relationships_v1', 'relationships', {'added': [{'id': 'r-local-1', 'name': 'relation-migrated'}], 'edits': {}, 'deleted': []}),
            ('life_wishes_v1', 'wishes', {'added': [{'id': 'w-local-1', 'name': 'wish-migrated'}], 'edits': {}, 'deleted': []}),
            ('life_watch_v1', 'watch', {'added': [{'id': 'watch-local-1', 'title': 'watch-migrated', 'date': '2026-05-25'}], 'edits': {}, 'deleted': []}),
        ]
        for storage_key, _, value in module_payloads:
            resp = self.client.put('/api/life/storage/{}'.format(storage_key), headers=self.headers(token), json={
                'mode': 'mock',
                'value': value
            })
            self.assertEqual(resp.status_code, 200)

        for _, module_name, _ in module_payloads:
            listed = self.client.get('/api/life/{}?mock=1'.format(module_name), headers=self.headers(token))
            self.assertEqual(listed.status_code, 200)
            self.assertGreaterEqual(len(listed.get_json()['items']), 1)
            self.assertEqual(listed.get_json()['items'][0]['dataScope'], 'sync_bridge_test')

    def test_sync_bridge_prefers_mock_storage_and_avoids_duplicates(self):
        token = self.login()
        real_resp = self.client.put('/api/life/storage/life_watch_v1', headers=self.headers(token), json={
            'mode': 'mock',
            'value': {'added': [{'id': 'watch-real-1', 'title': 'same-title', 'date': '2026-05-25'}], 'edits': {}, 'deleted': []}
        })
        self.assertEqual(real_resp.status_code, 200)
        mock_resp = self.client.put('/api/life/storage/life_mock_watch_v1', headers=self.headers(token), json={
            'mode': 'mock',
            'value': {'added': [{'id': 'watch-mock-1', 'title': 'same-title', 'date': '2026-05-25'}], 'edits': {}, 'deleted': []}
        })
        self.assertEqual(mock_resp.status_code, 200)

        listed = self.client.get('/api/life/watch?mock=1', headers=self.headers(token))
        self.assertEqual(listed.status_code, 200)
        items = listed.get_json()['items']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'same-title')
        self.assertEqual(items[0]['dataScope'], 'sync_bridge_test')
        self.assertEqual(items[0]['_syncBridge']['storageKey'], 'life_mock_watch_v1')

    def test_storage_and_upload(self):
        token = self.login()
        put_storage = self.client.put('/api/life/storage/life_moments_v1', headers=self.headers(token), json={
            'value': [{'id': 'm1', 'title': 'from-storage'}]
        })
        self.assertEqual(put_storage.status_code, 200)

        bootstrap = self.client.get('/api/life/bootstrap', headers=self.headers(token))
        self.assertEqual(bootstrap.status_code, 200)
        storage = bootstrap.get_json()['storage']
        self.assertIn('life_moments_v1', storage)
        self.assertEqual(storage['life_moments_v1'][0]['title'], 'from-storage')

        upload = self.client.post(
            '/api/life/uploads',
            headers=self.headers(token),
            data={'file': (io.BytesIO(b'\x89PNG\r\n\x1a\nxxxx'), 'demo.png')},
            content_type='multipart/form-data'
        )
        self.assertEqual(upload.status_code, 200)
        url = upload.get_json()['url']
        self.assertTrue(url.startswith('/assets/uploads/life/'))

        no_ext_upload = self.client.post(
            '/api/life/uploads',
            headers=self.headers(token),
            data={'file': (io.BytesIO(b'\x89PNG\r\n\x1a\nxxxx'), 'demo')},
            content_type='multipart/form-data'
        )
        self.assertEqual(no_ext_upload.status_code, 200)
        self.assertTrue(no_ext_upload.get_json()['url'].endswith('.png'))

        custom_ext_upload = self.client.post(
            '/api/life/uploads',
            headers=self.headers(token),
            data={'file': (io.BytesIO(b'\x89PNG\r\n\x1a\nxxxx'), 'demo.notimageext', 'image/png')},
            content_type='multipart/form-data'
        )
        self.assertEqual(custom_ext_upload.status_code, 200)
        self.assertTrue(custom_ext_upload.get_json()['url'].endswith('.notimageext'))

    def test_admin_can_reset_normal_user_password(self):
        admin_token = self.login()
        create_user = self.client.post('/api/life/admin/users', headers=self.headers(admin_token), json={
            'name': 'Bob',
            'email': 'bob@example.com',
            'password': 'bob12345',
            'role': 'user',
            'avatar': 'Q2',
        })
        self.assertEqual(create_user.status_code, 201)
        bob_id = create_user.get_json()['user']['id']

        reset_resp = self.client.post(
            '/api/life/admin/users/{}/reset-password'.format(bob_id),
            headers=self.headers(admin_token),
            json={'password': 'bob99999'}
        )
        self.assertEqual(reset_resp.status_code, 200)

        old_login = self.client.post('/api/life/auth/login', json={
            'email': 'bob@example.com',
            'password': 'bob12345',
        })
        self.assertEqual(old_login.status_code, 401)

        new_login = self.client.post('/api/life/auth/login', json={
            'email': 'bob@example.com',
            'password': 'bob99999',
        })
        self.assertEqual(new_login.status_code, 200)

    def test_admin_can_deactivate_and_activate_normal_user(self):
        admin_token = self.login()
        create_user = self.client.post('/api/life/admin/users', headers=self.headers(admin_token), json={
            'name': 'Cara',
            'email': 'cara@example.com',
            'password': 'cara1234',
            'role': 'user',
            'avatar': 'Q2',
        })
        self.assertEqual(create_user.status_code, 201)
        cara = create_user.get_json()['user']

        cara_login = self.client.post('/api/life/auth/login', json={
            'email': 'cara@example.com',
            'password': 'cara1234',
        })
        self.assertEqual(cara_login.status_code, 200)
        cara_token = cara_login.get_json()['token']

        deactivate = self.client.patch(
            '/api/life/admin/users/{}'.format(cara['id']),
            headers=self.headers(admin_token),
            json={'status': 'inactive'}
        )
        self.assertEqual(deactivate.status_code, 200)
        self.assertEqual(deactivate.get_json()['user']['status'], 'inactive')

        inactive_login = self.client.post('/api/life/auth/login', json={
            'email': 'cara@example.com',
            'password': 'cara1234',
        })
        self.assertEqual(inactive_login.status_code, 401)

        old_session = self.client.get('/api/life/auth/me', headers=self.headers(cara_token))
        self.assertEqual(old_session.status_code, 401)

        activate = self.client.patch(
            '/api/life/admin/users/{}'.format(cara['id']),
            headers=self.headers(admin_token),
            json={'status': 'active'}
        )
        self.assertEqual(activate.status_code, 200)
        self.assertEqual(activate.get_json()['user']['status'], 'active')

        active_login = self.client.post('/api/life/auth/login', json={
            'email': 'cara@example.com',
            'password': 'cara1234',
        })
        self.assertEqual(active_login.status_code, 200)

        admin_self = self.client.get('/api/life/auth/me', headers=self.headers(admin_token)).get_json()
        self_blocked = self.client.patch(
            '/api/life/admin/users/{}'.format(admin_self['id']),
            headers=self.headers(admin_token),
            json={'status': 'inactive'}
        )
        self.assertEqual(self_blocked.status_code, 400)

    def test_seed_normal_user_deactivation_survives_bootstrap(self):
        admin_token = self.login()
        users = self.client.get('/api/life/admin/users', headers=self.headers(admin_token))
        self.assertEqual(users.status_code, 200)
        xyc = [item for item in users.get_json()['items'] if item['username'] == 'xyc'][0]

        deactivate = self.client.patch(
            '/api/life/admin/users/{}'.format(xyc['id']),
            headers=self.headers(admin_token),
            json={'status': 'inactive'}
        )
        self.assertEqual(deactivate.status_code, 200)

        from life_backend.service import init_life_db
        init_life_db(self.life_db_path)

        inactive_login = self.client.post('/api/life/auth/login', json={
            'account': 'xyc',
            'password': '654321',
        })
        self.assertEqual(inactive_login.status_code, 401)

        refreshed_users = self.client.get('/api/life/admin/users', headers=self.headers(admin_token))
        self.assertEqual(refreshed_users.status_code, 200)
        refreshed_xyc = [item for item in refreshed_users.get_json()['items'] if item['username'] == 'xyc'][0]
        self.assertEqual(refreshed_xyc['status'], 'inactive')


if __name__ == '__main__':
    unittest.main()
