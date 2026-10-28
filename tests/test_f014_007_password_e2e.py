"""Self-service password change through production UI and disposable PostgreSQL."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
import unittest
from dataclasses import replace

import uvicorn
from sqlalchemy import select

import test_f005_007_e2e as fixtures
from ruvie.models import AccessGrant, AuditEvent, AuthSession, Membership, User
from ruvie.services.auth import hash_password, verify_password

CURRENT = " current-password-123 "
NEW = " new-password-456 "
OTHER = " other-password-123 "
OTHER_EMAIL = "password-other@example.test"


class PasswordChangeEndToEndTests(unittest.TestCase):
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
            actor = db.get(User, "alpha")
            self.assertIsNotNone(actor)
            actor.password_hash = hash_password(CURRENT)
            actor.system_role = "user"
            db.query(AuthSession).filter_by(user_id=actor.id).delete()
            other = db.scalar(select(User).where(User.email == OTHER_EMAIL))
            if other is None:
                other = User(
                    id="password-other", email=OTHER_EMAIL, display_name="Password Other",
                    password_hash=hash_password(OTHER), system_role="user", is_active=True,
                )
                db.add(other)
            else:
                other.password_hash = hash_password(OTHER)
                other.system_role = "user"
                other.is_active = True
            db.query(AuthSession).filter_by(user_id=other.id).delete()
            db.commit()

    def test_user_can_change_password_and_only_their_other_session_is_revoked(self):
        self._run_browser("user")

    def test_admin_can_change_password_without_changing_role_or_other_account(self):
        self._run_browser("admin")

    def _run_browser(self, role):
        root = Path(__file__).resolve().parents[1]
        node = shutil.which("node")
        if not node or not os.environ.get("RUVIE_PLAYWRIGHT_PATH") or not (root / "frontend/dist/index.html").is_file():
            self.skipTest("Build frontend and configure Playwright/Chromium; see README")
        with self.factory() as db:
            actor = db.get(User, "alpha")
            actor.system_role = role
            db.commit()
            actor_identity = (actor.email, actor.display_name, actor.is_active, actor.created_at)
            other_hash = db.get(User, "password-other").password_hash
            memberships = list(db.execute(select(Membership.__table__)))
            grants = list(db.execute(select(AccessGrant.__table__)))
        with socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))
            frontend_port = reserved.getsockname()[1]
        origin = f"http://127.0.0.1:{frontend_port}"
        self.fixture.client.app.state.settings = replace(
            self.fixture.settings, auth_allowed_origins=(origin,),
        )
        backend_socket = socket.socket()
        backend_socket.bind(("127.0.0.1", 0))
        backend_url = f"http://127.0.0.1:{backend_socket.getsockname()[1]}"
        server = uvicorn.Server(uvicorn.Config(
            self.fixture.client.app, lifespan="off", log_level="warning", access_log=False,
        ))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [backend_socket]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(server.started)
            env = {
                **os.environ,
                "RUVIE_E2E_BACKEND_URL": backend_url,
                "RUVIE_E2E_FRONTEND_PORT": str(frontend_port),
                "RUVIE_E2E_CURRENT_PASSWORD": CURRENT,
                "RUVIE_E2E_NEW_PASSWORD": NEW,
                "RUVIE_E2E_OTHER_PASSWORD": OTHER,
                "RUVIE_E2E_ACTOR_EMAIL": "alpha@example.test",
                "RUVIE_E2E_OTHER_EMAIL": OTHER_EMAIL,
            }
            result = subprocess.run(
                [node, "tests/account-settings-e2e.mjs"], cwd=root / "frontend", env=env,
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("F014 password-change E2E checks passed:", result.stdout)
            with self.factory() as db:
                actor = db.get(User, "alpha")
                other = db.get(User, "password-other")
                self.assertTrue(verify_password(NEW, actor.password_hash))
                self.assertFalse(verify_password(CURRENT, actor.password_hash))
                self.assertEqual(actor.system_role, role)
                self.assertEqual((actor.email, actor.display_name, actor.is_active, actor.created_at), actor_identity)
                self.assertEqual(other.password_hash, other_hash)
                self.assertEqual(list(db.execute(select(Membership.__table__))), memberships)
                self.assertEqual(list(db.execute(select(AccessGrant.__table__))), grants)
                self.assertEqual(db.query(AuthSession).filter_by(user_id=actor.id).count(), 2)
                self.assertEqual(db.query(AuthSession).filter_by(user_id=other.id).count(), 1)
                events = list(db.scalars(select(AuditEvent).where(
                    AuditEvent.action == "account.password_change", AuditEvent.resource_id == actor.id,
                )))
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0].actor_user_id, actor.id)
                self.assertEqual(events[0].reason, "self_service")
                self.assertNotIn(CURRENT, events[0].reason)
                self.assertNotIn(NEW, events[0].reason)
            print(result.stdout.strip())
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            backend_socket.close()
