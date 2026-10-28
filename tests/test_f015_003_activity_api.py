"""HTTP contract for account activation using real cookie sessions."""
import unittest
from fastapi.testclient import TestClient
from ruvie.services.auth import hash_password
from test_f013_008_admin_roles import AdminRoleApiTests, ORIGIN
from ruvie.models import User

class ActivityApiTests(AdminRoleApiTests):
    def test_activity_revokes_sessions_and_requires_new_login(self):
        with self.factory() as db:
            db.get(User, 'target').password_hash = hash_password('target-password-123')
            db.commit()
        target = TestClient(self.app, base_url=ORIGIN)
        self.addCleanup(target.close)
        login = target.post('/auth/login', headers={'Origin': ORIGIN}, json={'email': 'target@example.test', 'password': 'target-password-123'})
        self.assertEqual(login.status_code, 200)
        response = self.client.patch('/admin/users/target/activity', headers=self.headers, json={'is_active': False})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()['user']['is_active'])
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertNotIn('set-cookie', response.headers)
        self.assertEqual(target.get('/auth/session').status_code, 401)
        opened = self.client.patch('/admin/users/target/activity', headers=self.headers, json={'is_active': True})
        self.assertEqual(opened.status_code, 200, opened.text)
        self.assertEqual(target.get('/auth/session').status_code, 401)
        self.assertEqual(target.post('/auth/login', headers={'Origin': ORIGIN}, json={'email': 'target@example.test', 'password': 'target-password-123'}).status_code, 200)

    def test_invalid_body_and_origin_do_not_change_activity(self):
        response = self.client.patch('/admin/users/target/activity', headers=self.headers, json={'is_active': 'false'})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn('false', response.text)
        response = self.client.patch('/admin/users/target/activity', headers={'Origin': 'https://evil.test'}, content='{')
        self.assertEqual(response.status_code, 403)
        with self.factory() as db:
            self.assertTrue(db.get(User, 'target').is_active)

    def test_authorization_and_conflict_failures_are_safe(self):
        denied = self.client.patch('/admin/users/target/activity', headers={'Origin': ORIGIN}, json={'is_active': False})
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()['detail']['code'], 'csrf_invalid')
        self.assertEqual(denied.headers['cache-control'], 'no-store')
        no_user = self.client.patch('/admin/users/missing/activity', headers=self.headers, json={'is_active': False})
        self.assertEqual(no_user.status_code, 404)
        last = self.client.patch('/admin/users/actor/activity', headers=self.headers, json={'is_active': False})
        self.assertEqual(last.status_code, 409)
        self.assertEqual(last.json()['detail']['code'], 'last_active_admin')
        with self.factory() as db:
            db.get(User, 'target').system_role = 'admin'
            db.commit()
        self_lock = self.client.patch('/admin/users/actor/activity', headers=self.headers, json={'is_active': False})
        self.assertEqual(self_lock.status_code, 409)
        self.assertEqual(self_lock.json()['detail']['code'], 'self_deactivation_forbidden')

    def test_failure_is_redacted_and_no_store(self):
        from unittest.mock import patch
        with patch('ruvie.api.admin.AdminAccountService.set_account_activity', side_effect=RuntimeError('private database detail')):
            response = self.client.patch('/admin/users/target/activity', headers=self.headers, json={'is_active': False})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['detail']['code'], 'account_activity_unavailable')
        self.assertNotIn('private database detail', response.text)
        self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_regular_user_cannot_change_activity_even_with_valid_csrf(self):
        with self.factory() as db:
            db.get(User, 'target').password_hash = hash_password('target-password-123')
            db.commit()
        target = TestClient(self.app, base_url=ORIGIN)
        self.addCleanup(target.close)
        login = target.post('/auth/login', headers={'Origin': ORIGIN}, json={'email': 'target@example.test', 'password': 'target-password-123'})
        headers = {'Origin': ORIGIN, 'X-CSRF-Token': login.json()['csrf_token']}
        response = target.patch('/admin/users/actor/activity', headers=headers, json={'is_active': False})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['detail']['code'], 'admin_required')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        with self.factory() as db:
            self.assertTrue(db.get(User, 'actor').is_active)
