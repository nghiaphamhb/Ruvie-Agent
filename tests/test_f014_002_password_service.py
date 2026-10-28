"""Self-service password changes update password, current session and audit atomically."""
import hashlib
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ruvie.contracts.auth import ChangePasswordRequest
from ruvie.models import AuditEvent, AuthSession, Base, User
from ruvie.services.audit import AuditEventWriter
from ruvie.services.auth import AuthService, PasswordChangeError, hash_password, verify_password


OLD_PASSWORD = " old-password-123 "
NEW_PASSWORD = " new-password-456 "


class SelfServicePasswordChangeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine)
        with self.factory() as db:
            db.add_all([
                User(id="actor", email="actor@example.test", display_name="Actor",
                     password_hash=hash_password(OLD_PASSWORD), system_role="user", is_active=True),
                User(id="other", email="other@example.test", display_name="Other",
                     password_hash=hash_password(OLD_PASSWORD), system_role="admin", is_active=True),
            ])
            db.commit()
            self.actor_session = AuthService(db).create_session("actor")
            self.other_session = AuthService(db).create_session("actor")
            self.foreign_session = AuthService(db).create_session("other")

    def tearDown(self):
        self.engine.dispose()

    def command(self, **changes):
        values = {
            "current_password": OLD_PASSWORD,
            "new_password": NEW_PASSWORD,
            "password_confirmation": NEW_PASSWORD,
        }
        values.update(changes)
        return ChangePasswordRequest(**values)

    def change(self, token, command=None, actor_id="actor"):
        with self.factory() as db:
            return AuthService(db).change_password(
                actor_id, token, command or self.command()
            )

    def test_success_keeps_only_the_calling_session_and_audits_without_secrets(self):
        result = self.change(self.actor_session.token)
        self.assertEqual(result.user_id, "actor")
        with self.factory() as db:
            user = db.get(User, "actor")
            self.assertTrue(verify_password(NEW_PASSWORD, user.password_hash))
            self.assertNotEqual(user.password_hash, NEW_PASSWORD)
            sessions = list(db.scalars(select(AuthSession).where(AuthSession.user_id == "actor")))
            self.assertEqual([row.id for row in sessions], [
                db.scalar(select(AuthSession.id).where(
                    AuthSession.token_hash == hashlib.sha256(
                        self.actor_session.token.encode()
                    ).hexdigest()
                ))
            ])
            kept = sessions[0]
            self.assertEqual(kept.csrf_token, self.actor_session.csrf_token)
            self.assertEqual(
                kept.expires_at.replace(tzinfo=timezone.utc), self.actor_session.expires_at
            )
            self.assertEqual(
                db.scalar(select(func.count()).select_from(AuditEvent)), 1
            )
            event = db.scalar(select(AuditEvent))
            self.assertEqual(
                (event.actor_user_id, event.resource_id, event.action, event.reason),
                ("actor", "actor", "account.password_change", "self_service"),
            )
            self.assertNotIn(NEW_PASSWORD, event.reason)
            self.assertEqual(db.query(AuthSession).filter_by(user_id="other").count(), 1)

    def test_bad_current_password_does_not_change_hash_sessions_or_audit(self):
        with self.factory() as db:
            original_hash = db.get(User, "actor").password_hash
        with self.assertRaises(PasswordChangeError) as raised:
            self.change(self.actor_session.token, self.command(current_password="incorrect"))
        self.assertEqual(raised.exception.code, "current_password_incorrect")
        with self.factory() as db:
            self.assertEqual(db.get(User, "actor").password_hash, original_hash)
            self.assertEqual(db.query(AuthSession).filter_by(user_id="actor").count(), 2)
            self.assertEqual(db.query(AuditEvent).count(), 0)

    def test_new_password_must_differ_after_current_password_is_verified(self):
        with self.assertRaises(PasswordChangeError) as raised:
            self.change(self.actor_session.token, self.command(
                new_password=OLD_PASSWORD, password_confirmation=OLD_PASSWORD
            ))
        self.assertEqual(raised.exception.code, "password_unchanged")

    def test_revalidates_mutated_commands_and_rejects_inactive_or_missing_password_hash(self):
        mutated = ChangePasswordRequest.model_construct(
            current_password=OLD_PASSWORD,
            new_password="short",
            password_confirmation="short",
        )
        with self.assertRaises(ValueError):
            self.change(self.actor_session.token, mutated)
        with self.factory() as db:
            user = db.get(User, "actor")
            user.is_active = False
            db.commit()
        with self.assertRaises(PasswordChangeError) as inactive:
            self.change(self.actor_session.token)
        self.assertEqual(inactive.exception.code, "authentication_required")
        with self.factory() as db:
            user = db.get(User, "actor")
            user.is_active = True
            user.password_hash = None
            db.commit()
        with self.assertRaises(PasswordChangeError) as no_hash:
            self.change(self.actor_session.token)
        self.assertEqual(no_hash.exception.code, "current_password_incorrect")

    def test_hash_failure_rolls_back_password_session_and_audit_changes(self):
        with patch("ruvie.services.auth.hash_password", side_effect=RuntimeError("private hash detail")):
            with self.assertRaisesRegex(RuntimeError, "private hash detail"):
                self.change(self.actor_session.token)
        with self.factory() as db:
            self.assertTrue(verify_password(OLD_PASSWORD, db.get(User, "actor").password_hash))
            self.assertEqual(db.query(AuthSession).filter_by(user_id="actor").count(), 2)
            self.assertEqual(db.query(AuditEvent).count(), 0)

    def test_foreign_or_expired_session_is_rejected_without_mutation(self):
        for token, actor_id in ((self.foreign_session.token, "actor"),
                                ("missing-session-token", "actor")):
            with self.subTest(actor_id=actor_id):
                with self.assertRaises(PasswordChangeError) as raised:
                    self.change(token, actor_id=actor_id)
                self.assertEqual(raised.exception.code, "authentication_required")
        with self.factory() as db:
            actor_session = db.scalar(select(AuthSession).where(
                AuthSession.token_hash == hashlib.sha256(
                    self.actor_session.token.encode()
                ).hexdigest()
            ))
            actor_session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        with self.assertRaises(PasswordChangeError) as raised:
            self.change(self.actor_session.token)
        self.assertEqual(raised.exception.code, "authentication_required")

    def test_audit_failure_rolls_back_hash_and_session_deletion(self):
        original = AuditEventWriter.append

        def fail_after_append(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("audit failure")

        with patch.object(AuditEventWriter, "append", side_effect=fail_after_append):
            with self.assertRaises(RuntimeError):
                self.change(self.actor_session.token)
        with self.factory() as db:
            self.assertTrue(verify_password(OLD_PASSWORD, db.get(User, "actor").password_hash))
            self.assertEqual(db.query(AuthSession).filter_by(user_id="actor").count(), 2)
            self.assertEqual(db.query(AuditEvent).count(), 0)

    def test_commit_failure_rolls_back_hash_session_deletion_and_audit(self):
        from sqlalchemy.orm import Session

        with patch.object(Session, "commit", side_effect=RuntimeError("private commit detail")):
            with self.assertRaisesRegex(RuntimeError, "private commit detail"):
                self.change(self.actor_session.token)
        with self.factory() as db:
            self.assertTrue(verify_password(OLD_PASSWORD, db.get(User, "actor").password_hash))
            self.assertEqual(db.query(AuthSession).filter_by(user_id="actor").count(), 2)
            self.assertEqual(db.query(AuditEvent).count(), 0)


if __name__ == "__main__":
    unittest.main()
