"""Presence uses trusted sessions, server timestamps and a bounded online lease."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ruvie.api.auth import router as auth_router
from ruvie.api.admin import router as admin_router
from ruvie.models import AuthSession, Base, User
from ruvie.services.auth import hash_password
import test_f005_007_e2e as fixtures

ORIGIN = "https://presence.test"
PASSWORD = "presence-password"


class UserPresenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool,
                                    connect_args={"check_same_thread": False})
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine)
        with self.factory() as db:
            for identity, role in (("admin", "admin"), ("user", "user")):
                db.add(User(id=identity, email=f"{identity}@presence.test", display_name=identity,
                            password_hash=hash_password(PASSWORD), system_role=role))
            db.commit()
        app = FastAPI()
        app.include_router(auth_router)
        app.include_router(admin_router)
        app.state.session_factory = self.factory
        app.state.settings = SimpleNamespace(auth_allowed_origins=(ORIGIN,))
        self.app = app
        self.admin, self.admin_csrf = self.login("admin")

    def login(self, identity):
        client = TestClient(self.app, base_url=ORIGIN)
        self.addCleanup(client.close)
        response = client.post("/auth/login", headers={"Origin": ORIGIN},
                               json={"email": f"{identity}@presence.test", "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)
        return client, response.json()["csrf_token"]

    def presence(self, identity):
        response = self.admin.get("/admin/users/list")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn(self.admin.cookies["ruvie_session"], response.text)
        return response.json()["presence"][identity]

    def test_login_online_timeout_and_never_seen(self):
        self.assertEqual(self.presence("user"), {"is_online": False, "last_active_at": None})
        client, csrf = self.login("user")
        self.assertTrue(self.presence("user")["is_online"])
        with self.factory() as db:
            session = db.scalar(select(AuthSession).where(AuthSession.user_id == "user"))
            session.last_seen_at = datetime.now(timezone.utc) - timedelta(seconds=181)
            db.commit()
        self.assertFalse(self.presence("user")["is_online"])
        response = client.post("/auth/presence", headers={"Origin": ORIGIN, "X-CSRF-Token": csrf})
        self.assertEqual(response.status_code, 204, response.text)
        self.assertTrue(self.presence("user")["is_online"])

    def test_other_device_survives_logout_and_last_active_is_retained(self):
        first, first_csrf = self.login("user")
        second, second_csrf = self.login("user")
        last_active = self.presence("user")["last_active_at"]
        for client, csrf, online in ((first, first_csrf, True), (second, second_csrf, False)):
            response = client.post("/auth/logout", headers={"Origin": ORIGIN, "X-CSRF-Token": csrf})
            self.assertEqual(response.status_code, 204, response.text)
            result = self.presence("user")
            self.assertEqual(result["is_online"], online)
            self.assertEqual(result["last_active_at"], last_active)

    def test_heartbeat_identity_security_and_write_throttle(self):
        client, csrf = self.login("user")
        with self.factory() as db:
            row = db.scalar(select(AuthSession).where(AuthSession.user_id == "user"))
            row.last_seen_at = None
            db.commit()
        for headers, status in (({"Origin": ORIGIN}, 403),
                                ({"Origin": "https://evil.test", "X-CSRF-Token": csrf}, 403)):
            response = client.post("/auth/presence", headers=headers)
            self.assertEqual(response.status_code, status, response.text)
        before_admin = self.presence("admin")["last_active_at"]
        headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf, "X-User-Id": "admin"}
        response = client.post("/auth/presence", headers=headers,
                               json={"user_id": "admin", "last_seen_at": "2099-01-01T00:00:00Z"})
        self.assertEqual(response.status_code, 204, response.text)
        before = self.presence("user")["last_active_at"]
        self.assertLess(datetime.fromisoformat(before), datetime(2099, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(client.post("/auth/presence", headers=headers).status_code, 204)
        self.assertEqual(self.presence("user")["last_active_at"], before)
        self.assertEqual(self.presence("admin")["last_active_at"], before_admin)

    def test_expired_disabled_and_anonymous_sessions_are_not_online(self):
        client, csrf = self.login("user")
        with self.factory() as db:
            row = db.scalar(select(AuthSession).where(AuthSession.user_id == "user"))
            row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        self.assertFalse(self.presence("user")["is_online"])
        headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
        self.assertEqual(client.post("/auth/presence", headers=headers).status_code, 401)
        client, csrf = self.login("user")
        self.assertEqual(client.get("/admin/users/list").status_code, 403)
        with self.factory() as db:
            db.get(User, "user").is_active = False
            db.commit()
        self.assertFalse(self.presence("user")["is_online"])
        self.assertEqual(client.post("/auth/presence", headers={**headers, "X-CSRF-Token": csrf}).status_code, 401)
        client.cookies.clear()
        self.assertEqual(client.post("/auth/presence", headers=headers).status_code, 401)


class UserPresencePostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.F005007EndToEndTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.F005007EndToEndTests.tearDownClass()

    def test_migrated_postgres_stores_presence_and_revocation_clears_online(self):
        fixture = fixtures.F005007EndToEndTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        factory = fixture.client.app.state.session_factory
        with factory() as db:
            db.get(User, "alpha").system_role = "admin"
            db.commit()
        csrf, _ = fixture._login("alpha@example.test")
        client = fixture.client
        before = client.get("/admin/users/list").json()["presence"]["alpha"]
        self.assertTrue(before["is_online"])
        self.assertIsNotNone(before["last_active_at"])
        with factory() as db:
            db.scalar(select(AuthSession).where(AuthSession.user_id == "alpha")).last_seen_at = (
                datetime.now(timezone.utc) - timedelta(seconds=181)
            )
            db.commit()
        self.assertFalse(client.get("/admin/users/list").json()["presence"]["alpha"]["is_online"])
        heartbeat = client.post("/auth/presence", headers={
            "Origin": fixtures.ORIGIN, "X-CSRF-Token": csrf,
        })
        self.assertEqual(heartbeat.status_code, 204, heartbeat.text)
        self.assertTrue(client.get("/admin/users/list").json()["presence"]["alpha"]["is_online"])
        with factory() as db:
            self.assertIsNotNone(db.get(User, "alpha").last_active_at)
            self.assertIsNotNone(db.scalar(select(AuthSession).where(AuthSession.user_id == "alpha")).last_seen_at)
            db.execute(AuthSession.__table__.delete().where(AuthSession.user_id == "alpha"))
            db.commit()
        self.assertEqual(client.get("/auth/session").status_code, 401)
