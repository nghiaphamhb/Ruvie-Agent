"""F012-004: admin account use cases, PostgreSQL races and permission isolation."""
from concurrent.futures import ThreadPoolExecutor
import importlib
import importlib.util
import threading
import time
import unittest
from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import test_f005_007_e2e as fixtures
from ruvie.contracts.admin import CreateAccountRequest
from ruvie.models import AccessGrant, AuditEvent, AuthSession, Base, Document, Membership, User
from ruvie.services.access import DocumentAccessService
from ruvie.services.audit import AuditEventWriter
from ruvie.services.auth import AuthService, hash_password, verify_password

PASSWORD = " account-test-password "


class AccountHelpers:
    def load_admin_service(self):
        self.assertIsNotNone(importlib.util.find_spec("ruvie.services.admin"),
                             "Admin account use cases must have a service")
        self.admin = importlib.import_module("ruvie.services.admin")

    def command(self, **changes):
        return CreateAccountRequest(**{
            "display_name": " New Person ", "email": " NEW@Example.test ",
            "password": PASSWORD, **changes,
        })


class AdminAccountServiceTests(AccountHelpers, unittest.TestCase):
    def setUp(self):
        self.load_admin_service()
        self.engine = create_engine("sqlite://", poolclass=StaticPool,
                                    connect_args={"check_same_thread": False})
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine)
        self.db = self.factory()
        self.addCleanup(self.db.close)
        self.db.add(User(id="actor", email="actor@example.test", display_name="Actor",
                         system_role="admin", password_hash=hash_password("actor-password")))
        self.db.commit()
        self.service = self.admin.AdminAccountService(self.db)

    def test_default_user_has_safe_metadata_audit_and_no_new_session_or_grants(self):
        session = AuthService(self.db).create_session("actor")
        result = self.service.create_account("actor", self.command())
        self.assertEqual(result.user.model_dump(), {
            "id": result.user.id, "display_name": "New Person", "email": "new@example.test",
            "system_role": "user", "is_active": True, "created_at": result.user.created_at,
        })
        with self.factory() as fresh:
            user = fresh.get(User, result.user.id)
            self.assertTrue(verify_password(PASSWORD, user.password_hash))
            self.assertFalse(verify_password(PASSWORD.strip(), user.password_hash))
            self.assertEqual(fresh.query(AuthSession).count(), 1)
            self.assertEqual(fresh.query(Membership).count(), 0)
            self.assertEqual(fresh.query(AccessGrant).count(), 0)
            event = fresh.scalar(select(AuditEvent))
            self.assertEqual(fresh.query(AuditEvent).count(), 1)
            self.assertEqual((event.actor_user_id, event.resource_id, event.resource_type,
                              event.action, event.outcome, event.reason, event.project_id),
                             ("actor", user.id, "user", "account.create", "allow", "created_as_user", None))
            for secret in (PASSWORD, user.password_hash, session.token, session.csrf_token):
                self.assertNotIn(secret, repr(result))
                self.assertNotIn(secret, repr(event.__dict__))
        resolved = AuthService(self.db).resolve_session(session.token)
        self.assertEqual((resolved.user.id, resolved.csrf_token), ("actor", session.csrf_token))
        self.assertIsNotNone(AuthService(self.db).authenticate("NEW@example.test", PASSWORD))

    def test_created_admin_can_create_user_and_admin_without_receiving_a_session(self):
        created = self.service.create_account("actor", self.command(system_role="admin"))
        self.assertEqual(created.user.system_role, "admin")
        for role in ("user", "admin"):
            child = self.service.create_account(created.user.id, self.command(
                email=f"child-{role}@example.test", system_role=role))
            self.assertEqual(child.user.system_role, role)
        self.assertEqual(self.db.query(AuthSession).count(), 0)
        self.assertEqual([event.reason for event in self.db.scalars(select(AuditEvent))],
                         ["created_as_admin", "created_as_user", "created_as_admin"])

    def test_missing_inactive_and_ordinary_actors_cannot_create_or_lookup(self):
        for actor_id, active, role, error_name in (
            ("missing", True, "admin", "AuthenticationRequired"),
            ("actor", False, "admin", "AuthenticationRequired"),
            ("actor", True, "user", "AdminRequired"),
        ):
            with self.subTest(actor=actor_id, active=active, role=role):
                actor = self.db.get(User, "actor")
                actor.is_active, actor.system_role = active, role
                self.db.commit()
                error = getattr(self.admin, error_name)
                with self.assertRaises(error):
                    self.service.create_account(actor_id, self.command(system_role="admin"))
                with self.assertRaises(error):
                    self.service.lookup_account(actor_id, "actor@example.test")
                self.assertEqual(self.db.query(User).count(), 1)
                self.assertEqual(self.db.query(AuditEvent).count(), 0)

    def test_cached_role_and_activity_are_reloaded_before_authorization(self):
        cached_actor = self.service.require_admin("actor")
        with self.factory() as other:
            other.get(User, "actor").system_role = "user"
            other.commit()
        self.assertEqual(cached_actor.system_role, "admin")
        with self.assertRaises(self.admin.AdminRequired):
            self.service.create_account("actor", self.command())
        with self.factory() as other:
            actor = other.get(User, "actor")
            actor.system_role, actor.is_active = "admin", False
            other.commit()
        with self.assertRaises(self.admin.AuthenticationRequired):
            self.service.lookup_account("actor", "actor@example.test")

    def test_duplicate_inactive_email_preserves_password_role_and_state(self):
        created = self.service.create_account("actor", self.command())
        existing = self.db.get(User, created.user.id)
        existing.is_active = False
        self.db.commit()
        before = (existing.password_hash, existing.system_role, existing.display_name)
        with self.assertRaises(self.admin.EmailTaken):
            self.service.create_account("actor", self.command(
                email="NEW@example.test", password="replacement-password", system_role="admin"))
        existing = self.db.get(User, created.user.id)
        self.assertEqual((existing.password_hash, existing.system_role, existing.display_name), before)
        self.assertFalse(existing.is_active)
        self.assertEqual(self.db.query(User).count(), 2)
        self.assertEqual(self.db.query(AuditEvent).count(), 1)

    def test_lookup_normalizes_exact_email_and_returns_inactive_safe_summary(self):
        created = self.service.create_account("actor", self.command())
        self.db.get(User, created.user.id).is_active = False
        self.db.commit()
        found = self.service.lookup_account("actor", " NEW@Example.test ")
        self.assertEqual(found.model_dump(), {"users": [{
            "id": created.user.id, "display_name": "New Person", "email": "new@example.test",
            "system_role": "user", "is_active": False, "created_at": created.user.created_at,
        }]})
        for email in ("absent@example.test", "%@example.test", "new-other@example.test"):
            self.assertEqual(self.service.lookup_account("actor", email).model_dump(), {"users": []})
        self.assertEqual(self.db.query(AuthSession).count(), 0)
        self.assertEqual(self.db.query(AuditEvent).count(), 1)

    def test_lookup_rejects_invalid_missing_and_non_string_email(self):
        for email in (None, 42, "", " ", "new", "new@example.test trailing", "x" * 321):
            with self.subTest(email=email), self.assertRaises(ValidationError):
                self.service.lookup_account("actor", email)

    def test_lookup_refreshes_cached_recipient_metadata_from_the_database(self):
        created = self.service.create_account("actor", self.command())
        cached_user = self.db.get(User, created.user.id)
        with self.factory() as other:
            updated = other.get(User, created.user.id)
            updated.system_role, updated.is_active = "admin", False
            other.commit()
        self.assertEqual((cached_user.system_role, cached_user.is_active), ("user", True))
        found = self.service.lookup_account("actor", "new@example.test")
        self.assertEqual((found.users[0].system_role, found.users[0].is_active), ("admin", False))

    def test_create_revalidates_a_command_instead_of_trusting_constructed_models(self):
        for field, value in (("system_role", "owner"), ("password", "short"), ("display_name", " ")):
            command = self.command()
            setattr(command, field, value)
            with self.subTest(field=field), self.assertRaises(ValidationError):
                self.service.create_account("actor", command)
        self.assertEqual(self.db.query(User).count(), 1)
        self.assertEqual(self.db.query(AuditEvent).count(), 0)

    def test_hash_failure_creates_no_account_or_audit(self):
        with patch.object(self.admin, "hash_password", side_effect=RuntimeError(PASSWORD)):
            with self.assertRaises(RuntimeError):
                self.service.create_account("actor", self.command())
        self.assertEqual(self.db.query(User).count(), 1)
        self.assertEqual(self.db.query(AuditEvent).count(), 0)

    def test_non_email_constraint_failure_is_not_reported_as_email_taken(self):
        self.db.add(User(id="collision", display_name="Collision", email="collision@example.test"))
        self.db.commit()
        self.db.expunge_all()
        with patch.object(self.admin, "uuid4", return_value="collision"):
            with self.assertRaises(IntegrityError):
                self.service.create_account("actor", self.command())
        self.assertEqual(self.db.query(User).count(), 2)
        self.assertEqual(self.db.query(AuditEvent).count(), 0)


