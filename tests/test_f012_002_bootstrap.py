"""F012-003: real PostgreSQL bootstrap, concurrency and atomic failure handling."""
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import test_f005_007_e2e as fixtures
from ruvie.models import AccessGrant, AuditEvent, AuthSession, Membership, User
from ruvie.services.audit import AuditEventWriter
from ruvie.services.auth import AuthService, verify_password

PASSWORD = " bootstrap-test-password "


class BootstrapPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.F005007EndToEndTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.F005007EndToEndTests.tearDownClass()

    def setUp(self):
        self.fixture = fixtures.F005007EndToEndTests()
        # Each test gets its own migrated database, with no seeded accounts.
        with patch.object(self.fixture, "_seed_accounts"):
            self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.client = self.fixture.client
        self.factory = self.client.app.state.session_factory

    def register(self, client=None, email=" FIRST@Example.test "):
        return (client or self.client).post("/auth/register", headers={"Origin": fixtures.ORIGIN},
            json={"display_name": " First Admin ", "email": email, "password": PASSWORD})

    def assert_empty(self):
        with self.factory() as db:
            for model in (User, AuthSession, AuditEvent, Membership, AccessGrant):
                self.assertEqual(db.query(model).count(), 0, model.__name__)

    def test_setup_reads_empty_database_without_creating_a_session(self):
        response = self.client.get("/auth/setup")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"requires_initial_admin": True})
        self.assertNotIn("set-cookie", response.headers)
        self.assert_empty()

    def check_existing_account_closes_bootstrap(self, role, active):
        with self.factory() as db:
            db.add(User(id="existing", display_name="Existing", email="existing@example.test",
                        system_role=role, is_active=active, password_hash="unchanged"))
            db.commit()
        self.assertEqual(self.client.get("/auth/setup").json(), {"requires_initial_admin": False})
        for email in ("existing@example.test", "different@example.test"):
            response = self.register(email=email)
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(response.json(), {"detail": {"code": "setup_already_completed"}})
            self.assertNotIn("set-cookie", response.headers)
        with self.factory() as db:
            user = db.get(User, "existing")
            self.assertEqual((user.system_role, user.is_active, user.password_hash),
                             (role, active, "unchanged"))
            self.assertEqual(db.query(User).count(), 1)
            self.assertEqual(db.query(AuthSession).count(), 0)
            self.assertEqual(db.query(AuditEvent).count(), 0)

    def test_active_ordinary_user_closes_bootstrap(self):
        self.check_existing_account_closes_bootstrap("user", True)

    def test_inactive_ordinary_user_closes_bootstrap(self):
        self.check_existing_account_closes_bootstrap("user", False)

    def test_active_admin_closes_bootstrap(self):
        self.check_existing_account_closes_bootstrap("admin", True)

    def test_inactive_admin_closes_bootstrap(self):
        self.check_existing_account_closes_bootstrap("admin", False)

    def test_bootstrap_creates_admin_session_and_safe_audit_without_access_grants(self):
        response = self.register()
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["user"]["system_role"], "admin")
        self.assertEqual(response.json()["user"]["display_name"], "First Admin")
        self.assertEqual(self.client.get("/auth/session").json(), response.json())
        self.assertEqual(self.client.get("/auth/setup").json(), {"requires_initial_admin": False})
        with self.factory() as db:
            user = db.scalar(select(User))
            self.assertEqual(user.email, "first@example.test")
            self.assertTrue(user.is_active)
            self.assertTrue(verify_password(PASSWORD, user.password_hash))
            self.assertFalse(verify_password(PASSWORD.strip(), user.password_hash))
            self.assertEqual(db.query(User).count(), 1)
            self.assertEqual(db.query(AuthSession).count(), 1)
            self.assertEqual(db.query(AuditEvent).count(), 1)
            audit = db.scalar(select(AuditEvent))
            self.assertEqual((audit.actor_user_id, audit.action, audit.resource_type, audit.resource_id,
                              audit.outcome, audit.reason, audit.project_id),
                             (user.id, "account.bootstrap", "user", user.id,
                              "allow", "created_as_admin", None))
            for secret in (PASSWORD, user.password_hash, response.json()["csrf_token"],
                           self.client.cookies["ruvie_session"]):
                self.assertNotIn(secret, repr(audit.__dict__))
            self.assertEqual(db.query(Membership).count(), 0)
            self.assertEqual(db.query(AccessGrant).count(), 0)
        cookie = response.headers["set-cookie"].lower()
        for attribute in ("httponly", "secure", "samesite=lax", "path=/", "max-age=43200"):
            self.assertIn(attribute, cookie)

    def test_logout_new_browser_and_login_do_not_reopen_bootstrap_or_replace_session(self):
        created = self.register()
        self.assertEqual(created.status_code, 201, created.text)
        token = self.client.cookies["ruvie_session"]
        blocked = self.register(email="second@example.test")
        self.assertEqual(blocked.status_code, 409)
        self.assertNotIn("set-cookie", blocked.headers)
        self.assertEqual(self.client.cookies["ruvie_session"], token)
        self.assertEqual(self.client.get("/auth/session").json(), created.json())
        self.assertEqual(self.client.post("/auth/logout", headers={
            "Origin": fixtures.ORIGIN, "X-CSRF-Token": created.json()["csrf_token"],
        }).status_code, 204)
        browser = TestClient(self.client.app, base_url=fixtures.ORIGIN)
        self.addCleanup(browser.close)
        self.assertEqual(browser.get("/auth/setup").json(), {"requires_initial_admin": False})
        self.assertEqual(self.register(browser).status_code, 409)
        login = browser.post("/auth/login", headers={"Origin": fixtures.ORIGIN},
                             json={"email": "first@example.test", "password": PASSWORD})
        self.assertEqual(login.status_code, 200, login.text)
        self.assertEqual(login.json()["user"]["system_role"], "admin")

    def test_setup_database_failure_returns_unavailable_without_private_error(self):
        # Fail the real DB boundary rather than inventing a setup result.
        with patch.object(Session, "scalar", side_effect=SQLAlchemyError(PASSWORD)):
            response = self.client.get("/auth/setup")
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json(), {"detail": {"code": "setup_unavailable"}})
        self.assertNotIn(PASSWORD, response.text)
        self.assertNotIn("set-cookie", response.headers)
        self.assert_empty()

    def test_different_emails_in_concurrent_requests_create_only_one_admin_and_session(self):
        barrier = threading.Barrier(4)

        def submit(index):
            # Separate clients/connections exercise a real PostgreSQL race.
            browser = TestClient(self.client.app, base_url=fixtures.ORIGIN)
            try:
                barrier.wait(timeout=10)
                response = self.register(browser, email=f"person{index}@example.test")
                return response.status_code, response.json(), "set-cookie" in response.headers
            finally:
                browser.close()

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(submit, range(4)))
        self.assertEqual(sorted(status for status, _, _ in results), [201, 409, 409, 409], results)
        for status, body, has_cookie in results:
            self.assertEqual(has_cookie, status == 201)
            if status == 409:
                self.assertEqual(body, {"detail": {"code": "setup_already_completed"}})
        with self.factory() as db:
            self.assertEqual(db.query(User).count(), 1)
            self.assertEqual(db.scalar(select(User)).system_role, "admin")
            self.assertEqual(db.query(AuthSession).count(), 1)
            self.assertEqual(db.query(AuditEvent).count(), 1)

    def check_rollback(self, target, method, failure):
        with patch.object(target, method, side_effect=failure):
            response = self.register()
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(response.json(), {"detail": {"code": "account_creation_failed"}})
        self.assertNotIn(PASSWORD, response.text)
        self.assertNotIn("set-cookie", response.headers)
        self.assert_empty()
        self.assertEqual(self.client.get("/auth/setup").json(), {"requires_initial_admin": True})
        # Rollback must also release the bootstrap lock so a later request can succeed.
        retried = self.register()
        self.assertEqual(retried.status_code, 201, retried.text)

    def test_hash_failure_rolls_back_and_releases_bootstrap(self):
        import ruvie.services.auth as auth_module
        self.check_rollback(auth_module, "hash_password", RuntimeError(PASSWORD))

    def test_session_failure_rolls_back_staged_user_and_session(self):
        stage = AuthService._stage_session

        def fail(service, user_id):
            stage(service, user_id)
            service.session.flush()
            raise RuntimeError(PASSWORD)

        # autospec binds the service instance when injecting a failure after staging.
        with patch.object(AuthService, "_stage_session", autospec=True, side_effect=fail):
            response = self.register()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": {"code": "account_creation_failed"}})
        self.assertNotIn("set-cookie", response.headers)
        self.assertNotIn(PASSWORD, response.text)
        self.assert_empty()
        self.assertEqual(self.register().status_code, 201)

    def test_audit_failure_rolls_back_already_flushed_account_session_and_audit(self):
        append = AuditEventWriter.append

        def fail(*args, **kwargs):
            append(*args, **kwargs)
            raise SQLAlchemyError(PASSWORD)

        self.check_rollback(AuditEventWriter, "append", fail)

    def test_commit_failure_rolls_back_all_flushed_bootstrap_records(self):
        def fail(db):
            db.flush()
            raise SQLAlchemyError(PASSWORD)

        with patch.object(Session, "commit", autospec=True, side_effect=fail):
            response = self.register()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": {"code": "account_creation_failed"}})
        self.assertNotIn(PASSWORD, response.text)
        self.assertNotIn("set-cookie", response.headers)
        self.assert_empty()
        self.assertEqual(self.register().status_code, 201)


if __name__ == "__main__":
    unittest.main()
