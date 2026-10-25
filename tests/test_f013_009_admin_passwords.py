"""F013-009: password reset, atomic session revocation and login synchronization."""
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ruvie.api.admin import router
from ruvie.api.auth import router as auth_router
from ruvie.models import AuditEvent, AuthSession, Base, User
from ruvie.services.auth import hash_password, verify_password

ORIGIN = "https://password-reset.test"
OLD_PASSWORD = "old-password-123"
NEW_PASSWORD = "  new-password-123  "


class AdminPasswordApiTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", poolclass=StaticPool,
                               connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        self.factory = sessionmaker(engine)
        with self.factory() as db:
            db.add_all([
                User(id="actor", display_name="Admin", email="admin@example.test",
                     system_role="admin", password_hash=hash_password(OLD_PASSWORD), is_active=True,
                     created_at=datetime(2026, 10, 24, tzinfo=timezone.utc)),
                User(id="target", display_name="Target", email="target@example.test",
                     system_role="user", password_hash=hash_password(OLD_PASSWORD), is_active=True,
                     created_at=datetime(2026, 10, 23, tzinfo=timezone.utc)),
            ])
            db.commit()
        self.app = FastAPI()
        self.app.include_router(auth_router)
        self.app.include_router(router)
        self.app.state.settings = SimpleNamespace(auth_allowed_origins=(ORIGIN,))
        self.app.state.session_factory = self.factory
        self.actor = TestClient(self.app, base_url=ORIGIN)
        self.addCleanup(self.actor.close)
        login = self.actor.post("/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "admin@example.test", "password": OLD_PASSWORD,
        })
        self.assertEqual(login.status_code, 200, login.text)
        self.actor_headers = {"Origin": ORIGIN, "X-CSRF-Token": login.json()["csrf_token"]}

    def login_target(self, password):
        client = TestClient(self.app, base_url=ORIGIN)
        self.addCleanup(client.close)
        response = client.post("/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "target@example.test", "password": password,
        })
        return client, response

    def test_contract_validates_optional_password_without_trimming_it(self):
        from ruvie.contracts.admin import UpdateAccountRequest

        update = UpdateAccountRequest(password=NEW_PASSWORD)
        self.assertEqual(update.password, NEW_PASSWORD)
        self.assertNotIn("password", repr(update))
        for value in ("short", "x" * 129, None):
            with self.subTest(length=None if value is None else len(value)):
                with self.assertRaises(ValueError):
                    UpdateAccountRequest(password=value)

    def test_password_update_revokes_target_sessions_and_preserves_actor_session(self):
        target, old_login = self.login_target(OLD_PASSWORD)
        self.assertEqual(old_login.status_code, 200)
        actor_cookie = self.actor.cookies.get("ruvie_session")
        response = self.actor.patch("/admin/users/target", headers=self.actor_headers,
                                    json={"password": NEW_PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn(NEW_PASSWORD, response.text)
        self.assertNotIn("password_hash", response.text)
        self.assertEqual(self.actor.cookies.get("ruvie_session"), actor_cookie)
        self.assertEqual(target.get("/auth/session").status_code, 401)
        self.assertEqual(target.post("/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "target@example.test", "password": OLD_PASSWORD,
        }).status_code, 401)
        self.assertEqual(target.post("/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "target@example.test", "password": NEW_PASSWORD,
        }).status_code, 200)
        with self.factory() as db:
            user = db.get(User, "target")
            event = db.scalar(select(AuditEvent).where(
                AuditEvent.action == "account.update", AuditEvent.resource_id == "target",
            ))
            self.assertNotEqual(user.password_hash, OLD_PASSWORD)
            self.assertEqual(event.reason, "updated_password")
            self.assertNotIn(NEW_PASSWORD, event.reason)
            self.assertEqual(db.query(AuthSession).filter_by(user_id="target").count(), 1)
            self.assertEqual(db.query(AuthSession).filter_by(user_id="actor").count(), 1)

    def test_self_reset_revokes_every_session_and_returns_successful_request_then_requires_login(self):
        extra_session, login = self.login_target(OLD_PASSWORD)
        self.assertEqual(login.status_code, 200)
        with self.factory() as db:
            db.add(User(id="other-admin", display_name="Other", email="other@example.test",
                        system_role="admin", password_hash=hash_password(OLD_PASSWORD), is_active=True))
            db.commit()
        second_actor_session = TestClient(self.app, base_url=ORIGIN)
        self.addCleanup(second_actor_session.close)
        second_login = second_actor_session.post("/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "admin@example.test", "password": OLD_PASSWORD,
        })
        self.assertEqual(second_login.status_code, 200)

        response = self.actor.patch("/admin/users/actor", headers=self.actor_headers,
                                    json={"password": NEW_PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)
        with self.factory() as db:
            self.assertEqual(db.query(AuthSession).filter_by(user_id="actor").count(), 0)
        self.assertEqual(self.actor.get("/auth/session").status_code, 401)
        self.assertEqual(second_actor_session.get("/auth/session").status_code, 401)
        self.assertEqual(extra_session.get("/auth/session").status_code, 200)

    def test_invalid_password_is_redacted_and_never_changes_password_or_sessions(self):
        for password in ("tiny", "s" * 129):
            response = self.actor.patch("/admin/users/target", headers=self.actor_headers,
                                        json={"password": password})
            self.assertEqual(response.status_code, 422, response.text)
            self.assertNotIn(password, response.text)
            self.assertEqual(response.json()["detail"]["fields"]["password"], "password_length")
        with self.factory() as db:
            self.assertTrue(verify_password(OLD_PASSWORD, db.get(User, "target").password_hash))
            self.assertEqual(db.query(AuthSession).filter_by(user_id="target").count(), 0)


if __name__ == "__main__":
    unittest.main()
