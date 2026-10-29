"""Disabled login distinguishes correct credentials without creating sessions."""
import unittest
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from ruvie.models import Base, User, AuthSession
from ruvie.api.auth import router
from ruvie.services.auth import AuthService, AccountDisabledError, hash_password

ORIGIN = 'https://login.test'
PASSWORD = 'test-password-123'

class DisabledLoginTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine)
        with self.factory() as db:
            db.add_all([User(id='disabled', email='disabled@example.test', display_name='Disabled', password_hash=hash_password(PASSWORD), is_active=False), User(id='enabled', email='enabled@example.test', display_name='Enabled', password_hash=hash_password(PASSWORD), is_active=True), User(id='nohash', email='nohash@example.test', display_name='No hash', password_hash=None, is_active=False)])
            db.commit()
        app = FastAPI()
        app.include_router(router)
        app.state.settings = SimpleNamespace(auth_allowed_origins=(ORIGIN,))
        app.state.session_factory = self.factory
        self.client = TestClient(app, base_url=ORIGIN)
        self.addCleanup(self.client.close)

    def test_service_matrix(self):
        with self.factory() as db:
            service = AuthService(db)
            self.assertIsNotNone(service.authenticate('enabled@example.test', PASSWORD))
            for email, password in [('enabled@example.test', 'wrong'), ('disabled@example.test', 'wrong'), ('missing@example.test', PASSWORD), ('nohash@example.test', PASSWORD)]:
                self.assertIsNone(service.authenticate(email, password))
            with self.assertRaises(AccountDisabledError):
                service.authenticate('disabled@example.test', PASSWORD)
            self.assertEqual(db.query(AuthSession).count(), 0)

    def test_http_disabled_login_and_invalid_credentials(self):
        headers = {'Origin': ORIGIN}
        with self.factory() as db:
            user = db.get(User, 'disabled')
            original = (user.password_hash, user.system_role, user.is_active)
        def login(email, password):
            return self.client.post('/auth/login', headers=headers, json={'email': email, 'password': password})
        response = login('disabled@example.test', PASSWORD)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {'detail': {'code': 'account_disabled'}})
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertNotIn('set-cookie', response.headers)
        wrong = login('disabled@example.test', 'wrong')
        missing = login('missing@example.test', PASSWORD)
        nohash = login('nohash@example.test', PASSWORD)
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(nohash.status_code, 401)
        self.assertEqual(wrong.json(), missing.json())
        self.assertEqual(wrong.json(), nohash.json())
        for failed in (wrong, missing, nohash):
            self.assertEqual(failed.headers['cache-control'], 'no-store')
            self.assertNotIn('set-cookie', failed.headers)
        self.assertNotIn(PASSWORD, response.text)
        rejected = self.client.post('/auth/login', headers={'Origin': 'https://invalid.test'}, json={'email': 'disabled@example.test', 'password': PASSWORD})
        self.assertEqual(rejected.status_code, 403)
        self.assertNotIn('account_disabled', rejected.text)
        with self.factory() as db:
            self.assertEqual(db.query(AuthSession).count(), 0)
            user = db.get(User, 'disabled')
            self.assertEqual((user.password_hash, user.system_role, user.is_active), original)
        self.assertEqual(login('enabled@example.test', PASSWORD).status_code, 200)
