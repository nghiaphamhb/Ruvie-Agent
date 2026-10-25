"""F013-010 PostgreSQL regression for admin password reset and session revocation."""
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import select

import test_f005_007_e2e as fixtures
from ruvie.models import AuditEvent, AuthSession, User


class AdminPasswordResetEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.F005007EndToEndTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.F005007EndToEndTests.tearDownClass()

    def setUp(self):
        self.fixture = fixtures.F005007EndToEndTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.factory = self.fixture.client.app.state.session_factory
        with self.factory() as db:
            db.get(User, "alpha").system_role = "admin"
            db.commit()
        self.csrf, _ = self.fixture._login("alpha@example.test")

    def test_password_reset_revokes_existing_sessions_and_requires_new_password(self):
        actor = self.fixture.client
        target = TestClient(actor.app, base_url=fixtures.ORIGIN)
        self.addCleanup(target.close)
        old_password = " old-password-123 "
        new_password = "  reset-password-456  "
        created = actor.post(
            "/admin/users",
            headers={"Origin": fixtures.ORIGIN, "X-CSRF-Token": self.csrf},
            json={
                "display_name": "Reset target",
                "email": "reset-target@example.test",
                "password": old_password,
                "system_role": "user",
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        target_login = target.post(
            "/auth/login",
            headers={"Origin": fixtures.ORIGIN},
            json={"email": "reset-target@example.test", "password": old_password},
        )
        self.assertEqual(target_login.status_code, 200, target_login.text)
        target_cookie = target.cookies.get("ruvie_session")
        actor_session = actor.get("/auth/session").json()
        reset = actor.patch(
            f"/admin/users/{created.json()['user']['id']}",
            headers={"Origin": fixtures.ORIGIN, "X-CSRF-Token": self.csrf},
            json={"password": new_password},
        )
        self.assertEqual(reset.status_code, 200, reset.text)
        self.assertNotIn(new_password, reset.text)
        self.assertNotIn("password_hash", reset.text)
        self.assertEqual(target.get("/auth/session").status_code, 401)
        self.assertEqual(target.cookies.get("ruvie_session"), target_cookie)
        self.assertEqual(actor.get("/auth/session").json(), actor_session)
        self.assertEqual(
            target.post(
                "/auth/login",
                headers={"Origin": fixtures.ORIGIN},
                json={"email": "reset-target@example.test", "password": old_password},
            ).status_code,
            401,
        )
        self.assertEqual(
            target.post(
                "/auth/login",
                headers={"Origin": fixtures.ORIGIN},
                json={"email": "reset-target@example.test", "password": new_password},
            ).status_code,
            200,
        )
        with self.factory() as db:
            event = db.scalar(
                select(AuditEvent).where(
                    AuditEvent.action == "account.update",
                    AuditEvent.resource_id == created.json()["user"]["id"],
                )
            )
            self.assertEqual(event.reason, "updated_password")
            self.assertNotIn(new_password, event.reason)
            self.assertEqual(db.query(AuthSession).filter_by(user_id="alpha").count(), 1)


if __name__ == "__main__":
    unittest.main()
