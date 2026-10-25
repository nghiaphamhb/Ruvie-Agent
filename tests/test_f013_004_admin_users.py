"""F013-004: real account-list routes, database permissions and bounded pagination."""
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ruvie.api.admin import router
from ruvie.api.auth import router as auth_router
from ruvie.contracts import admin as contracts
from ruvie.models import AuthSession, Base, User
from ruvie.services.admin import AdminAccountService, AdminRequired, AuthenticationRequired
from ruvie.services.auth import hash_password
import test_f005_007_e2e as fixtures

ORIGIN = "https://list.test"
PASSWORD = "list-test-password"


class AdminUserListApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool,
                                    connect_args={"check_same_thread": False})
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine)
        with self.factory() as db:
            for identity, name, email, day, active, role in (
                ("actor", "Administrator", "actor@example.test", 20, True, "admin"),
                ("user", "Regular", "user@example.test", 21, True, "user"),
                ("d", "AN Other", "d@example.test", 22, True, "user"),
                ("c", "Team_100%/member", "special@example.test", 23, True, "user"),
                ("b", "Bình", "b@example.test", 23, False, "user"),
                ("a", "Nguyễn An", "a@example.test", 23, True, "user"),
            ):
                db.add(User(id=identity, display_name=name, email=email, system_role=role,
                            password_hash=hash_password(PASSWORD) if identity in ("actor", "user") else "private-hash",
                            is_active=active, created_at=datetime(2026, 10, day, 12, tzinfo=timezone.utc)))
            db.commit()
        self.app = FastAPI()
        self.app.include_router(auth_router)
        self.app.include_router(router)
        self.app.state.settings = SimpleNamespace(auth_allowed_origins=(ORIGIN,))
        self.app.state.session_factory = self.factory
        self.client = self.browser()
        self.login(self.client, "actor")
        self.cookie = self.client.cookies["ruvie_session"]

    def browser(self):
        client = TestClient(self.app, base_url=ORIGIN)
        self.addCleanup(client.close)
        return client

    def login(self, client, identity):
        response = client.post("/auth/login", headers={"Origin": ORIGIN},
                               json={"email": f"{identity}@example.test", "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)

    def listing(self, **query):
        response = self.client.get("/admin/users/list", params=query)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertNotIn("set-cookie", response.headers)
        return response.json()

    def test_pages_have_stable_ties_safe_metadata_and_include_inactive_accounts(self):
        pages = [self.listing(page=page, page_size=2) for page in (1, 2, 3, 4)]
        self.assertEqual([[user["id"] for user in page["users"]] for page in pages],
                         [["a", "b"], ["c", "d"], ["user", "actor"], []])
        for index, page in enumerate(pages, 1):
            self.assertEqual((page["total"], page["page"], page["page_size"]), (6, index, 2))
            for user in page["users"]:
                self.assertEqual(set(user), {"id", "display_name", "email", "system_role", "is_active", "created_at"})
                self.assertIsNotNone(datetime.fromisoformat(user["created_at"]).tzinfo)
        self.assertFalse(pages[0]["users"][1]["is_active"])
        self.assertEqual(self.client.cookies["ruvie_session"], self.cookie)
        with self.factory() as db:
            self.assertEqual(db.query(AuthSession).count(), 1)

    def test_search_matches_names_and_emails_counts_filtered_rows_and_escapes_wildcards(self):
        first = self.listing(q=" aN ", page_size=1)
        second = self.listing(q=" aN ", page=2, page_size=1)
        self.assertEqual((first["total"], first["users"][0]["id"], second["users"][0]["id"]), (2, "a", "d"))
        self.assertEqual([row["id"] for row in self.listing(q="B@EXAMPLE")["users"]], ["b"])
        for literal in ("%", "_", "/"):
            self.assertEqual([row["id"] for row in self.listing(q=literal)["users"]], ["c"])
        self.assertEqual(self.listing(q="missing")["total"], 0)
        blank = self.listing(q="   ")
        self.assertEqual((blank["total"], blank["page"], blank["page_size"]), (6, 1, 20))

    def test_invalid_queries_are_rejected_without_reflecting_user_input(self):
        for query in ({"page": 0}, {"page": -1}, {"page": 1000001}, {"page": "private-value"},
                      {"page": "1.5"}, {"page_size": 0}, {"page_size": 101}, {"q": "x" * 256},
                      {"actor_user_id": "private-value"}, {"q": "private-value", "extra": "secret"}):
            with self.subTest(query=query):
                response = self.client.get("/admin/users/list", params=query)
                self.assertEqual(response.status_code, 422, response.text)
                self.assertEqual(response.json(), {"detail": {"code": "validation_error"}})
                self.assertEqual(response.headers.get("cache-control"), "no-store")

    def test_untrusted_identity_cannot_read_and_current_admin_is_revalidated(self):
        anonymous = self.browser()
        ordinary = self.browser()
        self.login(ordinary, "user")
        for client, status in ((anonymous, 401), (ordinary, 403)):
            response = client.get("/admin/users/list", headers={"X-User-Id": "actor", "X-Role": "admin"})
            self.assertEqual(response.status_code, status)
            self.assertEqual(response.headers.get("cache-control"), "no-store")
            self.assertNotIn("example.test", response.text)
        with self.factory() as db:
            db.get(User, "actor").system_role = "user"
            db.commit()
        self.assertEqual(self.client.get("/admin/users/list").status_code, 403)
        with self.factory() as db:
            db.get(User, "actor").is_active = False
            db.commit()
        self.assertEqual(self.client.get("/admin/users/list").status_code, 401)

    def test_service_reloads_role_and_activity_even_for_an_identity_map_hit(self):
        query_type = getattr(contracts, "AccountListRequest", None)
        self.assertIsNotNone(query_type, "List query contract must exist")
        with self.factory() as db:
            actor = db.get(User, "actor")
            service = AdminAccountService(db)
            with self.factory() as changed:
                changed.get(User, "actor").system_role = "user"
                changed.commit()
            self.assertEqual(actor.system_role, "admin")
            with self.assertRaises(AdminRequired):
                service.list_accounts("actor", query_type())
            with self.factory() as changed:
                changed.get(User, "actor").is_active = False
                changed.commit()
            with self.assertRaises(AuthenticationRequired):
                service.list_accounts("actor", query_type())

    def test_database_failure_is_redacted_and_exact_email_lookup_stays_compatible(self):
        with patch.object(AdminAccountService, "list_accounts", create=True,
                          side_effect=SQLAlchemyError("private-hash password database")):
            response = self.client.get("/admin/users/list")
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json(), {"detail": {"code": "account_lookup_unavailable"}})
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        found = self.client.get("/admin/users?email=b@example.test")
        self.assertEqual(found.status_code, 200, found.text)
        self.assertEqual(set(found.json()), {"users"})
        self.assertEqual([user["id"] for user in found.json()["users"]], ["b"])


class AdminUserListPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.F005007EndToEndTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.F005007EndToEndTests.tearDownClass()

    def test_production_router_filters_and_paginates_postgres_without_exposing_credentials(self):
        fixture = fixtures.F005007EndToEndTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        factory = fixture.client.app.state.session_factory
        with factory() as db:
            db.get(User, "alpha").system_role = "admin"
            for identity in ("c", "b", "a"):
                db.add(User(id=identity, email=f"{identity}@page.test", display_name=f"Nguyễn_{identity}%",
                            password_hash="private-hash", is_active=identity != "b",
                            created_at=datetime(2026, 10, 23, tzinfo=timezone.utc)))
            db.commit()
        fixture._login("alpha@example.test")
        client = fixture.client
        for page, expected in ((1, ["a", "b"]), (2, ["c"]), (3, [])):
            response = client.get("/admin/users/list", params={"q": "NGUYỄN_", "page": page, "page_size": 2})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.headers.get("cache-control"), "no-store")
            self.assertEqual(response.json()["total"], 3)
            self.assertEqual([user["id"] for user in response.json()["users"]], expected)
            for secret in ("private-hash", fixtures.TEST_PASSWORD, client.cookies["ruvie_session"]):
                self.assertNotIn(secret, response.text)
        self.assertEqual(client.get("/admin/users/list", params={"q": "%"}).json()["total"], 3)
        with factory() as db:
            db.get(User, "alpha").system_role = "user"
            db.commit()
        self.assertEqual(client.get("/admin/users/list").status_code, 403)


if __name__ == "__main__":
    unittest.main()
