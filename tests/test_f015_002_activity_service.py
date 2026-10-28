"""Account activity changes preserve data and revoke only the target's sessions."""
from datetime import datetime, timedelta, timezone
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ruvie.contracts.admin import SetAccountActivityRequest
from ruvie.models import AuditEvent, AuthSession, Base, User
from ruvie.services.admin import AdminAccountService, LastActiveAdmin


class AccountActivityServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', poolclass=StaticPool)
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine)
        with self.factory() as db:
            db.add_all([
                User(id='admin', email='admin@example.test', display_name='Admin', system_role='admin', is_active=True, password_hash='admin-hash'),
                User(id='target', email='user@example.test', display_name='User', system_role='user', is_active=True, password_hash='user-hash'),
                AuthSession(id='target-session', user_id='target', token_hash='a' * 64, csrf_token='csrf', expires_at=datetime.now(timezone.utc) + timedelta(days=1)),
                AuthSession(id='admin-session', user_id='admin', token_hash='b' * 64, csrf_token='csrf', expires_at=datetime.now(timezone.utc) + timedelta(days=1)),
            ])
            db.commit()

    def test_lock_revokes_sessions_and_unlock_does_not_restore_them(self):
        with self.factory() as db:
            service = AdminAccountService(db)
            self.assertFalse(service.set_account_activity('admin', 'target', SetAccountActivityRequest(is_active=False)).is_active)
            self.assertTrue(service.set_account_activity('admin', 'target', SetAccountActivityRequest(is_active=True)).is_active)
        with self.factory() as db:
            user = db.get(User, 'target')
            self.assertEqual(user.password_hash, 'user-hash')
            self.assertEqual(user.system_role, 'user')
            self.assertIsNone(db.get(AuthSession, 'target-session'))
            self.assertIsNotNone(db.get(AuthSession, 'admin-session'))
            actions = set(db.scalars(select(AuditEvent.action)))
            self.assertEqual(actions, {'account.deactivate', 'account.activate'})

    def test_last_active_admin_cannot_lock_self(self):
        with self.factory() as db:
            with self.assertRaises(LastActiveAdmin):
                AdminAccountService(db).set_account_activity('admin', 'admin', SetAccountActivityRequest(is_active=False))

    def test_audit_failure_rolls_back_deactivation_and_session_removal(self):
        from unittest.mock import patch
        with self.factory() as db:
            with patch('ruvie.services.admin.AuditEventWriter.append', side_effect=RuntimeError('audit failure')):
                with self.assertRaises(RuntimeError):
                    AdminAccountService(db).set_account_activity('admin', 'target', SetAccountActivityRequest(is_active=False))
        with self.factory() as db:
            self.assertTrue(db.get(User, 'target').is_active)
            self.assertIsNotNone(db.get(AuthSession, 'target-session'))
            self.assertEqual(list(db.scalars(select(AuditEvent))), [])

    def test_repeat_lock_is_idempotent_and_does_not_duplicate_audit(self):
        with self.factory() as db:
            service = AdminAccountService(db)
            service.set_account_activity('admin', 'target', SetAccountActivityRequest(is_active=False))
            service.set_account_activity('admin', 'target', SetAccountActivityRequest(is_active=False))
        with self.factory() as db:
            self.assertEqual(len(list(db.scalars(select(AuditEvent)))), 1)

    def test_commit_failure_rolls_back_activity_and_sessions(self):
        from unittest.mock import patch
        with self.factory() as db:
            with patch.object(db, 'commit', side_effect=RuntimeError('commit failure')):
                with self.assertRaises(RuntimeError):
                    AdminAccountService(db).set_account_activity('admin', 'target', SetAccountActivityRequest(is_active=False))
        with self.factory() as db:
            self.assertTrue(db.get(User, 'target').is_active)
            self.assertIsNotNone(db.get(AuthSession, 'target-session'))
            self.assertEqual(list(db.scalars(select(AuditEvent))), [])

    def test_inactive_account_noop_clears_stray_sessions_without_audit(self):
        with self.factory() as db:
            db.get(User, 'target').is_active = False
            db.commit()
            AdminAccountService(db).set_account_activity('admin', 'target', SetAccountActivityRequest(is_active=False))
        with self.factory() as db:
            self.assertIsNone(db.get(AuthSession, 'target-session'))
            self.assertEqual(list(db.scalars(select(AuditEvent))), [])
