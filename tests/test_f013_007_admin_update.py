"""F013-007: safe admin account read-back and partial identity updates."""
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
from ruvie.models import AuditEvent, Base, User
from ruvie.services.auth import hash_password
import test_f005_007_e2e as fixtures

ORIGIN = "https://update.test"
PASSWORD = "update-test-password"


class AdminAccountUpdateTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", poolclass=StaticPool,
                               connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        self.factory = sessionmaker(engine)
        with self.factory() as db:
            db.add_all([
                User(id="actor", display_name="Admin", email="admin@example.test",
                     system_role="admin", password_hash=hash_password(PASSWORD), is_active=True,
                     created_at=datetime(2026, 10, 24, tzinfo=timezone.utc)),
                User(id="target", display_name="Before", email="before@example.test",
                     system_role="user", password_hash="private-hash", is_active=True,
                     created_at=datetime(2026, 10, 23, tzinfo=timezone.utc)),
                User(id="other", display_name="Other", email="other@example.test",
                     system_role="user", password_hash="private-hash", is_active=True,
                     created_at=datetime(2026, 10, 22, tzinfo=timezone.utc)),
            ])
            db.commit()
        self.app = FastAPI()
        self.app.include_router(auth_router)
        self.app.include_router(router)
        self.app.state.settings = SimpleNamespace(auth_allowed_origins=(ORIGIN,))
        self.app.state.session_factory = self.factory
        self.client = TestClient(self.app, base_url=ORIGIN)
        self.addCleanup(self.client.close)
        login = self.client.post("/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "admin@example.test", "password": PASSWORD,
        })
        self.assertEqual(login.status_code, 200, login.text)
        self.headers = {"Origin": ORIGIN, "X-CSRF-Token": login.json()["csrf_token"]}

    def test_get_by_id_returns_only_safe_metadata_and_requires_admin(self):
        response = self.client.get("/admin/users/target")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertEqual(response.json()["user"]["id"], "target")
        self.assertEqual(set(response.json()["user"]), {
            "id", "display_name", "email", "system_role", "is_active", "created_at",
        })
        self.assertNotIn("private-hash", response.text)
        self.assertNotIn("set-cookie", response.headers)
        self.assertEqual(self.client.get("/admin/users/missing").status_code, 404)
        with self.factory() as db:
            db.get(User, "actor").system_role = "user"
            db.commit()
        denied = self.client.get("/admin/users/target")
        self.assertEqual(denied.status_code, 403)
        self.assertNotIn("before@example.test", denied.text)

    def test_patch_updates_only_supplied_normalized_fields_and_audits(self):
        response = self.client.patch("/admin/users/target", headers=self.headers, json={
            "display_name": "  Renamed User ", "email": " NEW@Example.test ",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((response.json()["user"]["display_name"], response.json()["user"]["email"]),
                         ("Renamed User", "new@example.test"))
        self.assertEqual(response.json()["user"]["system_role"], "user")
        with self.factory() as db:
            updated = db.get(User, "target")
            self.assertEqual(updated.password_hash, "private-hash")
            event = db.scalar(select(AuditEvent).where(AuditEvent.action == "account.update"))
            self.assertIsNotNone(event)
            self.assertEqual((event.actor_user_id, event.resource_id, event.outcome),
                             ("actor", "target", "allow"))

    def test_patch_rejects_duplicate_email_invalid_and_empty_updates(self):
        for body, status in (({"email": "other@example.test"}, 409),
                             ({"email": "not-an-email"}, 422), ({}, 422)):
            with self.subTest(body=body):
                response = self.client.patch("/admin/users/target", headers=self.headers, json=body)
                self.assertEqual(response.status_code, status, response.text)
                self.assertEqual(response.headers.get("cache-control"), "no-store")
                self.assertNotIn("private-hash", response.text)

    def test_patch_accepts_role_after_f013_008(self):
        response = self.client.patch("/admin/users/target", headers=self.headers,
                                     json={"system_role": "admin"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["user"]["system_role"], "admin")

    def test_patch_requires_origin_csrf_and_fresh_database_admin(self):
        self.assertEqual(self.client.patch("/admin/users/target", json={
            "display_name": "Changed",
        }).status_code, 403)
        no_csrf = self.client.patch("/admin/users/target", headers={"Origin": ORIGIN}, json={
            "display_name": "Changed",
        })
        self.assertEqual(no_csrf.status_code, 403)
        with self.factory() as db:
            db.get(User, "actor").system_role = "user"
            db.commit()
        denied = self.client.patch("/admin/users/target", headers=self.headers, json={
            "display_name": "Changed",
        })
        self.assertEqual(denied.status_code, 403)
        with self.factory() as db:
            self.assertEqual(db.get(User, "target").display_name, "Before")


class AdminAccountUpdatePostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.F005007EndToEndTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.F005007EndToEndTests.tearDownClass()

    def test_production_routes_update_and_read_back_postgres_identity(self):
        fixture = fixtures.F005007EndToEndTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        factory = fixture.client.app.state.session_factory
        with factory() as db:
            db.get(User, "alpha").system_role = "admin"
            db.commit()
        csrf, session_cookie = fixture._login("alpha@example.test")
        headers = {"Origin": fixtures.ORIGIN, "X-CSRF-Token": csrf}
        response = fixture.client.patch("/admin/users/beta", headers=headers, json={
            "display_name": "Renamed in PostgreSQL", "email": "RENAMED@EXAMPLE.TEST",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((response.json()["user"]["display_name"], response.json()["user"]["email"]),
                         ("Renamed in PostgreSQL", "renamed@example.test"))
        self.assertEqual(fixture.client.cookies.get("ruvie_session"), session_cookie)
        readback = fixture.client.get("/admin/users/beta")
        self.assertEqual(readback.status_code, 200, readback.text)
        self.assertEqual(readback.json(), response.json())
        with factory() as db:
            event = db.scalar(select(AuditEvent).where(
                AuditEvent.action == "account.update", AuditEvent.resource_id == "beta",
            ))
            self.assertIsNotNone(event)
            self.assertEqual(event.actor_user_id, "alpha")


if __name__ == "__main__":
    unittest.main()
