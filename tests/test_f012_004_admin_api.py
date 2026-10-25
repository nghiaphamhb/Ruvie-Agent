"""F012 account contracts, redaction and protected production administration APIs."""
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.api import security
from ruvie.api.auth import router as auth_router
from ruvie.contracts import auth
from ruvie.models import AccessGrant, AuditEvent, AuthSession, Base, Membership, User
from ruvie.services.audit import AuditEventWriter
from ruvie.services.auth import hash_password

ORIGIN = "https://accounts.example.test"
PASSWORD = " sensitive-password-123 "


class ContractHelpers:
    def admin_contracts(self):
        self.assertIsNotNone(
            importlib.util.find_spec("ruvie.contracts.admin"),
            "Admin account contracts must exist",
        )
        return importlib.import_module("ruvie.contracts.admin")

    def account_body(self, **overrides):
        return {
            "display_name": " Nguyễn An ", "email": " AN@Example.test ",
            "password": PASSWORD, **overrides,
        }

    def account_summary(self):
        return {
            "id": "created-user", "display_name": "Nguyễn An", "email": "an@example.test",
            "system_role": "user", "is_active": True,
            "created_at": datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc),
        }


class AccountContractTests(ContractHelpers, unittest.TestCase):
    def test_creation_defaults_to_user_and_preserves_password_exactly(self):
        body = self.admin_contracts().CreateAccountRequest(**self.account_body())
        self.assertEqual(
            (body.display_name, body.email, body.password, body.system_role),
            ("Nguyễn An", "an@example.test", PASSWORD, "user"),
        )

    def test_admin_can_select_either_role_but_invalid_roles_are_rejected(self):
        request = self.admin_contracts().CreateAccountRequest
        for role in ("user", "admin"):
            with self.subTest(role=role):
                self.assertEqual(request(**self.account_body(system_role=role)).system_role, role)
        for role in ("pending", "Admin", "", None, True, 1, {"secret": PASSWORD}):
            with self.subTest(role=role), self.assertRaises(ValidationError):
                request(**self.account_body(system_role=role))

    def test_identity_and_password_accept_boundaries_and_unicode(self):
        request = self.admin_contracts().CreateAccountRequest
        for password in ("a" * 12, "a" * 128, "🔒" * 12, PASSWORD):
            with self.subTest(length=len(password)):
                body = request(**self.account_body(
                    display_name="名" * 255, email="a" * 307 + "@example.test", password=password,
                ))
                self.assertEqual(body.password, password)
                self.assertEqual(len(body.display_name), 255)
                self.assertEqual(len(body.email), 320)

    def test_invalid_identity_lengths_and_types_are_not_coerced(self):
        request = self.admin_contracts().CreateAccountRequest
        invalid = (
            {"display_name": " "}, {"display_name": "a" * 256}, {"display_name": False},
            {"email": "a" * 308 + "@example.test"}, {"email": "not-an-email"},
            {"email": "a@b.test trailing"}, {"email": 42},
            {"password": "a" * 11}, {"password": "a" * 129},
            {"password": None}, {"password": 123456789012},
        )
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValidationError):
                request(**self.account_body(**change))

    def test_required_fields_and_extra_permission_fields_are_rejected(self):
        request = self.admin_contracts().CreateAccountRequest
        for field in ("display_name", "email", "password"):
            body = self.account_body()
            del body[field]
            with self.subTest(missing=field), self.assertRaises(ValidationError):
                request(**body)
        for field in ("actor_user_id", "project_id", "memberships", "scopes", "password_hash"):
            with self.subTest(extra=field), self.assertRaises(ValidationError):
                request(**self.account_body(**{field: PASSWORD}))

    def test_initial_registration_never_accepts_a_client_selected_role(self):
        for role in ("user", "admin"):
            with self.subTest(role=role), self.assertRaises(ValidationError):
                auth.RegisterRequest(**self.account_body(system_role=role))

    def test_password_is_hidden_in_request_repr_and_validation_messages(self):
        for request in (auth.RegisterRequest, self.admin_contracts().CreateAccountRequest):
            with self.subTest(contract=request.__name__):
                self.assertNotIn(PASSWORD, repr(request(**self.account_body())))
                try:
                    request(**self.account_body(password={"secret": PASSWORD}))
                except ValidationError as error:
                    self.assertNotIn(PASSWORD, str(error))
                else:
                    self.fail("A password object must not be accepted")

    def test_setup_response_is_a_strict_boolean_and_exposes_only_setup_state(self):
        response = getattr(auth, "SetupStatusResponse", None)
        self.assertIsNotNone(response, "Setup state must have a public response contract")
        self.assertEqual(
            response(requires_initial_admin=True, api_key=PASSWORD).model_dump(),
            {"requires_initial_admin": True},
        )
        for value in ("true", 1, None):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                response(requires_initial_admin=value)

    def test_auth_user_requires_and_serializes_a_supported_system_role(self):
        user = auth.AuthUser(id="a", display_name="A", system_role="admin")
        self.assertEqual(user.model_dump(), {"id": "a", "display_name": "A", "system_role": "admin"})
        for extra in ({}, {"system_role": "pending"}, {"system_role": None}):
            with self.subTest(extra=extra), self.assertRaises(ValidationError):
                auth.AuthUser(id="a", display_name="A", **extra)

    def test_admin_responses_expose_only_safe_account_metadata(self):
        contracts = self.admin_contracts()
        account = SimpleNamespace(
            **self.account_summary(), password_hash=PASSWORD, csrf_token=PASSWORD, api_key=PASSWORD,
        )
        summary = contracts.AdminAccountSummary.model_validate(account)
        response = contracts.CreateAccountResponse(user=summary)
        self.assertEqual(response.model_dump(mode="json"), {
            "user": {**self.account_summary(), "created_at": "2026-10-23T12:00:00Z"},
        })
        self.assertNotIn(PASSWORD, response.model_dump_json())

    def test_lookup_response_allows_zero_or_one_account_without_secrets(self):
        contracts = self.admin_contracts()
        self.assertEqual(contracts.AccountLookupResponse(users=[]).model_dump(), {"users": []})
        summary = {**self.account_summary(), "password_hash": PASSWORD, "token": PASSWORD}
        one = contracts.AccountLookupResponse(users=[summary])
        self.assertEqual(one.model_dump(mode="json"), {
            "users": [{**self.account_summary(), "created_at": "2026-10-23T12:00:00Z"}],
        })

    def test_naive_database_created_at_is_normalized_to_utc(self):
        contracts = self.admin_contracts()
        data = self.account_summary()
        data["created_at"] = datetime(2026, 10, 23, 12, 0)
        account = SimpleNamespace(**data)
        summary = contracts.AdminAccountSummary.model_validate(account)
        self.assertEqual(summary.created_at.utcoffset(), timezone.utc.utcoffset(summary.created_at))
        with self.assertRaises(ValidationError):
            contracts.AccountLookupResponse(users=[summary, summary])


