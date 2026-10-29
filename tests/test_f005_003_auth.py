import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.models import AuthSession, Base, User
from ruvie.services.auth import AccountDisabledError, AuthService, hash_password, verify_password
from ruvie.api.auth import router as auth_router
from ruvie.dependencies import get_authenticated_user_id


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine)
        with self.factory() as db:
            db.add(User(id="user-1", email="person@example.test", display_name="Person", password_hash=hash_password("long-password")))
            db.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_password_hash_is_salted_and_verifies(self):
        first = hash_password("long-password")
        second = hash_password("long-password")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("long-password", first))
        self.assertFalse(verify_password("wrong", first))

    def test_authenticate_normalizes_email_and_rejects_inactive(self):
        with self.factory() as db:
            service = AuthService(db)
            self.assertEqual(service.authenticate(" PERSON@example.test ", "long-password").id, "user-1")
            db.get(User, "user-1").is_active = False
            db.commit()
            with self.assertRaises(AccountDisabledError):
                service.authenticate("person@example.test", "long-password")

    def test_session_token_is_hashed_and_session_resolves_then_revokes(self):
        with self.factory() as db:
            service = AuthService(db)
            created = service.create_session("user-1")
            stored = db.query(AuthSession).one()
            self.assertNotEqual(stored.token_hash, created.token)
            self.assertEqual(service.resolve_session(created.token).user.id, "user-1")
            self.assertTrue(service.revoke_session(created.token))
            self.assertIsNone(service.resolve_session(created.token))


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine)
        with self.factory() as db:
            db.add(User(id="user-1", email="person@example.test", display_name="Person", password_hash=hash_password("long-password")))
            db.commit()
        app = FastAPI()
        app.include_router(auth_router)
        app.state.session_factory = self.factory
        app.state.settings = type("Settings", (), {"auth_allowed_origins": ("http://localhost:5173",)})()

        @app.get("/protected")
        def protected(user_id: str = Depends(get_authenticated_user_id)):
            return {"user_id": user_id}

        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def test_login_sets_secure_http_only_cookie_and_session_authenticates(self):
        response = self.client.post("/auth/login", headers={"Origin": "http://localhost:5173"}, json={"email": "person@example.test", "password": "long-password"})
        self.assertEqual(response.status_code, 200)
        cookie = response.cookies.get("ruvie_session")
        self.assertTrue(cookie)
        self.assertIn("httponly", response.headers["set-cookie"].lower())
        self.assertIn("secure", response.headers["set-cookie"].lower())
        self.assertEqual(self.client.get("/protected", headers={"Cookie": f"ruvie_session={cookie}", "X-User-Id": "forged"}).json(), {"user_id": "user-1"})
        self.assertEqual(self.client.get("/auth/session", headers={"Cookie": f"ruvie_session={cookie}"}).status_code, 200)

    def test_login_rejects_bad_credentials_and_unlisted_origin(self):
        invalid = self.client.post("/auth/login", headers={"Origin": "http://localhost:5173"}, json={"email": "person@example.test", "password": "wrong"})
        self.assertEqual(invalid.status_code, 401)
        origin = self.client.post("/auth/login", headers={"Origin": "https://attacker.test"}, json={"email": "person@example.test", "password": "long-password"})
        self.assertEqual(origin.status_code, 403)

    def test_logout_requires_csrf_then_revokes_session(self):
        logged = self.client.post("/auth/login", headers={"Origin": "http://localhost:5173"}, json={"email": "person@example.test", "password": "long-password"})
        token = logged.cookies.get("ruvie_session")
        csrf = logged.json()["csrf_token"]
        headers = {"Origin": "http://localhost:5173", "Cookie": f"ruvie_session={token}"}
        self.assertEqual(self.client.post("/auth/logout", headers=headers).status_code, 403)
        ended = self.client.post("/auth/logout", headers={**headers, "X-CSRF-Token": csrf})
        self.assertEqual(ended.status_code, 204)
        self.assertEqual(self.client.get("/protected", headers={"Cookie": f"ruvie_session={token}"}).status_code, 401)

    def test_expired_session_is_rejected(self):
        with self.factory() as db:
            service = AuthService(db)
            created = service.create_session("user-1")
            record = db.query(AuthSession).one()
            record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
            self.assertIsNone(service.resolve_session(created.token))


if __name__ == "__main__":
    unittest.main()
