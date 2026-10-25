"""Account workflows against active routes, real PostgreSQL and production browser UI."""
from dataclasses import replace
from datetime import datetime
import os
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import select
import uvicorn

import test_f005_007_e2e as fixtures
from ruvie.models import AccessGrant, AuditEvent, AuthSession, Membership, User

PASSWORD = " provisioned-password-123 "
PRIVATE_TEXT = "F012_PRIVATE_GUIDE"


class AccountsEndToEndTests(unittest.TestCase):
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
            db.get(User, "alpha").system_role = "admin"
            db.commit()
        self.csrf, _ = self.fixture._login("alpha@example.test")
        uploaded = self.fixture._upload(self.csrf, "project-alpha", "Private guide", PRIVATE_TEXT.encode())
        self.assertEqual(uploaded.status_code, 202, uploaded.text)
        self.fixture._run_worker_once()
        self.revision = uploaded.json()["revision_id"]

    def test_created_roles_login_without_grants_or_private_passages_and_keep_actor_session(self):
        """Create through HTTP, log in separately and check the real retrieval/chat boundary."""
        client = self.fixture.client
        original = client.get("/auth/session").json()
        cookie = client.cookies.get("ruvie_session")
        with self.factory() as db:
            sessions_before = db.query(AuthSession).count()
        for index, role in enumerate(("user", "admin")):
            with self.subTest(role=role):
                created = client.post("/admin/users", headers={"Origin": fixtures.ORIGIN, "X-CSRF-Token": self.csrf}, json={
                    "display_name": f"Created {role}", "email": f"created-{role}@example.test",
                    "password": PASSWORD, "system_role": role,
                })
                self.assertEqual(created.status_code, 201, created.text)
                self.assertNotIn("set-cookie", created.headers)
                summary = created.json()["user"]
                self.assertEqual(set(summary), {
                    "id", "display_name", "email", "system_role", "is_active", "created_at",
                })
                self.assertIsNotNone(datetime.fromisoformat(summary["created_at"]))
                self.assertEqual(client.get("/auth/session").json(), original)
                self.assertEqual(client.cookies.get("ruvie_session"), cookie)
                with self.factory() as db:
                    self.assertEqual(db.query(AuthSession).count(), sessions_before + index)
                    self.assertEqual(db.query(AuthSession).filter_by(user_id=summary["id"]).count(), 0)
                    self.assertEqual(db.query(Membership).filter_by(user_id=summary["id"]).count(), 0)
                    self.assertEqual(db.query(AccessGrant).filter_by(principal_id=summary["id"]).count(), 0)
                recipient = TestClient(client.app, base_url=fixtures.ORIGIN)
                self.addCleanup(recipient.close)
                login = recipient.post("/auth/login", headers={"Origin": fixtures.ORIGIN}, json={"email": summary["email"], "password": PASSWORD})
                self.assertEqual(login.status_code, 200, login.text)
                self.assertEqual(login.json()["user"]["system_role"], role)
                headers = {"Origin": fixtures.ORIGIN, "X-CSRF-Token": login.json()["csrf_token"]}
                self.assertEqual(recipient.get("/projects").json(), {"items": []})
                self.assertEqual(recipient.get(f"/documents/revisions/{self.revision}/status").status_code, 404)
                retrieved = recipient.post("/documents/retrieve", headers=headers, json={"query": PRIVATE_TEXT})
                self.assertEqual(retrieved.status_code, 200, retrieved.text)
                answer = recipient.post("/chat", headers=headers, json={"message": PRIVATE_TEXT})
                self.assertEqual(answer.status_code, 200, answer.text)
                self.assertIn("event: completed", answer.text)
                self.assertNotIn(self.revision, retrieved.text + answer.text)
                self.assertNotIn(PRIVATE_TEXT, retrieved.text)
                messages = self.fixture.provider_state.chat_requests[-1][0]["messages"]
                references = messages[-1]["content"].split("\n\nReferences:\n", 1)[1]
                self.assertEqual(references, "(none)")
                self.assertEqual(client.get("/auth/session").json(), original)
                forbidden = recipient.get("/admin/users?email=alpha@example.test")
                self.assertEqual(forbidden.status_code, 403 if role == "user" else 200)

    def test_setup_and_session_responses_forbid_caching_including_unauthenticated_session(self):
        """The feature contract requires HTTP cache headers, not only fetch cache options."""
        for path in ("/auth/setup", "/auth/session"):
            response = self.fixture.client.get(path)
            self.assertEqual(response.headers.get("cache-control"), "no-store", path)
        anonymous = TestClient(self.fixture.client.app, base_url=fixtures.ORIGIN)
        self.addCleanup(anonymous.close)
        response = anonymous.get("/auth/session")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers.get("cache-control"), "no-store")

    def test_browser_admin_provisions_roles_lost_response_lookup_and_delegation(self):
        """Production browser talks to this disposable API/database; providers stay local fakes."""
        root = Path(__file__).resolve().parents[1]
        node = shutil.which("node")
        if not node or not os.environ.get("RUVIE_PLAYWRIGHT_PATH") or not (root / "frontend/dist/index.html").is_file():
            self.skipTest("Build frontend and configure Playwright/browser; see README")
        with socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))
            frontend_port = reserved.getsockname()[1]
        origin = f"http://127.0.0.1:{frontend_port}"
        self.fixture.client.app.state.settings = replace(self.fixture.settings, auth_allowed_origins=(origin,))
        backend_socket = socket.socket()
        backend_socket.bind(("127.0.0.1", 0))
        backend_url = f"http://127.0.0.1:{backend_socket.getsockname()[1]}"
        server = uvicorn.Server(uvicorn.Config(self.fixture.client.app, lifespan="off", log_level="warning", access_log=False))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [backend_socket]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(server.started)
            env = {**os.environ, "RUVIE_E2E_BACKEND_URL": backend_url,
                   "RUVIE_E2E_FRONTEND_PORT": str(frontend_port), "RUVIE_E2E_PRIVATE_REVISION": self.revision}
            result = subprocess.run([node, "tests/admin-e2e.mjs"], cwd=root / "frontend", env=env,
                                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Admin E2E:", result.stdout)
            print(result.stdout.strip())
            with self.factory() as db:
                created = list(db.scalars(select(User).where(User.email.like("%@accounts.test"))))
                self.assertEqual(len(created), 5)
                self.assertEqual(sorted(user.system_role for user in created), ["admin", "admin", "user", "user", "user"])
                self.assertEqual(db.query(AuditEvent).filter_by(action="account.create").count(), 5)
                manager = next(user for user in created if user.email == "manager@accounts.test")
                for user in created:
                    self.assertEqual(db.query(Membership).filter_by(user_id=user.id).count(), 0)
                    self.assertEqual(db.query(AccessGrant).filter_by(principal_id=user.id).count(), 0)
                    event = db.scalar(select(AuditEvent).where(AuditEvent.action == "account.create", AuditEvent.resource_id == user.id))
                    self.assertEqual(event.actor_user_id, manager.id if user.email.startswith("delegated-") else "alpha")
                    self.assertNotIn(PASSWORD, event.reason)
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            backend_socket.close()
