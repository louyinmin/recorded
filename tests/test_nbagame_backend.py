import hashlib
import importlib
import os
import shutil
import sqlite3
import tempfile
import threading
import unittest
import uuid
from datetime import datetime
from pathlib import Path
from unittest import mock

from nbagame_backend.service import ASSET_SPECS


PNG_1X1 = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
    b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
)
JPEG_1X1 = b'\xff\xd8\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xd9'


class NbaGameBackendTestCase(unittest.TestCase):
    ENV_NAMES = (
        'RECORDED_BASE_DIR',
        'RECORDED_DB_PATH',
        'LIFE_DB_PATH',
        'NBA_DB_PATH',
        'WECHAT_DB_PATH',
        'NBAGAME_DB_PATH',
        'NBAGAME_WECHAT_APPID',
        'NBAGAME_WECHAT_SECRET',
        'NBAGAME_TOKEN_SECRET',
        'NBAGAME_ASSETS_DIR',
        'NBAGAME_PUBLISHED_ASSETS_DIR',
        'NBAGAME_PUBLIC_BASE_URL',
        'NBAGAME_ASSET_MANIFEST_VERSION',
        'NBAGAME_MAX_REQUEST_BYTES',
        'NBAGAME_LOGIN_RATE_LIMIT',
        'NBAGAME_LOGIN_RATE_WINDOW_SECONDS',
    )

    def setUp(self):
        self.original_env = {name: os.environ.get(name) for name in self.ENV_NAMES}
        self.base_dir = tempfile.mkdtemp(prefix='nbagame-backend-test-')
        self.assets_dir = os.path.join(self.base_dir, 'assets')
        self.published_assets_dir = os.path.join(self.base_dir, 'published-assets')
        self.write_test_assets(self.assets_dir)
        os.environ['RECORDED_BASE_DIR'] = self.base_dir
        os.environ['RECORDED_DB_PATH'] = os.path.join(self.base_dir, 'data.db')
        os.environ['LIFE_DB_PATH'] = os.path.join(self.base_dir, 'life.db')
        os.environ['NBA_DB_PATH'] = os.path.join(self.base_dir, 'nba.db')
        os.environ['WECHAT_DB_PATH'] = os.path.join(self.base_dir, 'wechat.db')
        os.environ['NBAGAME_DB_PATH'] = os.path.join(self.base_dir, 'nbagame.db')
        os.environ['NBAGAME_WECHAT_APPID'] = 'court-deck-appid'
        os.environ['NBAGAME_WECHAT_SECRET'] = 'court-deck-secret'
        os.environ['NBAGAME_TOKEN_SECRET'] = 'court-deck-token-secret'
        os.environ['NBAGAME_ASSETS_DIR'] = self.assets_dir
        os.environ['NBAGAME_PUBLISHED_ASSETS_DIR'] = self.published_assets_dir
        os.environ['NBAGAME_PUBLIC_BASE_URL'] = 'https://cdn.example.test'
        os.environ['NBAGAME_ASSET_MANIFEST_VERSION'] = 'legacy-manual-version'
        os.environ['NBAGAME_MAX_REQUEST_BYTES'] = str(2 * 1024 * 1024)
        os.environ['NBAGAME_LOGIN_RATE_LIMIT'] = '1000'
        os.environ['NBAGAME_LOGIN_RATE_WINDOW_SECONDS'] = '60'
        self.app_module = importlib.reload(importlib.import_module('app'))
        self.client = self.app_module.app.test_client()

    def tearDown(self):
        for name, value in self.original_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        shutil.rmtree(self.base_dir)

    @staticmethod
    def write_test_assets(root):
        for specs in ASSET_SPECS.values():
            for _, relative_path in specs:
                path = Path(root, relative_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(PNG_1X1 if path.suffix == '.png' else JPEG_1X1)

    def reload_app(self):
        self.app_module = importlib.reload(self.app_module)
        self.client = self.app_module.app.test_client()

    def login(self, openid='court-deck-openid'):
        import nbagame_backend.routes as routes
        original = routes.exchange_wechat_code
        routes.exchange_wechat_code = lambda appid, secret, code: {'openid': openid, 'session_key': 'do-not-store'}
        self.addCleanup(lambda: setattr(routes, 'exchange_wechat_code', original))
        response = self.client.post('/nbagame/v1/auth/wechat/login', headers={'X-App-Id': 'court-deck-prod'}, json={'code': 'one-time-code'})
        self.assertEqual(response.status_code, 200)
        return response.get_json()['data']

    @staticmethod
    def career_payload():
        return {
            'schemaVersion': 1,
            'clientRevision': 0,
            'clientUpdatedAt': '2026-07-22T08:00:00Z',
            'reason': 'regular_game_completed',
            'snapshot': {
                'phase': 'season', 'position': 'PG', 'careerTeam': 'LAL',
                'attrs': {'three': 88, 'mid': 81, 'pass': 90, 'rebound': 70, 'athletic': 84, 'clutch': 86},
                'progression': {'seasonNumber': 1},
                'season': {'seasonNumber': 1, 'wins': 12, 'losses': 6, 'isChampion': False, 'playoffResult': None},
            },
        }

    def auth_headers(self, login_data, **extra):
        if 'Idempotency-Key' in extra:
            raw_key = str(extra['Idempotency-Key'])
            try:
                extra['Idempotency-Key'] = str(uuid.UUID(raw_key))
            except ValueError:
                extra['Idempotency-Key'] = str(uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    'https://example.test/idempotency/' + raw_key,
                ))
        return {'Authorization': 'Bearer ' + login_data['accessToken'], **extra}

    def write_career(self, login_data, *, key, expected_revision=0, client_revision=0, season_number=1, team='LAL'):
        body = self.career_payload()
        body['clientRevision'] = client_revision
        body['snapshot']['careerTeam'] = team
        body['snapshot']['progression']['seasonNumber'] = season_number
        body['snapshot']['season']['seasonNumber'] = season_number
        return self.client.put(
            '/nbagame/v1/career',
            headers=self.auth_headers(login_data, **{
                'If-Match': '"career-{}"'.format(expected_revision),
                'Idempotency-Key': key,
            }),
            json=body,
        )

    def create_season_start(self, login_data, *, key, event_id, team='LAL', season_number=1, occurred_at=None):
        event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, 'https://example.test/events/' + event_id))
        body = {'eventId': event_id, 'team': team, 'seasonNumber': season_number}
        if occurred_at:
            body['occurredAt'] = occurred_at
        return self.client.post(
            '/nbagame/v1/leaderboards/season-starts/events',
            headers=self.auth_headers(login_data, **{'Idempotency-Key': key}),
            json=body,
        )

    def test_login_hashes_openid_and_returns_no_sensitive_fields(self):
        result = self.login()
        self.assertNotIn('openid', result)
        self.assertNotIn('session_key', result)
        conn = sqlite3.connect(os.environ['NBAGAME_DB_PATH'])
        try:
            columns = {row[1] for row in conn.execute('PRAGMA table_info(nbagame_application_users)')}
            row = conn.execute('SELECT openid_hash FROM nbagame_application_users').fetchone()
        finally:
            conn.close()
        self.assertNotIn('openid', columns)
        self.assertNotEqual(row[0], 'court-deck-openid')
        self.assertTrue(result['user']['isNew'])

    def test_manifest_etag_and_published_file_are_scoped_to_app(self):
        headers = {'X-App-Id': 'court-deck-prod'}
        manifest = self.client.get('/nbagame/v1/assets/manifest?group=headshot-sprites', headers=headers)
        self.assertEqual(manifest.status_code, 200)
        payload = manifest.get_json()['data']
        self.assertEqual(len(payload['assets']), 15)
        self.assertEqual(payload['assets'][0]['key'], 'players-0')
        self.assertTrue(payload['assets'][0]['url'].startswith('https://cdn.example.test/nbagame/v1/assets/files/'))
        self.assertEqual(manifest.headers['Vary'], 'X-App-Id')
        unchanged = self.client.get('/nbagame/v1/assets/manifest?group=headshot-sprites', headers={**headers, 'If-None-Match': manifest.headers['ETag']})
        self.assertEqual(unchanged.status_code, 304)
        asset = self.client.get(payload['assets'][0]['url'], headers=headers)
        try:
            self.assertEqual(asset.status_code, 200)
            self.assertIn('immutable', asset.headers['Cache-Control'])
            self.assertEqual(asset.headers['X-Content-Type-Options'], 'nosniff')
        finally:
            asset.close()
        forbidden = self.client.get('/nbagame/v1/assets/manifest', headers={'X-App-Id': 'nba'})
        self.assertEqual(forbidden.status_code, 403)

    def test_home_manifest_publishes_v6_png(self):
        manifest = self.client.get(
            '/nbagame/v1/assets/manifest?group=home',
            headers={'X-App-Id': 'court-deck-prod'},
        )
        self.assertEqual(manifest.status_code, 200)
        assets = {asset['key']: asset for asset in manifest.get_json()['data']['assets']}
        self.assertIn('broadcast-home-v6', assets)
        self.assertNotIn('broadcast-home-v5', assets)
        self.assertEqual(assets['broadcast-home-v6']['contentType'], 'image/png')
        self.assertTrue(assets['broadcast-home-v6']['url'].endswith('/broadcast-home-v6.png'))

    def test_write_routes_reject_non_json_malformed_json_and_oversized_bodies(self):
        headers = {'X-App-Id': 'court-deck-prod'}
        non_json = self.client.post(
            '/nbagame/v1/auth/wechat/login', headers=headers, data='code=one-time-code',
            content_type='application/x-www-form-urlencoded',
        )
        self.assertEqual(non_json.status_code, 415)
        self.assertIn('error', non_json.get_json())

        malformed = self.client.post(
            '/nbagame/v1/auth/wechat/login', headers=headers, data='{"code":',
            content_type='application/json',
        )
        self.assertEqual(malformed.status_code, 400)
        self.assertIn('error', malformed.get_json())

        oversized = self.client.post(
            '/nbagame/v1/auth/wechat/login', headers=headers,
            data=b'{"code":"' + (b'x' * (2 * 1024 * 1024)) + b'"}',
            content_type='application/json',
        )
        self.assertEqual(oversized.status_code, 413)
        self.assertIn('error', oversized.get_json())

    def test_login_rate_limit_uses_forwarded_ip_and_returns_retry_after(self):
        os.environ['NBAGAME_LOGIN_RATE_LIMIT'] = '2'
        os.environ['NBAGAME_LOGIN_RATE_WINDOW_SECONDS'] = '60'
        self.reload_app()
        import nbagame_backend.routes as routes

        with mock.patch.object(routes, 'exchange_wechat_code', return_value={'openid': 'rate-limit-user'}):
            headers = {'X-App-Id': 'court-deck-prod', 'X-Real-IP': '198.51.100.10'}
            self.assertEqual(self.client.post('/nbagame/v1/auth/wechat/login', headers=headers, json={'code': 'code-1'}).status_code, 200)
            self.assertEqual(self.client.post('/nbagame/v1/auth/wechat/login', headers=headers, json={'code': 'code-2'}).status_code, 200)
            limited = self.client.post('/nbagame/v1/auth/wechat/login', headers=headers, json={'code': 'code-3'})
            self.assertEqual(limited.status_code, 429)
            self.assertGreater(int(limited.headers['Retry-After']), 0)
            self.assertIn('error', limited.get_json())

            other_ip = self.client.post(
                '/nbagame/v1/auth/wechat/login',
                headers={'X-App-Id': 'court-deck-prod', 'X-Real-IP': '198.51.100.11'},
                json={'code': 'code-4'},
            )
            self.assertEqual(other_ip.status_code, 200)

    def test_source_change_automatically_publishes_a_new_content_version(self):
        headers = {'X-App-Id': 'court-deck-prod'}
        original_response = self.client.get(
            '/nbagame/v1/assets/manifest?group=home', headers=headers,
        )
        original_manifest = original_response.get_json()['data']
        original_manifest_etag = original_response.headers['ETag']
        self.assertTrue(original_manifest['manifestVersion'].startswith('content-'))
        original_assets = {asset['key']: asset for asset in original_manifest['assets']}
        original_home = original_assets['broadcast-home-v6']
        original_arena = original_assets['broadcast-arena-bg']
        original = self.client.get(original_home['url'], headers=headers)
        original_body, original_etag = original.data, original.headers['ETag']
        original.close()

        source = Path(self.assets_dir, ASSET_SPECS['home'][0][1])
        changed_body = PNG_1X1 + b'changed-after-publication'
        source.write_bytes(changed_body)
        self.reload_app()

        updated_response = self.client.get(
            '/nbagame/v1/assets/manifest?group=home',
            headers={**headers, 'If-None-Match': original_manifest_etag},
        )
        self.assertEqual(updated_response.status_code, 200)
        self.assertNotEqual(updated_response.headers['ETag'], original_manifest_etag)
        updated_manifest = updated_response.get_json()['data']
        updated_assets = {asset['key']: asset for asset in updated_manifest['assets']}
        self.assertNotEqual(updated_manifest['manifestVersion'], original_manifest['manifestVersion'])
        self.assertNotEqual(updated_assets['broadcast-home-v6']['url'], original_home['url'])
        self.assertEqual(updated_assets['broadcast-arena-bg']['url'], original_arena['url'])

        updated = self.client.get(updated_assets['broadcast-home-v6']['url'], headers=headers)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data, changed_body)
        updated.close()

        immutable_old = self.client.get(original_home['url'], headers=headers)
        self.assertEqual(immutable_old.status_code, 200)
        self.assertEqual(immutable_old.data, original_body)
        self.assertEqual(immutable_old.headers['ETag'], original_etag)
        immutable_old.close()

    def test_missing_published_asset_is_restored_on_startup(self):
        headers = {'X-App-Id': 'court-deck-prod'}
        manifest = self.client.get('/nbagame/v1/assets/manifest?group=home', headers=headers).get_json()['data']
        conn = sqlite3.connect(os.environ['NBAGAME_DB_PATH'])
        try:
            storage_path = conn.execute(
                '''SELECT files.storage_path FROM nbagame_asset_manifest_items items
                   JOIN nbagame_asset_files files
                     ON files.application_id=items.application_id
                    AND files.version=items.asset_version
                    AND files.asset_key=items.asset_key
                   WHERE items.application_id=? AND items.manifest_version=? AND items.asset_key=?''',
                ('court-deck-prod', manifest['manifestVersion'], manifest['assets'][0]['key']),
            ).fetchone()[0]
        finally:
            conn.close()
        published_path = Path(self.published_assets_dir, storage_path)
        published_path.unlink()

        self.reload_app()

        self.assertTrue(published_path.is_file())
        reloaded_manifest = self.client.get(
            '/nbagame/v1/assets/manifest?group=home', headers=headers,
        ).get_json()['data']
        self.assertEqual(reloaded_manifest['manifestVersion'], manifest['manifestVersion'])
        self.assertEqual(reloaded_manifest['assets'], manifest['assets'])
        restored = self.client.get(manifest['assets'][0]['url'], headers=headers)
        self.assertEqual(restored.status_code, 200)
        restored.close()

    def test_legacy_database_migrates_and_manual_asset_url_remains_available(self):
        legacy_body = PNG_1X1 + b'legacy-manual-version'
        legacy_relative_path = 'court-deck-prod/legacy-v1/home/legacy-home.png'
        legacy_path = Path(self.published_assets_dir, legacy_relative_path)
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_bytes(legacy_body)
        conn = sqlite3.connect(os.environ['NBAGAME_DB_PATH'])
        try:
            conn.execute('DROP TABLE nbagame_asset_manifest_items')
            conn.execute(
                '''INSERT INTO nbagame_asset_files
                   (application_id, version, asset_group, asset_key, extension, storage_path,
                    sha256, content_type, bytes, width, height)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    'court-deck-prod', 'legacy-v1', 'home', 'legacy-home', 'png',
                    legacy_relative_path, hashlib.sha256(legacy_body).hexdigest(),
                    'image/png', len(legacy_body), 1, 1,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        self.reload_app()

        manifest = self.client.get(
            '/nbagame/v1/assets/manifest?group=home',
            headers={'X-App-Id': 'court-deck-prod'},
        )
        self.assertEqual(manifest.status_code, 200)
        legacy = self.client.get(
            '/nbagame/v1/assets/files/legacy-v1/legacy-home.png',
            headers={'X-App-Id': 'court-deck-prod'},
        )
        self.assertEqual(legacy.status_code, 200)
        self.assertEqual(legacy.data, legacy_body)
        legacy.close()

    def test_idempotency_key_must_be_a_uuid(self):
        login = self.login()
        response = self.client.put(
            '/nbagame/v1/profile',
            headers={
                'Authorization': 'Bearer ' + login['accessToken'],
                'Idempotency-Key': 'not-a-uuid',
            },
            json={'nickname': 'Player'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['error']['code'], 'VALIDATION_ERROR')

    def test_career_rejects_stale_revision_and_replays_idempotent_write(self):
        login = self.login()
        headers = self.auth_headers(login, **{'If-Match': '"career-0"', 'Idempotency-Key': 'career-write-1'})
        first = self.client.put('/nbagame/v1/career', headers=headers, json=self.career_payload())
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()['data']['revision'], 1)
        retry = self.client.put('/nbagame/v1/career', headers=headers, json=self.career_payload())
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.get_json()['data']['revision'], 1)
        changed = self.career_payload()
        changed['clientRevision'] = 1
        changed['snapshot']['season']['wins'] = 13
        conflict = self.client.put('/nbagame/v1/career', headers=self.auth_headers(login, **{'If-Match': '"career-0"', 'Idempotency-Key': 'career-write-2'}), json=changed)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.get_json()['error']['code'], 'CAREER_CONFLICT')
        stored = self.client.get('/nbagame/v1/career', headers=self.auth_headers(login))
        self.assertEqual(stored.get_json()['data']['snapshot']['state']['careerTeam'], 'LAL')

    def test_career_deduplicates_client_revision_and_rejects_changed_snapshot(self):
        login = self.login()
        first = self.write_career(login, key='career-client-revision-1')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()['data']['revision'], 1)

        duplicate = self.write_career(
            login, key='career-client-revision-2', expected_revision=1,
        )
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.get_json()['data']['revision'], 1)

        changed = self.career_payload()
        changed['snapshot']['season']['wins'] = 13
        conflict = self.client.put(
            '/nbagame/v1/career',
            headers=self.auth_headers(login, **{
                'If-Match': '"career-1"',
                'Idempotency-Key': 'career-client-revision-3',
            }),
            json=changed,
        )
        self.assertEqual(conflict.status_code, 409)
        stored = self.client.get('/nbagame/v1/career', headers=self.auth_headers(login))
        self.assertEqual(stored.get_json()['data']['revision'], 1)
        self.assertEqual(stored.get_json()['data']['snapshot']['state']['season']['wins'], 12)

    def test_concurrent_career_writes_allow_only_one_revision_winner(self):
        login = self.login()
        self.assertEqual(self.write_career(login, key='career-concurrent-base').status_code, 200)
        barrier = threading.Barrier(2)
        statuses = []
        statuses_lock = threading.Lock()

        def write_changed_snapshot(key, wins):
            body = self.career_payload()
            body['clientRevision'] = 1
            body['snapshot']['season']['wins'] = wins
            with self.app_module.app.test_client() as client:
                barrier.wait()
                response = client.put(
                    '/nbagame/v1/career',
                    headers=self.auth_headers(login, **{
                        'If-Match': '"career-1"',
                        'Idempotency-Key': key,
                    }),
                    json=body,
                )
            with statuses_lock:
                statuses.append(response.status_code)

        threads = [
            threading.Thread(target=write_changed_snapshot, args=('career-concurrent-a', 13)),
            threading.Thread(target=write_changed_snapshot, args=('career-concurrent-b', 14)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sorted(statuses), [200, 409])
        stored = self.client.get('/nbagame/v1/career', headers=self.auth_headers(login))
        self.assertEqual(stored.get_json()['data']['revision'], 2)

    def test_concurrent_profile_retries_return_the_first_result(self):
        login = self.login()
        barrier = threading.Barrier(2)
        results = []
        results_lock = threading.Lock()

        def write_profile(nickname):
            with self.app_module.app.test_client() as client:
                barrier.wait()
                response = client.put(
                    '/nbagame/v1/profile',
                    headers=self.auth_headers(login, **{'Idempotency-Key': 'same-profile-write'}),
                    json={'nickname': nickname},
                )
            with results_lock:
                results.append((response.status_code, response.get_json()['data']))

        threads = [
            threading.Thread(target=write_profile, args=('Player A',)),
            threading.Thread(target=write_profile, args=('Player B',)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual([status for status, _ in results], [200, 200])
        self.assertEqual(results[0][1], results[1][1])

    def test_career_ignores_rank_and_rejects_nested_identity_fields(self):
        login = self.login()
        body = self.career_payload()
        body['rank'] = 1
        body['snapshot']['leaderboardProfile'] = {'rank': 2, 'playerName': 'Player'}
        accepted = self.client.put(
            '/nbagame/v1/career',
            headers=self.auth_headers(login, **{
                'If-Match': '"career-0"',
                'Idempotency-Key': 'career-with-rank',
            }),
            json=body,
        )
        self.assertEqual(accepted.status_code, 200)
        stored = self.client.get('/nbagame/v1/career', headers=self.auth_headers(login)).get_json()['data']
        self.assertNotIn('rank', stored['snapshot']['state']['leaderboardProfile'])

        changed = self.career_payload()
        changed['clientRevision'] = 1
        changed['snapshot']['leaderboardProfile'] = {'user_id': 'another-user'}
        rejected = self.client.put(
            '/nbagame/v1/career',
            headers=self.auth_headers(login, **{
                'If-Match': '"career-1"',
                'Idempotency-Key': 'career-with-identity',
            }),
            json=changed,
        )
        self.assertEqual(rejected.status_code, 400)

    def test_profile_sync_and_leaderboard_event_are_idempotent(self):
        login = self.login()
        profile = self.client.put('/nbagame/v1/profile', headers=self.auth_headers(login, **{'Idempotency-Key': 'profile-1'}), json={'nickname': 'Court Player', 'avatarUrl': 'https://example.com/avatar.png'})
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.get_json()['data']['user']['nickname'], 'Court Player')
        self.assertEqual(self.write_career(login, key='career-before-event').status_code, 200)
        event = self.create_season_start(
            login, key='event-1', event_id='event-1', occurred_at='2026-07-22T08:02:00Z',
        )
        self.assertEqual(event.get_json()['data']['starts'], 1)
        retry = self.create_season_start(
            login, key='event-1', event_id='event-1', occurred_at='2026-07-22T08:02:00Z',
        )
        self.assertEqual(retry.get_json()['data']['starts'], 1)
        personal = self.client.get('/nbagame/v1/leaderboards/season-starts?scope=personal', headers=self.auth_headers(login))
        self.assertEqual(personal.get_json()['data']['rows'][0]['playerName'], 'Court Player')
        friends = self.client.get('/nbagame/v1/leaderboards/season-starts?scope=friends', headers=self.auth_headers(login))
        self.assertFalse(friends.get_json()['data']['friendsAvailable'])

    def test_delete_career_keeps_season_start_history(self):
        login = self.login()
        self.assertEqual(self.write_career(login, key='career-2').status_code, 200)
        self.assertEqual(self.create_season_start(login, key='event-2', event_id='event-2').status_code, 200)
        deleted = self.client.delete('/nbagame/v1/career', headers=self.auth_headers(login, **{'If-Match': '"career-1"', 'Idempotency-Key': 'delete-1'}))
        self.assertEqual(deleted.status_code, 200)
        personal = self.client.get('/nbagame/v1/leaderboards/season-starts?scope=personal', headers=self.auth_headers(login))
        self.assertEqual(personal.get_json()['data']['rows'][0]['starts'], 1)

    def test_duplicate_event_returns_first_result_even_when_payload_changes(self):
        login = self.login()
        self.assertEqual(self.write_career(login, key='career-duplicate-event').status_code, 200)
        first = self.create_season_start(login, key='event-key-1', event_id='stable-event-id')
        self.assertEqual(first.status_code, 200)

        duplicate = self.create_season_start(
            login, key='event-key-2', event_id='stable-event-id', team='BOS', season_number=2,
        )
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.get_json()['data'], first.get_json()['data'])

    def test_season_start_must_match_career_and_revision_can_only_count_once(self):
        login = self.login()
        self.assertEqual(self.write_career(login, key='career-season-start').status_code, 200)

        mismatch = self.create_season_start(
            login, key='event-mismatch', event_id='event-mismatch', team='BOS',
        )
        self.assertEqual(mismatch.status_code, 409)

        first = self.create_season_start(login, key='event-first', event_id='event-first')
        self.assertEqual(first.status_code, 200)
        repeated_revision = self.create_season_start(
            login, key='event-second', event_id='event-second',
        )
        self.assertEqual(repeated_revision.status_code, 200)
        self.assertEqual(repeated_revision.get_json()['data'], first.get_json()['data'])
        personal = self.client.get(
            '/nbagame/v1/leaderboards/season-starts?scope=personal',
            headers=self.auth_headers(login),
        )
        self.assertEqual(personal.get_json()['data']['rows'][0]['starts'], 1)

    def test_leaderboard_orders_by_server_time_each_count_was_reached(self):
        player_a = self.login('ranking-player-a')
        player_b = self.login('ranking-player-b')
        for player, name, key in ((player_a, 'Player A', 'profile-a'), (player_b, 'Player B', 'profile-b')):
            response = self.client.put(
                '/nbagame/v1/profile',
                headers=self.auth_headers(player, **{'Idempotency-Key': key}),
                json={'nickname': name},
            )
            self.assertEqual(response.status_code, 200)

        import nbagame_backend.service as service
        clock = {'now': datetime(2026, 7, 22, 10, 0, 0)}
        with mock.patch.object(service, 'utcnow', side_effect=lambda: clock['now']):
            self.assertEqual(self.write_career(player_a, key='rank-career-a-1').status_code, 200)
            self.assertEqual(self.create_season_start(player_a, key='rank-event-a-1', event_id='rank-event-a-1').status_code, 200)
            clock['now'] = datetime(2026, 7, 22, 10, 1, 0)
            self.assertEqual(self.write_career(player_b, key='rank-career-b-1').status_code, 200)
            self.assertEqual(self.create_season_start(player_b, key='rank-event-b-1', event_id='rank-event-b-1').status_code, 200)

            clock['now'] = datetime(2026, 7, 22, 10, 2, 0)
            self.assertEqual(self.write_career(
                player_b, key='rank-career-b-2', expected_revision=1,
                client_revision=1, season_number=2,
            ).status_code, 200)
            self.assertEqual(self.create_season_start(
                player_b, key='rank-event-b-2', event_id='rank-event-b-2',
                season_number=2, occurred_at='2099-01-01T00:00:00Z',
            ).status_code, 200)

            clock['now'] = datetime(2026, 7, 22, 10, 3, 0)
            self.assertEqual(self.write_career(
                player_a, key='rank-career-a-2', expected_revision=1,
                client_revision=1, season_number=2,
            ).status_code, 200)
            self.assertEqual(self.create_season_start(
                player_a, key='rank-event-a-2', event_id='rank-event-a-2',
                season_number=2, occurred_at='2000-01-01T00:00:00Z',
            ).status_code, 200)

        leaderboard = self.client.get(
            '/nbagame/v1/leaderboards/season-starts?scope=global',
            headers=self.auth_headers(player_a),
        )
        rows = leaderboard.get_json()['data']['rows']
        self.assertEqual([(row['playerName'], row['starts']) for row in rows[:2]], [
            ('Player B', 2), ('Player A', 2),
        ])