class AdminAccountPostgresTests(AccountHelpers, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.F005007EndToEndTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.F005007EndToEndTests.tearDownClass()

    def setUp(self):
        self.load_admin_service()
        self.fixture = fixtures.F005007EndToEndTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.factory = self.fixture.client.app.state.session_factory
        with self.factory() as db:
            for actor_id in ("alpha", "beta"):
                db.get(User, actor_id).system_role = "admin"
            db.commit()

    def test_two_admins_racing_on_case_variant_email_create_one_account_and_one_audit(self):
        barrier = threading.Barrier(2)

        def synchronized_hash(password):
            # Both independent actors pass the email precheck before either inserts.
            barrier.wait(timeout=10)
            return hash_password(password)

        def create(actor_id, email):
            with self.factory() as db:
                try:
                    result = self.admin.AdminAccountService(db).create_account(
                        actor_id, self.command(email=email))
                    return "created", result.user.id
                except self.admin.EmailTaken:
                    return "email_taken", None

        with patch.object(self.admin, "hash_password", side_effect=synchronized_hash):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(create, "alpha", "Race@example.test")
                second = pool.submit(create, "beta", "race@EXAMPLE.test")
                results = [first.result(timeout=20), second.result(timeout=20)]
        self.assertEqual(sorted(outcome for outcome, _ in results), ["created", "email_taken"])
        with self.factory() as db:
            users = list(db.scalars(select(User).where(User.email == "race@example.test")))
            self.assertEqual(len(users), 1)
            self.assertEqual(db.query(AuditEvent).filter_by(resource_id=users[0].id).count(), 1)
            self.assertEqual(db.query(AuthSession).count(), 0)

    def test_pending_demotion_is_observed_after_waiting_for_actor_row_lock(self):
        blocker = self.factory()
        self.addCleanup(blocker.close)
        blocker.get(User, "alpha").system_role = "user"
        blocker.flush()
        started = threading.Event()

        def create():
            with self.factory() as db:
                started.set()
                return self.admin.AdminAccountService(db).create_account("alpha", self.command())

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(create)
            try:
                self.assertTrue(started.wait(timeout=5))
                deadline = time.monotonic() + 5
                waiting = False
                while time.monotonic() < deadline and not future.done():
                    with self.fixture.client.app.state.engine.connect() as connection:
                        waiting = connection.scalar(text(
                            "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                            "WHERE datname = current_database() AND wait_event_type = 'Lock' "
                            "AND query ILIKE '%FOR UPDATE%')"
                        ))
                    if waiting:
                        break
                    time.sleep(0.02)
                self.assertTrue(waiting, "Creation must wait on the actor's uncommitted role change")
            finally:
                blocker.commit()
            with self.assertRaises(self.admin.AdminRequired):
                future.result(timeout=10)
        with self.factory() as db:
            self.assertIsNone(db.scalar(select(User).where(User.email == "new@example.test")))
            self.assertEqual(db.query(AuditEvent).count(), 0)

    def test_audit_failure_rolls_back_flushed_account_and_event(self):
        append = AuditEventWriter.append

        def fail(*args, **kwargs):
            append(*args, **kwargs)
            raise SQLAlchemyError(PASSWORD)

        with self.factory() as db:
            with patch.object(AuditEventWriter, "append", side_effect=fail):
                with self.assertRaises(SQLAlchemyError):
                    self.admin.AdminAccountService(db).create_account("alpha", self.command())
        with self.factory() as db:
            self.assertIsNone(db.scalar(select(User).where(User.email == "new@example.test")))
            self.assertEqual(db.query(AuditEvent).count(), 0)
            self.assertEqual(db.query(AuthSession).count(), 0)

    def test_commit_failure_rolls_back_account_and_audit_without_revoking_existing_session(self):
        with self.factory() as db:
            existing = AuthService(db).create_session("alpha")

            def fail():
                db.flush()
                raise SQLAlchemyError(PASSWORD)

            with patch.object(db, "commit", side_effect=fail):
                with self.assertRaises(SQLAlchemyError):
                    self.admin.AdminAccountService(db).create_account("alpha", self.command())
        with self.factory() as db:
            self.assertIsNone(db.scalar(select(User).where(User.email == "new@example.test")))
            self.assertEqual(db.query(AuditEvent).count(), 0)
            resolved = AuthService(db).resolve_session(existing.token)
            self.assertEqual((resolved.user.id, resolved.csrf_token), ("alpha", existing.csrf_token))
            self.assertEqual(db.query(AuthSession).count(), 1)

    def test_both_new_roles_have_no_membership_or_private_document_access(self):
        csrf, _ = self.fixture._login("alpha@example.test")
        uploaded = self.fixture._upload(csrf, "project-alpha", "Private", b"ADMIN_PRIVATE_GUIDE")
        self.assertEqual(uploaded.status_code, 202, uploaded.text)
        with self.factory() as db:
            document = db.scalar(select(Document))
            for role in ("user", "admin"):
                created = self.admin.AdminAccountService(db).create_account("alpha", self.command(
                    email=f"new-{role}@example.test", system_role=role))
                self.assertEqual(db.query(Membership).filter_by(user_id=created.user.id).count(), 0)
                self.assertEqual(db.query(AccessGrant).filter_by(principal_id=created.user.id).count(), 0)
                self.assertFalse(DocumentAccessService.can_read_document(db, created.user.id, document.id))
                self.assertIsNotNone(AuthService(db).authenticate(created.user.email, PASSWORD))


if __name__ == "__main__":
    unittest.main()