class SharedAccountRouteTests(ContractHelpers, unittest.TestCase):
    def setUp(self):
        route = getattr(security, "AccountCreationRoute", None)
        self.assertIsNotNone(route, "Account creation must share a redacting HTTP route")
        contracts = self.admin_contracts()
        app = FastAPI()
        app.state.settings = SimpleNamespace(auth_allowed_origins=(ORIGIN,))
        router = APIRouter(route_class=route)

        @router.post("/test-accounts", response_model=contracts.CreateAccountResponse, status_code=201)
        def create(body: contracts.CreateAccountRequest):
            # Test-only endpoint exercises real parsing/serialization; it does not persist users.
            return {"user": {
                "id": "created-user", "display_name": body.display_name, "email": body.email,
                "system_role": body.system_role, "is_active": True,
                "created_at": datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc),
            }}

        @router.get("/test-status")
        def status():
            return {"ok": True}

        app.include_router(router)
        self.client = TestClient(app, base_url=ORIGIN)
        self.addCleanup(self.client.close)

    def test_valid_creation_uses_normalized_identity_without_returning_password(self):
        response = self.client.post("/test-accounts", headers={"Origin": ORIGIN},
                                    json=self.account_body(system_role="admin"))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["user"], {
            **self.account_summary(),
            "system_role": "admin",
            "created_at": "2026-10-23T12:00:00Z",
        })
        self.assertNotIn(PASSWORD, response.text)
        self.assertNotIn("set-cookie", response.headers)

    def test_field_errors_are_safe_and_specific(self):
        cases = (
            ({"password": "short"}, "password", "password_length"),
            ({"password": {"secret": PASSWORD}}, "password", "invalid_type"),
            ({"display_name": 9}, "display_name", "invalid_type"),
            ({"display_name": " "}, "display_name", "name_length"),
            ({"email": "bad"}, "email", "invalid_email"),
            ({"system_role": PASSWORD}, "system_role", "invalid_role"),
        )
        for change, field, code in cases:
            with self.subTest(change=change):
                response = self.client.post("/test-accounts", headers={"Origin": ORIGIN},
                                            json=self.account_body(**change))
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json(), {
                    "detail": {"code": "validation_error", "fields": {field: code}},
                })
                self.assertNotIn(PASSWORD, response.text)
                self.assertNotIn('"input"', response.text)
                self.assertNotIn('"ctx"', response.text)

    def test_missing_field_reports_required_without_echoing_other_fields(self):
        body = self.account_body()
        del body["email"]
        response = self.client.post("/test-accounts", headers={"Origin": ORIGIN}, json=body)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["fields"], {"email": "required"})
        self.assertNotIn(PASSWORD, response.text)

    def test_unknown_field_names_and_values_are_not_reflected(self):
        response = self.client.post("/test-accounts", headers={"Origin": ORIGIN},
                                    json=self.account_body(**{PASSWORD: PASSWORD}))
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json(), {"detail": {"code": "validation_error"}})
        self.assertNotIn(PASSWORD, response.text)

    def test_malformed_json_does_not_echo_submitted_secrets(self):
        response = self.client.post(
            "/test-accounts", headers={"Origin": ORIGIN, "Content-Type": "application/json"},
            content='{"password":"' + PASSWORD + '"',
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json(), {"detail": {"code": "validation_error"}})
        self.assertNotIn(PASSWORD, response.text)

    def test_origin_is_checked_before_parsing_sensitive_payloads(self):
        for headers in ({}, {"Origin": "https://untrusted.test"}):
            with self.subTest(headers=headers):
                response = self.client.post("/test-accounts", headers=headers,
                                            content='{"password":"' + PASSWORD + '"')
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), {"detail": {"code": "origin_not_allowed"}})
                self.assertNotIn(PASSWORD, response.text)

    def test_read_routes_do_not_require_a_write_origin(self):
        self.assertEqual(self.client.get("/test-status").json(), {"ok": True})


class AuthRoleResponseTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool,
                                    connect_args={"check_same_thread": False})
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine)
        with self.factory() as db:
            db.add(User(id="admin", email="admin@example.test", display_name="Admin",
                        password_hash=hash_password(PASSWORD), system_role="admin"))
            db.commit()
        app = FastAPI()
        app.include_router(auth_router)
        app.state.settings = SimpleNamespace(auth_allowed_origins=(ORIGIN,))
        app.state.session_factory = self.factory
        self.client = TestClient(app, base_url=ORIGIN)
        self.addCleanup(self.client.close)

    def test_login_and_session_return_the_role_from_the_database(self):
        logged = self.client.post("/auth/login", headers={"Origin": ORIGIN},
                                  json={"email": "admin@example.test", "password": PASSWORD})
        self.assertEqual(logged.status_code, 200)
        self.assertEqual(logged.json()["user"].get("system_role"), "admin")
        with self.factory() as db:
            db.get(User, "admin").system_role = "user"
            db.commit()
        session = self.client.get("/auth/session")
        self.assertEqual(session.status_code, 200)
        self.assertEqual(session.json()["user"]["system_role"], "user")
        self.assertEqual(session.json()["csrf_token"], logged.json()["csrf_token"])
        self.assertNotIn(PASSWORD, session.text)

    def test_registration_still_redacts_and_rejects_a_client_selected_role(self):
        response = self.client.post("/auth/register", headers={"Origin": ORIGIN}, json={
            "display_name": "New", "email": "new@example.test", "password": PASSWORD,
            "system_role": "admin",
        })
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "validation_error")
        self.assertNotIn(PASSWORD, response.text)
        with self.factory() as db:
            self.assertEqual(db.query(User).count(), 1)


