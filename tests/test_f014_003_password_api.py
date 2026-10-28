"""HTTP contract for self-service password change and safe authentication failures."""
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ruvie.api.auth import router as auth_router
from ruvie.models import AuthSession, Base, User
from ruvie.services.auth import hash_password


ORIGIN = "https://password.test"
OLD_PASSWORD = " old-password-123 "
NEW_PASSWORD = " new-password-456 "


class ChangePasswordApiTests(unittest.TestCase):
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
        app = FastAPI()
        app.include_router(auth_router)
        app.state.session_factory = self.factory
        app.state.settings = type("Settings", (), {"auth_allowed_origins": (ORIGIN,)})()
        self.app = app
        self.actor, self.actor_csrf = self.login("actor")
        self.other, self.other_csrf = self.login("other")

    def tearDown(self):
        self.actor.close()
        self.other.close()
        self.engine.dispose()

    def login(self, identity):
        client = TestClient(self.app, base_url=ORIGIN)
        response = client.post("/auth/login", headers={"Origin": ORIGIN}, json={
            "email": f"{identity}@example.test", "password": OLD_PASSWORD,
        })
        self.assertEqual(response.status_code, 200, response.text)
        return client, response.json()["csrf_token"]

    def send(self, client=None, csrf=None, **overrides):
        payload = {
            "current_password": OLD_PASSWORD,
            "new_password": NEW_PASSWORD,
            "password_confirmation": NEW_PASSWORD,
        }
        payload.update(overrides)
        return (client or self.actor).post(
            "/auth/password",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf or self.actor_csrf},
            json=payload,
        )

    def test_success_preserves_current_cookie_and_returns_empty_no_store_response(self):
        cookie = self.actor.cookies.get("ruvie_session")
        response = self.send()
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(response.content, b"")
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertNotIn("set-cookie", response.headers)
        self.assertEqual(self.actor.cookies.get("ruvie_session"), cookie)
        self.assertEqual(self.actor.get("/auth/session").status_code, 200)
        with self.factory() as db:
            self.assertEqual(db.query(AuthSession).filter_by(user_id="actor").count(), 1)
            self.assertEqual(db.query(AuthSession).filter_by(user_id="other").count(), 1)

    def test_wrong_current_password_is_a_field_error_and_keeps_session(self):
        response = self.send(current_password="wrong-current-password")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "current_password_incorrect")
        self.assertEqual(
            response.json()["detail"]["fields"]["current_password"],
            "current_password_incorrect",
        )
        self.assertNotIn("wrong-current-password", response.text)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertEqual(self.actor.get("/auth/session").status_code, 200)

    def test_confirmation_mismatch_and_new_password_unchanged_have_safe_codes(self):
        mismatch = self.send(password_confirmation="different-password")
        self.assertEqual(mismatch.status_code, 422)
        self.assertEqual(mismatch.json()["detail"]["code"], "password_confirmation_mismatch")
        unchanged = self.send(new_password=OLD_PASSWORD, password_confirmation=OLD_PASSWORD)
        self.assertEqual(unchanged.status_code, 422)
        self.assertEqual(unchanged.json()["detail"]["code"], "password_unchanged")

    def test_origin_csrf_and_body_validation_are_safe_and_never_cached(self):
        missing_origin = self.actor.post("/auth/password", json={"new_password": "secret-marker"})
        self.assertEqual(missing_origin.status_code, 403)
        self.assertEqual(missing_origin.headers.get("cache-control"), "no-store")
        bad_origin = self.actor.post(
            "/auth/password", headers={"Origin": "https://attacker.test"},
            content=b"{bad json containing secret-marker",
        )
        self.assertEqual(bad_origin.status_code, 403)
        self.assertNotIn("secret-marker", bad_origin.text)
        self.assertEqual(bad_origin.headers.get("cache-control"), "no-store")

        no_csrf = self.actor.post("/auth/password", headers={"Origin": ORIGIN}, json={
            "current_password": OLD_PASSWORD,
            "new_password": NEW_PASSWORD,
            "password_confirmation": NEW_PASSWORD,
        })
        self.assertEqual(no_csrf.status_code, 403)
        self.assertEqual(no_csrf.json()["detail"]["code"], "csrf_invalid")
        self.assertEqual(no_csrf.headers.get("cache-control"), "no-store")

        invalid = self.send(current_password="secret-marker", new_password="short")
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(invalid.json()["detail"]["fields"]["new_password"], "password_length")
        self.assertNotIn("secret-marker", invalid.text)
        self.assertEqual(invalid.headers.get("cache-control"), "no-store")

    def test_missing_cookie_inactive_user_malformed_json_and_extra_fields_are_safe(self):
        anonymous = TestClient(self.app, base_url=ORIGIN)
        try:
            missing = anonymous.post(
                "/auth/password", headers={"Origin": ORIGIN}, json={
                    "current_password": OLD_PASSWORD,
                    "new_password": NEW_PASSWORD,
                    "password_confirmation": NEW_PASSWORD,
                },
            )
            self.assertEqual(missing.status_code, 401)
            self.assertEqual(missing.headers.get("cache-control"), "no-store")
            self.assertEqual(missing.json()["detail"]["code"], "authentication_required")
        finally:
            anonymous.close()

        with self.factory() as db:
            db.get(User, "actor").is_active = False
            db.commit()
        inactive = self.send()
        self.assertEqual(inactive.status_code, 401)
        self.assertEqual(inactive.headers.get("cache-control"), "no-store")
        with self.factory() as db:
            db.get(User, "actor").is_active = True
            db.commit()

        malformed = self.actor.post(
            "/auth/password", headers={"Origin": ORIGIN, "X-CSRF-Token": self.actor_csrf},
            content=b'{"current_password":"secret-marker",',
        )
        self.assertEqual(malformed.status_code, 422)
        self.assertEqual(malformed.json()["detail"]["code"], "validation_error")
        self.assertNotIn("secret-marker", malformed.text)
        self.assertEqual(malformed.headers.get("cache-control"), "no-store")

        extra = self.send(user_id="attacker-selected-id")
        self.assertEqual(extra.status_code, 422)
        self.assertEqual(extra.json()["detail"]["code"], "validation_error")
        self.assertNotIn("attacker-selected-id", extra.text)
        self.assertEqual(extra.headers.get("cache-control"), "no-store")

    def test_service_failure_is_503_no_store_and_does_not_expose_exception(self):
        with patch("ruvie.api.auth.AuthService.change_password", side_effect=RuntimeError("secret-marker sql password")):
            response = self.send()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "password_change_unavailable")
        self.assertNotIn("secret-marker", response.text)
        self.assertNotIn("sql password", response.text)
        self.assertEqual(response.headers.get("cache-control"), "no-store")

    def test_user_and_admin_can_change_only_their_own_password(self):
        actor_cookie = self.actor.cookies.get("ruvie_session")
        response = self.send(self.other, csrf=self.other_csrf)
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertEqual(self.other.get("/auth/session").status_code, 200)
        self.assertEqual(self.actor.cookies.get("ruvie_session"), actor_cookie)
        with self.factory() as db:
            self.assertEqual(db.query(AuthSession).filter_by(user_id="other").count(), 1)
            self.assertEqual(db.query(AuthSession).filter_by(user_id="actor").count(), 1)


if __name__ == "__main__":
    unittest.main()
