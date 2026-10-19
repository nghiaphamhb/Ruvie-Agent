"""Register using the active API and PostgreSQL; new accounts get no document access."""
from concurrent.futures import ThreadPoolExecutor
import threading
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
from dataclasses import replace
import uvicorn
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import func, select

import test_f005_007_e2e as fixtures
from ruvie.models import AuthSession, User, Membership, AccessGrant

PASSWORD = "registered-test-password"


class RegistrationPostgresTests(unittest.TestCase):
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

    def client(self):
        client = TestClient(self.fixture.client.app, base_url=fixtures.ORIGIN)
        self.addCleanup(client.close)
        return client

    def test_new_account_session_cannot_read_existing_private_revision_or_context(self):
        csrf, _ = self.fixture._login("alpha@example.test")
        uploaded = self.fixture._upload(csrf, "project-alpha", "Private guide", b"ALPHA_PRIVATE_GUIDE")
        self.assertEqual(uploaded.status_code, 202, uploaded.text)
        self.fixture._run_worker_once()
        revision = uploaded.json()["revision_id"]
        client = self.client()
        response = client.post("/auth/register", headers={"Origin": fixtures.ORIGIN},
            json={"display_name": "New Person", "email": "new@example.test", "password": PASSWORD})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(client.get("/auth/session").json(), response.json())
        self.assertEqual(client.get("/projects").json(), {"items": []})
        self.assertEqual(client.get(f"/documents/revisions/{revision}/status").status_code, 404)
        retrieved = client.post("/documents/retrieve", headers={"Origin": fixtures.ORIGIN,
            "X-CSRF-Token": response.json()["csrf_token"]}, json={"query": "ALPHA_PRIVATE_GUIDE"})
        self.assertEqual(retrieved.status_code, 200, retrieved.text)
        self.assertNotIn("ALPHA_PRIVATE_GUIDE", retrieved.text)
        self.assertNotIn(revision, retrieved.text)
        answer = client.post("/chat", headers={"Origin": fixtures.ORIGIN,
            "X-CSRF-Token": response.json()["csrf_token"]}, json={"message": "ALPHA_PRIVATE_GUIDE"})
        self.assertEqual(answer.status_code, 200, answer.text)
        self.assertNotIn(revision, answer.text)
        # The user's question may contain the string; document context must not.
        for body, _headers in self.fixture.provider_state.chat_requests:
            for message in body["messages"]:
                if message["role"] != "user":
                    self.assertNotIn("ALPHA_PRIVATE_GUIDE", message["content"])
        user_id = response.json()["user"]["id"]
        with self.fixture.client.app.state.session_factory() as db:
            self.assertEqual(db.query(Membership).filter_by(user_id=user_id).count(), 0)
            self.assertEqual(db.query(AccessGrant).filter_by(principal_id=user_id).count(), 0)

    def test_simultaneous_requests_create_one_user_and_one_registration_session(self):
        barrier = threading.Barrier(2)
        def submit(email):
            client = TestClient(self.fixture.client.app, base_url=fixtures.ORIGIN)
            try:
                barrier.wait(timeout=5)
                response = client.post("/auth/register", headers={"Origin": fixtures.ORIGIN},
                    json={"display_name": "Concurrent", "email": email, "password": PASSWORD})
                return response.status_code, response.json()
            finally:
                client.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, ["Concurrent@example.test", "concurrent@EXAMPLE.test"]))
        self.assertEqual(sorted(status for status, _ in results), [201, 409], results)
        with self.fixture.client.app.state.session_factory() as db:
            users = list(db.scalars(select(User).where(func.lower(User.email) == "concurrent@example.test")))
            self.assertEqual(len(users), 1)
            self.assertEqual(db.query(AuthSession).filter_by(user_id=users[0].id).count(), 1)

    def test_session_failure_leaves_no_postgres_account(self):
        from ruvie.services.auth import AuthService
        client = self.client()
        with patch.object(AuthService, "_stage_session", side_effect=RuntimeError("private failure")):
            response = client.post("/auth/register", headers={"Origin": fixtures.ORIGIN},
                json={"display_name": "Failure", "email": "failure@example.test", "password": PASSWORD})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private failure", response.text)
        with self.fixture.client.app.state.session_factory() as db:
            self.assertIsNone(db.scalar(select(User).where(User.email == "failure@example.test")))


    def test_browser_register_reload_logout_and_login_against_active_backend(self):
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
        server = uvicorn.Server(uvicorn.Config(
            self.fixture.client.app, lifespan="off", log_level="warning", access_log=False))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [backend_socket]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(server.started)
            env = {**os.environ, "RUVIE_E2E_BACKEND_URL": backend_url,
                   "RUVIE_E2E_FRONTEND_PORT": str(frontend_port)}
            result = subprocess.run([node, "tests/auth-e2e.mjs"], cwd=root / "frontend", env=env,
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Auth E2E: registration", result.stdout)
            with self.fixture.client.app.state.session_factory() as db:
                self.assertEqual(db.query(User).filter_by(email="browser-new@example.test").count(), 1)
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            backend_socket.close()


if __name__ == "__main__":
    unittest.main()