class AdminApiTests(ContractHelpers, unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("ruvie.api.admin"), "Production admin routes must exist")
        self.admin_api = importlib.import_module("ruvie.api.admin")
        self.engine = create_engine("sqlite://", poolclass=StaticPool,
                                    connect_args={"check_same_thread": False})
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine)
        with self.factory() as db:
            for role in ("admin", "user"):
                db.add(User(id=role, email=f"{role}@example.test", display_name=role,
                            system_role=role, password_hash=hash_password(PASSWORD)))
            db.commit()
        self.app = FastAPI()
        self.app.include_router(auth_router)
        self.app.include_router(self.admin_api.router)
        self.app.state.settings = SimpleNamespace(auth_allowed_origins=(ORIGIN,))
        self.app.state.session_factory = self.factory
        self.client = self.browser()
        logged = self.login(self.client, "admin")
        self.identity = logged.json()
        self.csrf = self.identity["csrf_token"]
        self.token = self.client.cookies["ruvie_session"]
        self.headers = {"Origin": ORIGIN, "X-CSRF-Token": self.csrf}

    def browser(self):
        browser = TestClient(self.app, base_url=ORIGIN)
        self.addCleanup(browser.close)
        return browser

    def login(self, browser, role):
        result = browser.post("/auth/login", headers={"Origin": ORIGIN},
                              json={"email": f"{role}@example.test", "password": PASSWORD})
        self.assertEqual(result.status_code, 200, result.text)
        return result

    def create(self, browser=None, headers=None, **changes):
        return (browser or self.client).post("/admin/users", headers=self.headers if headers is None else headers,
                                             json=self.account_body(**changes))

    def assert_safe(self, response, status, code=None):
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertNotIn("set-cookie", response.headers)
        for secret in (PASSWORD, self.csrf, self.token):
            self.assertNotIn(secret, response.text)
        if code:
            self.assertEqual(response.json()["detail"]["code"], code)

    def assert_no_new_account(self):
        with self.factory() as db:
            self.assertEqual(db.query(User).count(), 2)
            self.assertEqual(db.query(AuditEvent).count(), 0)

    def test_admin_creates_both_roles_without_replacing_own_session(self):
        for role in ("user", "admin"):
            body = self.account_body(email=f"created-{role}@example.test")
            if role == "admin":
                body["system_role"] = role
            response = self.client.post("/admin/users", headers=self.headers, json=body)
            self.assert_safe(response, 201)
            self.assertEqual(set(response.json()), {"user"})
            summary = response.json()["user"]
            self.assertEqual(set(summary), {
                "id", "display_name", "email", "system_role", "is_active", "created_at",
            })
            self.assertIsNotNone(datetime.fromisoformat(summary["created_at"]))
            self.assertEqual((summary["email"], summary["system_role"], summary["is_active"]),
                             (f"created-{role}@example.test", role, True))
        self.assertEqual(self.client.cookies["ruvie_session"], self.token)
        self.assertEqual(self.client.get("/auth/session").json(), self.identity)
        with self.factory() as db:
            self.assertEqual(db.query(AuthSession).count(), 1)
            self.assertEqual(db.query(AuditEvent).count(), 2)
            self.assertEqual(db.query(Membership).count(), 0)
            self.assertEqual(db.query(AccessGrant).count(), 0)

    def test_anonymous_requests_are_denied_without_account_metadata(self):
        anonymous = self.browser()
        self.assert_safe(self.create(anonymous), 401, "authentication_required")
        response = anonymous.get("/admin/users", params={"email": "admin@example.test"})
        self.assert_safe(response, 401, "authentication_required")
        self.assertNotIn("admin@example.test", response.text)
        self.assert_no_new_account()

    def test_ordinary_user_cannot_forge_admin_via_headers_or_recipient_role(self):
        browser = self.browser()
        logged = self.login(browser, "user")
        headers = {"Origin": ORIGIN, "X-CSRF-Token": logged.json()["csrf_token"],
                   "X-User-Id": "admin", "X-System-Role": "admin"}
        self.assert_safe(self.create(browser, headers, system_role="admin"), 403, "admin_required")
        self.assert_safe(browser.get("/admin/users", params={"email": "admin@example.test"},
                                     headers=headers), 403, "admin_required")
        self.assert_no_new_account()

    def test_demotion_is_applied_to_the_next_request_even_with_existing_cookie(self):
        with self.factory() as db:
            db.get(User, "admin").system_role = "user"
            db.commit()
        self.assert_safe(self.create(), 403, "admin_required")
        self.assert_safe(self.client.get("/admin/users", params={"email": "user@example.test"}),
                         403, "admin_required")
        self.assertEqual(self.client.cookies["ruvie_session"], self.token)
        self.assert_no_new_account()

    def test_inactive_actor_is_unauthenticated_for_both_endpoints(self):
        with self.factory() as db:
            db.get(User, "admin").is_active = False
            db.commit()
        self.assert_safe(self.create(), 401, "authentication_required")
        self.assert_safe(self.client.get("/admin/users", params={"email": "user@example.test"}),
                         401, "authentication_required")
        self.assert_no_new_account()

    def test_expired_session_is_denied_without_creating_a_recipient_session(self):
        with self.factory() as db:
            db.scalar(select(AuthSession)).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        self.assert_safe(self.create(), 401, "authentication_required")
        self.assert_safe(self.client.get("/admin/users", params={"email": "user@example.test"}),
                         401, "authentication_required")
        self.assert_no_new_account()

    def test_missing_or_wrong_csrf_does_not_create_or_change_admin_session(self):
        other = self.browser()
        other_csrf = self.login(other, "user").json()["csrf_token"]
        for token in (None, "invalid-csrf", other_csrf):
            headers = {"Origin": ORIGIN}
            if token:
                headers["X-CSRF-Token"] = token
            self.assert_safe(self.create(headers=headers), 403, "csrf_invalid")
        self.assert_no_new_account()
        self.assertEqual(self.client.get("/auth/session").json(), self.identity)

    def test_origin_is_checked_before_parsing_sensitive_json(self):
        for headers in ({"X-CSRF-Token": self.csrf},
                        {"Origin": "https://untrusted.test", "X-CSRF-Token": self.csrf}):
            response = self.client.post("/admin/users", headers=headers,
                                        content='{"password":"' + PASSWORD + '"')
            self.assert_safe(response, 403, "origin_not_allowed")
        self.assert_no_new_account()

    def test_creation_validation_never_echoes_secret_values_or_arbitrary_field_names(self):
        for change in ({"password": {"secret": PASSWORD}}, {"system_role": PASSWORD},
                       {"actor_user_id": "admin"}, {PASSWORD: PASSWORD}):
            self.assert_safe(self.create(**change), 422, "validation_error")
        malformed = self.client.post("/admin/users", headers=self.headers,
                                      content='{"password":"' + PASSWORD + '"')
        self.assert_safe(malformed, 422, "validation_error")
        self.assert_no_new_account()

    def test_lookup_normalizes_email_and_returns_only_one_safe_inactive_summary(self):
        created = self.create()
        self.assert_safe(created, 201)
        with self.factory() as db:
            db.get(User, created.json()["user"]["id"]).is_active = False
            db.commit()
        response = self.client.get("/admin/users", params={"email": " AN@Example.test "})
        self.assert_safe(response, 200)
        self.assertEqual(response.json(), {"users": [{**created.json()["user"], "is_active": False}]})
        for email in ("absent@example.test", "%@example.test"):
            absent = self.client.get("/admin/users", params={"email": email})
            self.assert_safe(absent, 200)
            self.assertEqual(absent.json(), {"users": []})
        self.assertEqual(self.client.get("/auth/session").json(), self.identity)

    def test_lookup_missing_invalid_and_extra_query_values_are_redacted(self):
        cases = ({}, {"email": PASSWORD}, {"email": "x" * 321},
                 {"email": "user@example.test", PASSWORD: PASSWORD})
        for params in cases:
            with self.subTest(params=params):
                response = self.client.get("/admin/users", params=params)
                self.assert_safe(response, 422, "validation_error")
                self.assertNotIn('"input"', response.text)
                self.assertNotIn('"ctx"', response.text)

    def test_duplicate_email_including_inactive_preserves_existing_account(self):
        created = self.create()
        self.assert_safe(created, 201)
        for active in (True, False):
            with self.factory() as db:
                existing = db.get(User, created.json()["user"]["id"])
                existing.is_active = active
                before = (existing.password_hash, existing.system_role, existing.display_name)
                db.commit()
            response = self.create(email="AN@example.test", system_role="admin", password="replacement-password")
            self.assert_safe(response, 409, "email_taken")
            self.assertEqual(response.json()["detail"]["fields"], {"email": "email_taken"})
            with self.factory() as db:
                existing = db.get(User, created.json()["user"]["id"])
                self.assertEqual((existing.password_hash, existing.system_role, existing.display_name), before)
                self.assertEqual(existing.is_active, active)
                self.assertEqual(db.query(AuditEvent).count(), 1)

    def test_internal_creation_and_lookup_failures_return_only_safe_codes(self):
        import ruvie.services.admin as admin_service
        with patch.object(admin_service, "hash_password", side_effect=RuntimeError(PASSWORD)):
            self.assert_safe(self.create(), 500, "account_creation_failed")
        with patch.object(admin_service.AdminAccountService, "lookup_account", side_effect=SQLAlchemyError(PASSWORD)):
            response = self.client.get("/admin/users", params={"email": "user@example.test"})
            self.assert_safe(response, 503, "account_lookup_unavailable")
        self.assert_no_new_account()
        self.assertEqual(self.client.get("/auth/session").json(), self.identity)

    def test_service_rechecks_role_after_the_dependency_has_passed(self):
        from ruvie.dependencies import get_admin_user_id

        def identity_then_demotion():
            with self.factory() as db:
                db.get(User, "admin").system_role = "user"
                db.commit()
            return "admin"

        self.app.dependency_overrides[get_admin_user_id] = identity_then_demotion
        self.assert_safe(self.create(), 403, "admin_required")
        self.assert_no_new_account()


class AdminApiPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_f005_007_e2e as fixtures
        fixtures.F005007EndToEndTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        import test_f005_007_e2e as fixtures
        fixtures.F005007EndToEndTests.tearDownClass()

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("ruvie.api.admin"), "Production admin router must exist")
        import test_f005_007_e2e as fixtures
        self.fixture = fixtures.F005007EndToEndTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.factory = self.fixture.client.app.state.session_factory
        with self.factory() as db:
            db.get(User, "alpha").system_role = "admin"
            db.commit()
        self.csrf, _ = self.fixture._login("alpha@example.test")
        self.client = self.fixture.client
        self.token = self.client.cookies["ruvie_session"]
        self.headers = {"Origin": fixtures.ORIGIN, "X-CSRF-Token": self.csrf}

    def test_registered_router_creates_both_roles_and_lookup_without_changing_session(self):
        for role in ("user", "admin"):
            response = self.client.post("/admin/users", headers=self.headers, json={
                "display_name": "Recipient", "email": f"{role}-recipient@example.test",
                "password": PASSWORD, "system_role": role,
            })
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(response.headers.get("cache-control"), "no-store")
            self.assertNotIn("set-cookie", response.headers)
            self.assertNotIn(PASSWORD, response.text)
            found = self.client.get("/admin/users", params={"email": f"{role}-recipient@example.test"})
            self.assertEqual(found.json(), {"users": [response.json()["user"]]})
        self.assertEqual(self.client.cookies["ruvie_session"], self.token)
        self.assertEqual(self.client.get("/auth/session").json()["user"]["id"], "alpha")
        with self.factory() as db:
            self.assertEqual(db.query(AuthSession).count(), 1)

    def test_audit_failure_returns_safe_500_and_rolls_back_real_database(self):
        append = AuditEventWriter.append

        def failed_audit(*args, **kwargs):
            append(*args, **kwargs)
            raise SQLAlchemyError(PASSWORD)

        with patch.object(AuditEventWriter, "append", side_effect=failed_audit):
            response = self.client.post("/admin/users", headers=self.headers, json={
                "display_name": "Failure", "email": "failure@example.test", "password": PASSWORD,
            })
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(response.json(), {"detail": {"code": "account_creation_failed"}})
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertNotIn("set-cookie", response.headers)
        self.assertNotIn(PASSWORD, response.text)
        self.assertEqual(self.client.cookies["ruvie_session"], self.token)
        with self.factory() as db:
            self.assertEqual(db.query(User).count(), 2)
            self.assertEqual(db.query(AuditEvent).count(), 0)
            self.assertEqual(db.query(AuthSession).count(), 1)


if __name__ == "__main__":
    unittest.main()
