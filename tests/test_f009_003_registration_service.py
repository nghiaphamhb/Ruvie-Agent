"""F009 registration contracts and atomic service behavior, without providers."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import ruvie.contracts.auth as contracts
from ruvie.models import AuthSession, Base, User, Membership, AccessGrant
from ruvie.services.auth import AuthService, verify_password


class RegistrationContractTests(unittest.TestCase):
    def request(self, **overrides):
        request_type = getattr(contracts, "RegisterRequest", None)
        self.assertIsNotNone(request_type, "Registration must have its own validated contract")
        return request_type(**{"display_name": " Nguyễn An ", "email": " AN@Example.test ",
                              "password": " example-password ", **overrides})

    def test_normalizes_identity_but_preserves_password(self):
        body = self.request()
        self.assertEqual(body.display_name, "Nguyễn An")
        self.assertEqual(body.email, "an@example.test")
        self.assertEqual(body.password, " example-password ")

    def test_rejects_invalid_fields_and_client_permissions(self):
        for change in (
            {"display_name": "   "}, {"display_name": "a" * 256},
            {"email": "missing-at"}, {"email": "a b@example.test"}, {"email": "a@b.test trailing"},
            {"email": 42}, {"display_name": False}, {"password": 123456789012},
            {"password": "a" * 11}, {"password": "a" * 129},
            {"role": "admin"}, {"project_id": "private"}, {"id": "chosen"},
            {"is_active": True}, {"password_hash": "chosen"},
        ):
            with self.subTest(change=change):
                with self.assertRaises(ValidationError):
                    self.request(**change)

    def test_accepts_password_boundaries_and_unicode(self):
        for password in ("a" * 12, "a" * 128, "🔒" * 12, "Đăng kí 12345"):
            with self.subTest(length=len(password)):
                self.assertEqual(self.request(password=password).password, password)


class RegistrationServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool,
                                    connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def register(self, db, **overrides):
        method = getattr(AuthService(db), "register", None)
        self.assertTrue(callable(method), "AuthService must create an account and session atomically")
        return method(**{"display_name": " Nguyễn An ", "email": " AN@Example.test ",
                         "password": " example-password ", **overrides})

    def test_creates_salted_credentials_and_session_without_access(self):
        with self.factory() as db:
            result = self.register(db)
            self.assertEqual((result.user.display_name, result.user.email, result.user.is_active),
                             ("Nguyễn An", "an@example.test", True))
            self.assertTrue(verify_password(" example-password ", result.user.password_hash))
            self.assertNotEqual(result.user.password_hash, " example-password ")
            created = result.created_session
            self.assertNotEqual(db.scalar(select(AuthSession)).token_hash, created.token)
            self.assertEqual(AuthService(db).resolve_session(created.token).user.id, result.user.id)
            self.assertEqual(db.query(Membership).count(), 0)
            self.assertEqual(db.query(AccessGrant).count(), 0)
        with self.factory() as db:
            self.assertEqual(db.query(User).count(), 1)
            self.assertEqual(db.query(AuthSession).count(), 1)

    def test_duplicate_inactive_user_is_not_overwritten_or_unlocked(self):
        with self.factory() as db:
            user = self.register(db).user
            user.is_active = False
            old_hash = user.password_hash
            db.commit()
            with self.assertRaisesRegex(ValueError, "email_taken"):
                self.register(db, email="AN@example.test", password="different-password")
            self.assertFalse(db.get(User, user.id).is_active)
            self.assertEqual(db.get(User, user.id).password_hash, old_hash)
            self.assertEqual(db.query(User).count(), 1)
            self.assertEqual(db.query(AuthSession).count(), 1)

    def test_session_failure_rolls_back_new_user(self):
        with self.factory() as db:
            with patch("ruvie.services.auth.secrets.token_urlsafe", side_effect=RuntimeError("session failure")):
                with self.assertRaises(RuntimeError):
                    self.register(db)
            self.assertEqual(db.query(User).count(), 0)
            self.assertEqual(db.query(AuthSession).count(), 0)

    def test_commit_failure_after_flush_rolls_back_both_records(self):
        with self.factory() as db:
            def failed_commit():
                db.flush()
                raise SQLAlchemyError("test commit failure")
            with patch.object(db, "commit", side_effect=failed_commit):
                with self.assertRaises(SQLAlchemyError):
                    self.register(db)
            self.assertEqual(db.query(User).count(), 0)
            self.assertEqual(db.query(AuthSession).count(), 0)

    def test_invalid_service_input_cannot_create_an_account(self):
        with self.factory() as db:
            with self.assertRaises(ValueError):
                self.register(db, display_name=" ", password="short")
            self.assertEqual(db.query(User).count(), 0)


if __name__ == "__main__":
    unittest.main()
