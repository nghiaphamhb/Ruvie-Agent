"""F009 HTTP contracts: failures must not expose credentials or commit partial users."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from ruvie.api.auth import router
from ruvie.models import AuthSession, Base, User

ORIGIN = "https://auth.example.test"
PASSWORD = "private-test-password"


class RegistrationApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool,
                                    connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine)
        app = FastAPI()
        app.include_router(router)
        app.state.session_factory = self.factory
        app.state.settings = type("Settings", (), {"auth_allowed_origins": (ORIGIN,)})()
        self.client = TestClient(app, base_url=ORIGIN)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def register(self, **overrides):
        return self.client.post("/auth/register", headers={"Origin": ORIGIN}, json={
            "display_name": " Nguyễn An ", "email": " AN@example.test ",
            "password": PASSWORD, **overrides,
        })

    def test_registration_cookie_restores_session_and_logout_revokes_it(self):
        response = self.register()
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(set(body), {"user", "csrf_token"})
        self.assertEqual(set(body["user"]), {"id", "display_name"})
        self.assertEqual(body["user"]["display_name"], "Nguyễn An")
        self.assertNotIn(PASSWORD, response.text)
        self.assertNotIn(self.client.cookies["ruvie_session"], response.text)
        cookie = response.headers["set-cookie"].lower()
        for attribute in ("httponly", "secure", "samesite=lax", "path=/", "max-age=43200"):
            self.assertIn(attribute, cookie)
        self.assertEqual(self.client.get("/auth/session").json(), body)
        self.assertEqual(self.client.post("/auth/logout", headers={"Origin": ORIGIN}).status_code, 403)
        ended = self.client.post("/auth/logout", headers={
            "Origin": ORIGIN, "X-CSRF-Token": body["csrf_token"]})
        self.assertEqual(ended.status_code, 204)
        self.assertEqual(self.client.get("/auth/session").status_code, 401)
        login = self.client.post("/auth/login", headers={"Origin": ORIGIN},
                                 json={"email": "AN@example.test", "password": PASSWORD})
        self.assertEqual(login.status_code, 200)

    def test_duplicate_email_returns_safe_field_error(self):
        self.assertEqual(self.register().status_code, 201)
        response = self.register(email="an@EXAMPLE.test")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"detail": {"code": "email_taken",
                                                      "fields": {"email": "email_taken"}}})

    def test_untrusted_origin_never_creates_a_user(self):
        for headers in ({}, {"Origin": "https://untrusted.test"}):
            with self.subTest(headers=headers):
                response = self.client.post("/auth/register", headers=headers,
                    json={"display_name": "Person", "email": "an@example.test", "password": PASSWORD})
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["detail"]["code"], "origin_not_allowed")
        with self.factory() as db:
            self.assertEqual(db.query(User).count(), 0)

    def test_invalid_payload_uses_redacted_validation_errors(self):
        for change in ({"password": "secret"}, {"password": {"secret": PASSWORD}},
                       {"display_name": " "}, {"email": "wrong"}, {"role": PASSWORD}):
            with self.subTest(change=change):
                response = self.register(**change)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["detail"]["code"], "validation_error")
                self.assertNotIn(PASSWORD, response.text)
                self.assertNotIn('"input"', response.text)
                self.assertNotIn('"ctx"', response.text)
        response = self.client.post("/auth/register", headers={"Origin": ORIGIN},
                                    content='{"password":"secret"', )
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("secret", response.text)
        with self.factory() as db:
            self.assertEqual(db.query(User).count(), 0)

    def test_internal_failure_returns_safe_error_without_cookie_or_records(self):
        with patch("ruvie.services.auth.hash_password", side_effect=RuntimeError(PASSWORD)):
            response = self.register()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": {"code": "registration_failed"}})
        self.assertNotIn(PASSWORD, response.text)
        self.assertNotIn("set-cookie", response.headers)
        with self.factory() as db:
            self.assertEqual(db.query(User).count(), 0)
            self.assertEqual(db.query(AuthSession).count(), 0)


if __name__ == "__main__":
    unittest.main()
