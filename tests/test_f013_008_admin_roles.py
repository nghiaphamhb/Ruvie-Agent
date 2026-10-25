"""F013-008: admin role changes, last-active-admin protection and session retention."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from types import SimpleNamespace
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ruvie.api.admin import router
from ruvie.api.auth import router as auth_router
from ruvie.contracts.admin import UpdateAccountRequest
from ruvie.models import AuditEvent, Base, User
from ruvie.services.admin import AdminAccountService, AdminRequired
from ruvie.services.auth import hash_password
import test_f005_007_e2e as fixtures

ORIGIN = "https://roles.test"
PASSWORD = "role-test-password"


class AdminRoleApiTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", poolclass=StaticPool,
                               connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        self.factory = sessionmaker(engine)
        Base.metadata.create_all(engine)
        with self.factory() as db:
            db.add_all([
                User(id="actor", display_name="Admin", email="admin@example.test",
                     system_role="admin", password_hash=hash_password(PASSWORD), is_active=True,
                     created_at=datetime(2026, 10, 24, tzinfo=timezone.utc)),
                User(id="target", display_name="Target", email="target@example.test",
                     system_role="user", password_hash="private-hash", is_active=True,
                     created_at=datetime(2026, 10, 23, tzinfo=timezone.utc)),
                User(id="inactive-admin", display_name="Inactive", email="inactive@example.test",
                     system_role="admin", password_hash="private-hash", is_active=False,
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

    def test_contract_accepts_only_supported_role_values_and_role_only_patch(self):
        self.assertEqual(UpdateAccountRequest(system_role="admin").system_role, "admin")
        self.assertEqual(UpdateAccountRequest(system_role="user").system_role, "user")
        for body in ({"system_role": "owner"}, {"system_role": None}, {"password": "secret"}):
            with self.subTest(body=body), self.assertRaises(Exception):
                UpdateAccountRequest.model_validate(body)

    def test_patch_changes_role_and_audits_atomically(self):
        response = self.client.patch("/admin/users/target", headers=self.headers,
                                     json={"system_role": "admin"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["user"]["system_role"], "admin")
        with self.factory() as db:
            event = db.scalar(select(AuditEvent).where(
                AuditEvent.action == "account.update", AuditEvent.resource_id == "target",
            ))
            self.assertIsNotNone(event)
            self.assertEqual(event.reason, "updated_system_role")

    def test_last_active_admin_cannot_be_demoted_and_inactive_admin_does_not_count(self):
        response = self.client.patch("/admin/users/actor", headers=self.headers,
                                     json={"system_role": "user"})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "last_active_admin")
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        with self.factory() as db:
            self.assertEqual(db.get(User, "actor").system_role, "admin")
            db.get(User, "target").system_role = "admin"
            db.commit()
        demote = self.client.patch("/admin/users/target", headers=self.headers,
                                   json={"system_role": "user"})
        self.assertEqual(demote.status_code, 200, demote.text)
        with self.factory() as db:
            self.assertEqual(db.get(User, "inactive-admin").system_role, "admin")
            self.assertFalse(db.get(User, "inactive-admin").is_active)

    def test_self_demotion_keeps_authenticated_session_and_removes_admin_access(self):
        with self.factory() as db:
            db.get(User, "target").system_role = "admin"
            db.commit()
        session_cookie = self.client.cookies.get("ruvie_session")
        changed = self.client.patch("/admin/users/actor", headers=self.headers,
                                    json={"system_role": "user"})
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(self.client.cookies.get("ruvie_session"), session_cookie)
        session = self.client.get("/auth/session")
        self.assertEqual(session.status_code, 200, session.text)
        self.assertEqual(session.json()["user"]["system_role"], "user")
        self.assertEqual(self.client.get("/admin/users/target").status_code, 403)


class AdminRolePostgresConcurrencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.F005007EndToEndTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.F005007EndToEndTests.tearDownClass()

    def test_concurrent_cross_demotions_leave_one_active_admin(self):
        fixture = fixtures.F005007EndToEndTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        factory = fixture.client.app.state.session_factory
        with factory() as db:
            for identity, email in (("alpha", "alpha@example.test"),
                                    ("beta", "beta@example.test")):
                account = db.get(User, identity)
                account.email = email
                account.system_role = "admin"
                account.is_active = True
            db.commit()
        barrier = Barrier(2)

        def demote(actor_id, target_id):
            barrier.wait(timeout=10)
            with factory() as db:
                try:
                    AdminAccountService(db).update_account(
                        actor_id, target_id, UpdateAccountRequest(system_role="user"),
                    )
                    return "updated"
                except AdminRequired:
                    return "denied"

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda pair: demote(*pair), (("alpha", "beta"), ("beta", "alpha"))))
        self.assertCountEqual(outcomes, ["updated", "denied"])
        with factory() as db:
            active_admins = db.scalar(select(User).where(
                User.system_role == "admin", User.is_active.is_(True),
            ).with_only_columns(User.id))
            self.assertIsNotNone(active_admins)
            self.assertEqual(db.query(User).filter_by(system_role="admin", is_active=True).count(), 1)


if __name__ == "__main__":
    unittest.main()
