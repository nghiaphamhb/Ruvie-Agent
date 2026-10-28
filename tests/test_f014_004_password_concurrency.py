"""PostgreSQL proves concurrent self-service changes serialize on the account row."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import threading
import time
import unittest
from unittest.mock import patch

from sqlalchemy import select, text
from sqlalchemy.orm import Session

import test_f005_007_e2e as fixtures
from ruvie.models import AuditEvent, AuthSession, User
from ruvie.services.audit import AuditEventWriter
from ruvie.services import auth as auth_module
from ruvie.services.auth import AuthService, PasswordChangeError, hash_password, verify_password
from ruvie.contracts.auth import ChangePasswordRequest
from ruvie.contracts.admin import UpdateAccountRequest


OLD_PASSWORD = " concurrency-old-password "
FIRST_PASSWORD = " concurrency-new-password-one "
SECOND_PASSWORD = " concurrency-new-password-two "
RESET_PASSWORD = " concurrency-admin-reset-password "


class PasswordChangeConcurrencyTests(unittest.TestCase):
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
            db.get(User, "alpha").password_hash = hash_password(OLD_PASSWORD)
            db.commit()
            self.first = AuthService(db).create_session("alpha")
            self.second = AuthService(db).create_session("alpha")

    @staticmethod
    def command(new_password):
        return ChangePasswordRequest(
            current_password=OLD_PASSWORD,
            new_password=new_password,
            password_confirmation=new_password,
        )

    def wait_for_user_lock(self, future, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not future.done():
            with self.fixture.client.app.state.engine.connect() as connection:
                waiting = connection.scalar(text(
                    "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                    "WHERE datname = current_database() AND wait_event_type = 'Lock' "
                    "AND query ILIKE '%FOR UPDATE%')"
                ))
            if waiting:
                return True
            time.sleep(0.02)
        return False

    def test_two_sessions_racing_with_old_password_allow_exactly_one_change(self):
        first_hash_started = threading.Event()
        second_started = threading.Event()
        release_first = threading.Event()
        original_hash = auth_module.hash_password

        def pause_first_hash(password):
            if password == FIRST_PASSWORD:
                first_hash_started.set()
                if not release_first.wait(timeout=10):
                    raise TimeoutError("test did not release first password hash")
            return original_hash(password)

        def change(token, password, started=None):
            if started:
                started.set()
            try:
                with self.factory() as db:
                    AuthService(db).change_password("alpha", token, self.command(password))
                return "success"
            except PasswordChangeError as error:
                return error.code

        with patch.object(auth_module, "hash_password", side_effect=pause_first_hash):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(change, self.first.token, FIRST_PASSWORD)
                second = None
                try:
                    self.assertTrue(first_hash_started.wait(timeout=5))
                    second = pool.submit(change, self.second.token, SECOND_PASSWORD, second_started)
                    self.assertTrue(second_started.wait(timeout=5))

                    self.assertTrue(
                        self.wait_for_user_lock(second),
                        "second change must wait for the actor row lock",
                    )
                finally:
                    release_first.set()

                self.assertEqual(first.result(timeout=10), "success")
                self.assertEqual(second.result(timeout=10), "authentication_required")

        with self.factory() as db:
            self.assertTrue(verify_password(FIRST_PASSWORD, db.get(User, "alpha").password_hash))
            rows = list(db.scalars(select(AuthSession).where(AuthSession.user_id == "alpha")))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].token_hash, hashlib.sha256(
                self.first.token.encode()
            ).hexdigest())
            events = list(db.scalars(select(AuditEvent).where(
                AuditEvent.action == "account.password_change", AuditEvent.resource_id == "alpha",
            )))
            self.assertEqual(len(events), 1)

    def test_same_session_requests_serialize_and_old_password_loses_after_first_commit(self):
        first_hash_started = threading.Event()
        second_started = threading.Event()
        release_first = threading.Event()
        original_hash = auth_module.hash_password

        def pause_first_hash(password):
            if password == FIRST_PASSWORD:
                first_hash_started.set()
                if not release_first.wait(timeout=10):
                    raise TimeoutError("test did not release first password hash")
            return original_hash(password)

        def change(password, started=None):
            if started:
                started.set()
            try:
                with self.factory() as db:
                    AuthService(db).change_password("alpha", self.first.token, self.command(password))
                return "success"
            except PasswordChangeError as error:
                return error.code

        with patch.object(auth_module, "hash_password", side_effect=pause_first_hash):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(change, FIRST_PASSWORD)
                second = None
                try:
                    self.assertTrue(first_hash_started.wait(timeout=5))
                    second = pool.submit(change, SECOND_PASSWORD, second_started)
                    self.assertTrue(second_started.wait(timeout=5))
                    self.assertTrue(self.wait_for_user_lock(second))
                finally:
                    release_first.set()
                self.assertEqual(first.result(timeout=10), "success")
                self.assertEqual(second.result(timeout=10), "current_password_incorrect")
        with self.factory() as db:
            self.assertTrue(verify_password(FIRST_PASSWORD, db.get(User, "alpha").password_hash))
            self.assertEqual(db.query(AuthSession).filter_by(user_id="alpha").count(), 1)
            self.assertEqual(db.query(AuditEvent).filter_by(action="account.password_change").count(), 1)

    def test_login_before_change_is_revoked_and_login_after_change_rejects_old_password(self):
        with self.factory() as db:
            user = AuthService(db).authenticate("alpha@example.test", OLD_PASSWORD)
            self.assertIsNotNone(user)
            logged_in = AuthService(db).create_session(user.id)
        with self.factory() as db:
            AuthService(db).change_password("alpha", self.first.token, self.command(FIRST_PASSWORD))
        with self.factory() as db:
            self.assertEqual(db.scalar(select(AuthSession.id).where(
                AuthSession.token_hash == hashlib.sha256(logged_in.token.encode()).hexdigest()
            )), None)
            self.assertEqual(db.query(AuthSession).filter_by(user_id="alpha").count(), 1)
            self.assertIsNone(AuthService(db).authenticate("alpha@example.test", OLD_PASSWORD))
            self.assertTrue(verify_password(FIRST_PASSWORD, db.get(User, "alpha").password_hash))

    def test_login_holding_user_lock_finishes_before_change_and_its_session_is_revoked(self):
        login_verify_started = threading.Event()
        change_started = threading.Event()
        release_login = threading.Event()
        login_thread_id = None
        original_verify = auth_module.verify_password

        def pause_login_verify(password, encoded):
            if threading.get_ident() == login_thread_id:
                login_verify_started.set()
                if not release_login.wait(timeout=10):
                    raise TimeoutError("test did not release login verification")
            return original_verify(password, encoded)

        def login():
            nonlocal login_thread_id
            login_thread_id = threading.get_ident()
            with self.factory() as db:
                user = AuthService(db).authenticate("alpha@example.test", OLD_PASSWORD)
                return AuthService(db).create_session(user.id) if user else None

        def change():
            change_started.set()
            with self.factory() as db:
                return AuthService(db).change_password("alpha", self.first.token, self.command(FIRST_PASSWORD))

        with patch.object(auth_module, "verify_password", side_effect=pause_login_verify):
            with ThreadPoolExecutor(max_workers=2) as pool:
                login_future = pool.submit(login)
                change_future = None
                try:
                    self.assertTrue(login_verify_started.wait(timeout=5))
                    change_future = pool.submit(change)
                    self.assertTrue(change_started.wait(timeout=5))
                    self.assertTrue(self.wait_for_user_lock(change_future))
                finally:
                    release_login.set()
                logged_in = login_future.result(timeout=10)
                change_future.result(timeout=10)
        with self.factory() as db:
            self.assertEqual(db.scalar(select(AuthSession.id).where(
                AuthSession.token_hash == hashlib.sha256(logged_in.token.encode()).hexdigest()
            )), None)
            self.assertEqual(db.query(AuthSession).filter_by(user_id="alpha").count(), 1)
            self.assertTrue(verify_password(FIRST_PASSWORD, db.get(User, "alpha").password_hash))

    def test_change_holding_user_lock_makes_old_password_login_fail(self):
        change_hash_started = threading.Event()
        login_started = threading.Event()
        release_change = threading.Event()
        original_hash = auth_module.hash_password

        def pause_change_hash(password):
            if password == FIRST_PASSWORD:
                change_hash_started.set()
                if not release_change.wait(timeout=10):
                    raise TimeoutError("test did not release password change")
            return original_hash(password)

        def change():
            with self.factory() as db:
                AuthService(db).change_password("alpha", self.first.token, self.command(FIRST_PASSWORD))

        def login():
            login_started.set()
            with self.factory() as db:
                user = AuthService(db).authenticate("alpha@example.test", OLD_PASSWORD)
                return AuthService(db).create_session(user.id) if user else None

        with patch.object(auth_module, "hash_password", side_effect=pause_change_hash):
            with ThreadPoolExecutor(max_workers=2) as pool:
                change_future = pool.submit(change)
                login_future = None
                try:
                    self.assertTrue(change_hash_started.wait(timeout=5))
                    login_future = pool.submit(login)
                    self.assertTrue(login_started.wait(timeout=5))
                    self.assertTrue(self.wait_for_user_lock(login_future))
                finally:
                    release_change.set()
                change_future.result(timeout=10)
                self.assertIsNone(login_future.result(timeout=10))
        with self.factory() as db:
            self.assertEqual(db.query(AuthSession).filter_by(user_id="alpha").count(), 1)
            self.assertTrue(verify_password(FIRST_PASSWORD, db.get(User, "alpha").password_hash))

    def test_admin_reset_winning_after_change_revokes_retained_session_and_overwrites_hash(self):
        from ruvie.services.admin import AdminAccountService

        with self.factory() as db:
            db.add(User(
                id="reset-admin", email="reset-admin@example.test", display_name="Reset admin",
                password_hash=hash_password("reset-admin-password"), system_role="admin", is_active=True,
            ))
            db.commit()
        change_hash_started = threading.Event()
        reset_started = threading.Event()
        release_change = threading.Event()
        original_hash = auth_module.hash_password

        def pause_change_hash(password):
            if password == FIRST_PASSWORD:
                change_hash_started.set()
                if not release_change.wait(timeout=10):
                    raise TimeoutError("test did not release password change")
            return original_hash(password)

        def change():
            with self.factory() as db:
                AuthService(db).change_password("alpha", self.first.token, self.command(FIRST_PASSWORD))

        def reset():
            reset_started.set()
            with self.factory() as db:
                AdminAccountService(db).update_account(
                    "reset-admin", "alpha", UpdateAccountRequest(password=RESET_PASSWORD),
                )

        with patch.object(auth_module, "hash_password", side_effect=pause_change_hash):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(change)
                second = None
                try:
                    self.assertTrue(change_hash_started.wait(timeout=5))
                    second = pool.submit(reset)
                    self.assertTrue(reset_started.wait(timeout=5))
                    self.assertTrue(self.wait_for_user_lock(second))
                finally:
                    release_change.set()
                first.result(timeout=10)
                second.result(timeout=10)
        with self.factory() as db:
            self.assertTrue(verify_password(RESET_PASSWORD, db.get(User, "alpha").password_hash))
            self.assertEqual(db.query(AuthSession).filter_by(user_id="alpha").count(), 0)
            self.assertEqual(db.query(AuditEvent).filter_by(action="account.password_change").count(), 1)
            self.assertEqual(db.query(AuditEvent).filter_by(action="account.update").count(), 1)

    def test_admin_reset_winning_first_makes_waiting_change_reject_revoked_session(self):
        from ruvie.services.admin import AdminAccountService

        with self.factory() as db:
            db.add(User(
                id="reset-admin", email="reset-admin@example.test", display_name="Reset admin",
                password_hash=hash_password("reset-admin-password"), system_role="admin", is_active=True,
            ))
            db.commit()
        from ruvie.services import admin as admin_module

        reset_hash_started = threading.Event()
        change_started = threading.Event()
        release_reset = threading.Event()
        original_hash = admin_module.hash_password

        def pause_reset_hash(password):
            if password == RESET_PASSWORD:
                reset_hash_started.set()
                if not release_reset.wait(timeout=10):
                    raise TimeoutError("test did not release admin reset")
            return original_hash(password)

        def reset():
            with self.factory() as db:
                AdminAccountService(db).update_account(
                    "reset-admin", "alpha", UpdateAccountRequest(password=RESET_PASSWORD),
                )

        def change():
            change_started.set()
            try:
                with self.factory() as db:
                    AuthService(db).change_password("alpha", self.first.token, self.command(FIRST_PASSWORD))
                return "success"
            except PasswordChangeError as error:
                return error.code

        with patch.object(admin_module, "hash_password", side_effect=pause_reset_hash):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(reset)
                second = None
                try:
                    self.assertTrue(reset_hash_started.wait(timeout=5))
                    second = pool.submit(change)
                    self.assertTrue(change_started.wait(timeout=5))
                    self.assertTrue(self.wait_for_user_lock(second))
                finally:
                    release_reset.set()
                first.result(timeout=10)
                self.assertEqual(second.result(timeout=10), "authentication_required")
        with self.factory() as db:
            self.assertTrue(verify_password(RESET_PASSWORD, db.get(User, "alpha").password_hash))
            self.assertEqual(db.query(AuthSession).filter_by(user_id="alpha").count(), 0)
            self.assertEqual(db.query(AuditEvent).filter_by(action="account.password_change").count(), 0)
            self.assertEqual(db.query(AuditEvent).filter_by(action="account.update").count(), 1)

    def test_revoked_session_while_waiting_for_user_lock_is_rechecked(self):
        lock_acquired = threading.Event()
        release_lock = threading.Event()

        def hold_user_lock_and_revoke_session():
            with self.factory() as db:
                db.scalar(select(User).where(User.id == "alpha").with_for_update())
                lock_acquired.set()
                if not release_lock.wait(timeout=10):
                    raise TimeoutError("test did not release actor row lock")
                db.execute(AuthSession.__table__.delete().where(
                    AuthSession.user_id == "alpha", AuthSession.token_hash == hashlib.sha256(
                        self.first.token.encode()
                    ).hexdigest(),
                ))
                db.commit()

        def change():
            try:
                with self.factory() as db:
                    AuthService(db).change_password("alpha", self.first.token, self.command(FIRST_PASSWORD))
                return "success"
            except PasswordChangeError as error:
                return error.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            holder = pool.submit(hold_user_lock_and_revoke_session)
            change_future = None
            try:
                self.assertTrue(lock_acquired.wait(timeout=5))
                change_future = pool.submit(change)
                self.assertTrue(self.wait_for_user_lock(change_future))
            finally:
                release_lock.set()
            holder.result(timeout=10)
            self.assertEqual(change_future.result(timeout=10), "authentication_required")
        with self.factory() as db:
            self.assertTrue(verify_password(OLD_PASSWORD, db.get(User, "alpha").password_hash))
            self.assertEqual(db.query(AuditEvent).count(), 0)

    def test_expired_session_while_waiting_for_user_lock_is_rechecked(self):
        lock_acquired = threading.Event()
        release_lock = threading.Event()

        def hold_user_lock_and_expire_session():
            with self.factory() as db:
                db.scalar(select(User).where(User.id == "alpha").with_for_update())
                lock_acquired.set()
                if not release_lock.wait(timeout=10):
                    raise TimeoutError("test did not release actor row lock")
                db.execute(AuthSession.__table__.update().where(
                    AuthSession.user_id == "alpha", AuthSession.token_hash == hashlib.sha256(
                        self.first.token.encode()
                    ).hexdigest(),
                ).values(expires_at=datetime.now(timezone.utc) - timedelta(days=1)))
                db.commit()

        def change():
            try:
                with self.factory() as db:
                    AuthService(db).change_password("alpha", self.first.token, self.command(FIRST_PASSWORD))
                return "success"
            except PasswordChangeError as error:
                return error.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            holder = pool.submit(hold_user_lock_and_expire_session)
            change_future = None
            try:
                self.assertTrue(lock_acquired.wait(timeout=5))
                change_future = pool.submit(change)
                self.assertTrue(self.wait_for_user_lock(change_future))
            finally:
                release_lock.set()
            holder.result(timeout=10)
            self.assertEqual(change_future.result(timeout=10), "authentication_required")
        with self.factory() as db:
            self.assertTrue(verify_password(OLD_PASSWORD, db.get(User, "alpha").password_hash))
            self.assertEqual(db.query(AuditEvent).count(), 0)

    def test_audit_and_commit_failures_roll_back_all_changes_on_postgres(self):
        original_append = AuditEventWriter.append

        def append_then_fail(*args, **kwargs):
            original_append(*args, **kwargs)
            raise RuntimeError("secret audit marker")

        for failure, patcher in (
            ("audit", patch.object(AuditEventWriter, "append", side_effect=append_then_fail)),
            ("commit", patch.object(Session, "commit", side_effect=RuntimeError("secret commit marker"))),
        ):
            with self.subTest(failure=failure):
                with patcher:
                    with self.assertRaises(RuntimeError):
                        with self.factory() as db:
                            AuthService(db).change_password(
                                "alpha", self.first.token, self.command(FIRST_PASSWORD),
                            )
                with self.factory() as db:
                    self.assertTrue(verify_password(OLD_PASSWORD, db.get(User, "alpha").password_hash))
                    self.assertEqual(db.query(AuthSession).filter_by(user_id="alpha").count(), 2)
                    self.assertEqual(db.query(AuditEvent).count(), 0)

    def test_presence_on_other_session_cannot_restore_it_after_change(self):
        with self.factory() as db:
            auth = AuthService(db)
            self.assertTrue(auth.touch_presence(self.second.token, "alpha"))
            auth.change_password("alpha", self.first.token, self.command(FIRST_PASSWORD))
            self.assertFalse(auth.touch_presence(self.second.token, "alpha"))
            self.assertTrue(auth.resolve_session(self.first.token))
            self.assertIsNone(auth.resolve_session(self.second.token))

    def test_logout_before_change_rejects_change_and_change_before_logout_ends_session(self):
        with self.factory() as db:
            self.assertTrue(AuthService(db).revoke_session(self.first.token))
        with self.assertRaises(PasswordChangeError) as revoked:
            with self.factory() as db:
                AuthService(db).change_password("alpha", self.first.token, self.command(FIRST_PASSWORD))
        self.assertEqual(revoked.exception.code, "authentication_required")
        with self.factory() as db:
            self.assertTrue(verify_password(OLD_PASSWORD, db.get(User, "alpha").password_hash))

    def test_change_then_logout_still_revokes_the_retained_session(self):
        with self.factory() as db:
            AuthService(db).change_password("alpha", self.first.token, self.command(FIRST_PASSWORD))
        with self.factory() as db:
            self.assertTrue(AuthService(db).revoke_session(self.first.token))
            self.assertEqual(db.query(AuthSession).filter_by(user_id="alpha").count(), 0)


if __name__ == "__main__":
    unittest.main()
