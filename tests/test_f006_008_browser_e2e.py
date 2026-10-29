"""Browser -> active API -> disposable PostgreSQL -> fake provider; no dev data."""

from dataclasses import replace
import os
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
import unittest

import uvicorn
import test_f005_007_e2e as fixtures


ROOT = Path(__file__).resolve().parents[1]


class F006008BrowserEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        if not cls.node or not os.environ.get("RUVIE_PLAYWRIGHT_PATH"):
            raise unittest.SkipTest("Build frontend and set RUVIE_PLAYWRIGHT_PATH for browser E2E; see README")
        if not (ROOT / "frontend/dist/index.html").is_file():
            raise unittest.SkipTest("Build frontend before browser E2E; see README")
        # Reuse the active migration/container fixture rather than a second DB bootstrap.
        fixtures.F005007EndToEndTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.F005007EndToEndTests.tearDownClass()

    def test_model_choice_persists_and_accounts_keep_private_citations(self):
        fixture = fixtures.F005007EndToEndTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        for account, project, title, content in (
            ("alpha", "project-alpha", "Alpha guide", b"ALPHA_PRIVATE_GUIDE: install from Alpha portal."),
            ("beta", "project-beta", "Beta guide", b"BETA_PRIVATE_GUIDE: confidential Beta instructions."),
        ):
            csrf, _token = fixture._login(f"{account}@example.test")
            uploaded = fixture._upload(csrf, project, title, content)
            self.assertEqual(uploaded.status_code, 202, uploaded.text)
            self.assertEqual(fixture._run_worker_once(), uploaded.json()["job_id"])

        with socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))
            frontend_port = reserved.getsockname()[1]
        origin = f"http://127.0.0.1:{frontend_port}"
        fixture.client.app.state.settings = replace(fixture.settings, auth_allowed_origins=(origin,))
        backend_socket = socket.socket()
        backend_socket.bind(("127.0.0.1", 0))
        backend_url = f"http://127.0.0.1:{backend_socket.getsockname()[1]}"
        # TestClient already owns resources. Uvicorn exposes those same services over HTTP.
        server = uvicorn.Server(uvicorn.Config(
            fixture.client.app, lifespan="off", log_level="warning", access_log=False,
        ))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [backend_socket]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(server.started, "Test API did not start")
            env = {
                **os.environ,
                "RUVIE_E2E_BACKEND_URL": backend_url,
                "RUVIE_E2E_FRONTEND_PORT": str(frontend_port),
                "RUVIE_E2E_PROVIDER_URL": fixture.settings.llm.base_url,
                "RUVIE_E2E_PASSWORD": fixtures.TEST_PASSWORD,
            }
            result = subprocess.run(
                [self.node, "tests/llm-e2e.mjs"], cwd=ROOT / "frontend",
                env=env, capture_output=True, text=True, timeout=90,
                encoding="utf-8", errors="replace",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Browser E2E: 2 accounts passed", result.stdout)
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            backend_socket.close()

        requests = fixture.provider_state.chat_requests
        self.assertEqual(len(requests), 2)
        for (body, headers), model, key, private, forbidden in (
            (requests[0], "b", "e2e-llm-key", "ALPHA_PRIVATE_GUIDE", "BETA_PRIVATE_GUIDE"),
            (requests[1], "a", "e2e-llm-key", "BETA_PRIVATE_GUIDE", "ALPHA_PRIVATE_GUIDE"),
        ):
            self.assertEqual(body["model"], model)
            self.assertEqual(headers["Authorization"], f"Bearer {key}")
            self.assertIn(private, str(body["messages"]))
            self.assertNotIn(forbidden, str(body["messages"]))
            self.assertNotIn("Cookie", headers)
