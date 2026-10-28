"""PostgreSQL serializes conflicting account deactivations."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest
import time
from sqlalchemy import select, func, text
from ruvie.contracts.admin import SetAccountActivityRequest
from ruvie.models import User
from ruvie.services.admin import AdminAccountService, AuthenticationRequired
import test_f005_007_e2e as fixtures

class ActivityConcurrencyTests(unittest.TestCase):
    def wait_for_lock(self, factory):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            with factory() as db:
                waiting = db.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock')"))
            if waiting:
                return True
            time.sleep(0.02)
        return False
    @classmethod
    def setUpClass(cls):
        fixtures.F005007EndToEndTests.setUpClass()
    @classmethod
    def tearDownClass(cls):
        fixtures.F005007EndToEndTests.tearDownClass()
    def test_cross_deactivation_retains_one_active_admin(self):
        fixture = fixtures.F005007EndToEndTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        factory = fixture.client.app.state.session_factory
        with factory() as db:
            for name in ('alpha', 'beta'):
                user = db.get(User, name)
                user.system_role = 'admin'
                user.is_active = True
            db.commit()
        barrier = Barrier(2)
        def deactivate(pair):
            barrier.wait(timeout=10)
            with factory() as db:
                try:
                    AdminAccountService(db).set_account_activity(pair[0], pair[1], SetAccountActivityRequest(is_active=False))
                    return 'changed'
                except AuthenticationRequired:
                    return 'denied'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(deactivate, [('alpha', 'beta'), ('beta', 'alpha')]))
        self.assertCountEqual(results, ['changed', 'denied'])
        with factory() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(User).where(User.system_role == 'admin', User.is_active.is_(True))), 1)

    def test_deactivation_and_self_demotion_keep_active_admin(self):
        from ruvie.contracts.admin import UpdateAccountRequest
        from ruvie.services.admin import LastActiveAdmin
        fixture = fixtures.F005007EndToEndTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        factory = fixture.client.app.state.session_factory
        with factory() as db:
            for name in ('alpha', 'beta'):
                user = db.get(User, name)
                user.system_role = 'admin'
                user.is_active = True
            db.commit()
        barrier = Barrier(2)
        def act(kind):
            barrier.wait(timeout=10)
            with factory() as db:
                try:
                    service = AdminAccountService(db)
                    if kind == 'lock':
                        service.set_account_activity('alpha', 'beta', SetAccountActivityRequest(is_active=False))
                    else:
                        service.update_account('beta', 'beta', UpdateAccountRequest(system_role='user'))
                    return 'changed'
                except (AuthenticationRequired, LastActiveAdmin):
                    return 'denied'
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(act, ['lock', 'demote']))
        self.assertIn('changed', outcomes)
        with factory() as db:
            self.assertGreaterEqual(db.scalar(select(func.count()).select_from(User).where(User.system_role == 'admin', User.is_active.is_(True))), 1)

    def test_login_and_lock_are_serialized_on_target_row(self):
        from threading import Event
        from sqlalchemy import select
        from ruvie.models import AuthSession
        from ruvie.services.auth import AuthService, hash_password
        fixture = fixtures.F005007EndToEndTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        factory = fixture.client.app.state.session_factory
        with factory() as db:
            db.get(User, 'alpha').system_role = 'admin'
            db.get(User, 'beta').password_hash = hash_password('race-password-123')
            db.commit()
        login_has_lock, release_login, lock_started = Event(), Event(), Event()
        def login_first():
            with factory() as db:
                service = AuthService(db)
                user = service.authenticate('beta@example.test', 'race-password-123')
                self.assertIsNotNone(user)
                login_has_lock.set()
                self.assertTrue(release_login.wait(10))
                return service.create_session(user.id).token
        def deactivate():
            lock_started.set()
            with factory() as db:
                return AdminAccountService(db).set_account_activity('alpha', 'beta', SetAccountActivityRequest(is_active=False))
        with ThreadPoolExecutor(max_workers=2) as pool:
            login = pool.submit(login_first)
            try:
                self.assertTrue(login_has_lock.wait(10))
                locked = pool.submit(deactivate)
                self.assertTrue(lock_started.wait(10))
                self.assertTrue(self.wait_for_lock(factory))
            finally:
                release_login.set()
            token = login.result(timeout=20)
            self.assertFalse(locked.result(timeout=20).is_active)
        with factory() as db:
            self.assertIsNone(AuthService(db).resolve_session(token))
            self.assertIsNone(AuthService(db).authenticate('beta@example.test', 'race-password-123'))
            self.assertEqual(db.query(AuthSession).filter_by(user_id='beta').count(), 0)

    def test_actor_is_rechecked_after_waiting_for_advisory_lock(self):
        from threading import Event
        from sqlalchemy import text
        from ruvie.services.admin import AdminRequired
        fixture = fixtures.F005007EndToEndTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        factory = fixture.client.app.state.session_factory
        with factory() as db:
            db.get(User, 'alpha').system_role = 'admin'
            db.get(User, 'beta').system_role = 'admin'
            db.commit()
        started = Event()
        def change():
            with factory() as db:
                db.get(User, 'beta')  # Populate the identity map before permission changes.
                started.set()
                with self.assertRaises(AdminRequired):
                    AdminAccountService(db).set_account_activity('beta', 'alpha', SetAccountActivityRequest(is_active=False))
        with factory() as gate:
            gate.execute(text('SELECT pg_advisory_xact_lock(:first, :second)'), {'first': 0x52555649, 'second': 13})
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending = pool.submit(change)
                try:
                    self.assertTrue(started.wait(10))
                    self.assertTrue(self.wait_for_lock(factory))
                    with factory() as db:
                        db.get(User, 'beta').system_role = 'user'
                        db.commit()
                finally:
                    gate.commit()
                pending.result(timeout=20)
        with factory() as db:
            self.assertTrue(db.get(User, 'alpha').is_active)

    def test_password_change_before_deactivation_cannot_leave_session_active(self):
        from threading import Event
        from unittest.mock import patch
        from ruvie.contracts.auth import ChangePasswordRequest
        from ruvie.models import AuthSession
        from ruvie.services import auth as auth_module
        from ruvie.services.auth import AuthService, PasswordChangeError, hash_password
        fixture = fixtures.F005007EndToEndTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        factory = fixture.client.app.state.session_factory
        old, new = 'old-race-password-123', 'new-race-password-123'
        with factory() as db:
            db.get(User, 'alpha').system_role = 'admin'
            db.get(User, 'beta').password_hash = hash_password(old)
            db.commit()
            token = AuthService(db).create_session('beta').token
        hashing, release, started = Event(), Event(), Event()
        original_hash = auth_module.hash_password
        def pause_hash(password):
            if password == new:
                hashing.set()
                if not release.wait(10):
                    raise TimeoutError('password test release timed out')
            return original_hash(password)
        def change_password():
            with factory() as db:
                return AuthService(db).change_password('beta', token, ChangePasswordRequest(current_password=old, new_password=new, password_confirmation=new))
        def deactivate():
            started.set()
            with factory() as db:
                return AdminAccountService(db).set_account_activity('alpha', 'beta', SetAccountActivityRequest(is_active=False))
        with patch.object(auth_module, 'hash_password', side_effect=pause_hash):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(change_password)
                try:
                    self.assertTrue(hashing.wait(10))
                    second = pool.submit(deactivate)
                    self.assertTrue(started.wait(10))
                    self.assertTrue(self.wait_for_lock(factory))
                finally:
                    release.set()
                first.result(timeout=20)
                self.assertFalse(second.result(timeout=20).is_active)
        with factory() as db:
            self.assertEqual(db.query(AuthSession).filter_by(user_id='beta').count(), 0)
            self.assertIsNone(AuthService(db).resolve_session(token))
            with self.assertRaises(PasswordChangeError):
                AuthService(db).change_password('beta', token, ChangePasswordRequest(current_password=new, new_password=old, password_confirmation=old))

    def test_presence_before_lock_does_not_restore_a_revoked_session(self):
        from threading import Event
        from unittest.mock import patch
        from ruvie.models import AuthSession
        from ruvie.services.auth import AuthService
        fixture = fixtures.F005007EndToEndTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        factory = fixture.client.app.state.session_factory
        with factory() as db:
            db.get(User, 'alpha').system_role = 'admin'
            db.commit()
            token = AuthService(db).create_session('beta').token
            db.query(AuthSession).filter_by(user_id='beta').update({'last_seen_at': None})
            db.commit()
        entered, release, started = Event(), Event(), Event()
        original = AuthService._record_activity
        def pause(service, user_id, now):
            entered.set()
            if not release.wait(10):
                raise TimeoutError('presence test release timed out')
            return original(service, user_id, now)
        def presence():
            with factory() as db:
                return AuthService(db).touch_presence(token, 'beta')
        def deactivate():
            started.set()
            with factory() as db:
                return AdminAccountService(db).set_account_activity('alpha', 'beta', SetAccountActivityRequest(is_active=False))
        with patch.object(AuthService, '_record_activity', pause):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(presence)
                try:
                    self.assertTrue(entered.wait(10))
                    second = pool.submit(deactivate)
                    self.assertTrue(started.wait(10))
                    self.assertTrue(self.wait_for_lock(factory))
                finally:
                    release.set()
                self.assertTrue(first.result(timeout=20))
                self.assertFalse(second.result(timeout=20).is_active)
        with factory() as db:
            self.assertFalse(AuthService(db).touch_presence(token, 'beta'))
            self.assertEqual(db.query(AuthSession).filter_by(user_id='beta').count(), 0)

    def test_concurrent_duplicate_deactivation_writes_one_audit(self):
        from ruvie.models import AuditEvent, AuthSession
        from ruvie.services.auth import AuthService
        fixture = fixtures.F005007EndToEndTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        factory = fixture.client.app.state.session_factory
        with factory() as db:
            db.get(User, 'alpha').system_role = 'admin'
            db.commit()
            first = AuthService(db).create_session('beta')
            second = AuthService(db).create_session('beta')
        barrier = Barrier(2)
        def deactivate(_):
            barrier.wait(timeout=10)
            with factory() as db:
                return AdminAccountService(db).set_account_activity('alpha', 'beta', SetAccountActivityRequest(is_active=False)).is_active
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(deactivate, range(2))), [False, False])
        with factory() as db:
            self.assertEqual(db.query(AuthSession).filter_by(user_id='beta').count(), 0)
            self.assertIsNone(AuthService(db).resolve_session(first.token))
            self.assertIsNone(AuthService(db).resolve_session(second.token))
            self.assertEqual(db.query(AuditEvent).filter_by(action='account.deactivate', resource_id='beta').count(), 1)

    def test_lock_before_login_rejects_login_after_waiting(self):
        from threading import Event
        from unittest.mock import patch
        from ruvie.services.audit import AuditEventWriter
        from ruvie.services.auth import AuthService, hash_password
        fixture = fixtures.F005007EndToEndTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        factory = fixture.client.app.state.session_factory
        with factory() as db:
            db.get(User, 'alpha').system_role = 'admin'
            db.get(User, 'beta').password_hash = hash_password('race-password-123')
            db.commit()
        entered, release, started = Event(), Event(), Event()
        original = AuditEventWriter.append
        def pause_audit(*args, **kwargs):
            if kwargs.get('action') == 'account.deactivate':
                entered.set()
                if not release.wait(10):
                    raise TimeoutError('lock test release timed out')
            return original(*args, **kwargs)
        def deactivate():
            with factory() as db:
                return AdminAccountService(db).set_account_activity('alpha', 'beta', SetAccountActivityRequest(is_active=False))
        def login():
            started.set()
            with factory() as db:
                return AuthService(db).authenticate('beta@example.test', 'race-password-123')
        with patch.object(AuditEventWriter, 'append', side_effect=pause_audit):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(deactivate)
                try:
                    self.assertTrue(entered.wait(10))
                    second = pool.submit(login)
                    self.assertTrue(started.wait(10))
                    self.assertTrue(self.wait_for_lock(factory))
                finally:
                    release.set()
                self.assertFalse(first.result(timeout=20).is_active)
                self.assertIsNone(second.result(timeout=20))

    def test_concurrent_lock_then_unlock_keeps_old_token_revoked(self):
        from threading import Event
        from unittest.mock import patch
        from ruvie.models import AuditEvent
        from ruvie.services.audit import AuditEventWriter
        from ruvie.services.auth import AuthService
        fixture = fixtures.F005007EndToEndTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        factory = fixture.client.app.state.session_factory
        with factory() as db:
            db.get(User, 'alpha').system_role = 'admin'
            db.commit()
            token = AuthService(db).create_session('beta').token
        entered, release, started = Event(), Event(), Event()
        original = AuditEventWriter.append
        def pause_audit(*args, **kwargs):
            if kwargs.get('action') == 'account.deactivate':
                entered.set()
                if not release.wait(10):
                    raise TimeoutError('activity test release timed out')
            return original(*args, **kwargs)
        def activity(active):
            if active:
                started.set()
            with factory() as db:
                return AdminAccountService(db).set_account_activity('alpha', 'beta', SetAccountActivityRequest(is_active=active))
        with patch.object(AuditEventWriter, 'append', side_effect=pause_audit):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(activity, False)
                try:
                    self.assertTrue(entered.wait(10))
                    second = pool.submit(activity, True)
                    self.assertTrue(started.wait(10))
                    self.assertTrue(self.wait_for_lock(factory))
                finally:
                    release.set()
                self.assertFalse(first.result(timeout=20).is_active)
                self.assertTrue(second.result(timeout=20).is_active)
        with factory() as db:
            self.assertIsNone(AuthService(db).resolve_session(token))
            actions = set(db.scalars(select(AuditEvent.action).where(AuditEvent.resource_id == 'beta')))
            self.assertTrue({'account.activate', 'account.deactivate'}.issubset(actions))
