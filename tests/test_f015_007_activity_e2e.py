"""Real browser account deactivation against disposable PostgreSQL."""
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
from ruvie.models import AccessGrant, AuditEvent, Document, Membership, User, UserLlmSettings
from ruvie.services.auth import hash_password
import test_f005_007_e2e as fixtures

class ActivityEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.F005007EndToEndTests.setUpClass()
    @classmethod
    def tearDownClass(cls):
        fixtures.F005007EndToEndTests.tearDownClass()
    def test_admin_deactivates_and_reactivates_user(self):
        self._run_activity('user')

    def test_admin_deactivates_and_reactivates_other_admin(self):
        self._run_activity('admin')

    def _run_activity(self, target_role):
        root = Path(__file__).resolve().parents[1]
        node = shutil.which('node')
        if not node or not os.environ.get('RUVIE_PLAYWRIGHT_PATH') or not (root / 'frontend/dist/index.html').is_file():
            self.skipTest('Build frontend and configure Playwright/Chromium; see README')
        fixture = fixtures.F005007EndToEndTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        factory = fixture.client.app.state.session_factory
        password = 'e2e-password-123'
        with factory() as db:
            actor, target = db.get(User, 'alpha'), db.get(User, 'beta')
            actor.system_role, actor.is_active, actor.password_hash = 'admin', True, hash_password(password)
            target.system_role, target.is_active, target.password_hash = target_role, True, hash_password(password)
            db.add(User(id='gamma', email='gamma@example.test', display_name='Gamma',
                        system_role='user', is_active=True, password_hash=hash_password(password)))
            db.add(Document(id='preserved-doc', project_id='project-beta', title='Preserved guide'))
            db.add(UserLlmSettings(user_id='beta', selected_model_id=None))
            db.commit()
            target_hash = target.password_hash
            memberships = list(db.execute(select(Membership.__table__)))
            grants = list(db.execute(select(AccessGrant.__table__)))
            documents = list(db.execute(select(Document.__table__)))
            settings = list(db.execute(select(UserLlmSettings.__table__)))
        with socket.socket() as reserved:
            reserved.bind(('127.0.0.1', 0))
            frontend_port = reserved.getsockname()[1]
        origin = f'http://127.0.0.1:{frontend_port}'
        fixture.client.app.state.settings = replace(fixture.settings, auth_allowed_origins=(origin,))
        backend_socket = socket.socket()
        backend_socket.bind(('127.0.0.1', 0))
        backend_url = f'http://127.0.0.1:{backend_socket.getsockname()[1]}'
        server = uvicorn.Server(uvicorn.Config(fixture.client.app, lifespan='off', log_level='warning', access_log=False))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [backend_socket]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue(server.started)
            env = {**os.environ, 'RUVIE_E2E_BACKEND_URL': backend_url, 'RUVIE_E2E_FRONTEND_PORT': str(frontend_port), 'RUVIE_E2E_CURRENT_PASSWORD': password}
            result = subprocess.run([node, 'tests/admin-activity-e2e.mjs'], cwd=root / 'frontend', env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('F015 activity E2E checks passed:', result.stdout)
            with factory() as db:
                target = db.get(User, 'beta')
                self.assertTrue(target.is_active)
                self.assertEqual(target.password_hash, target_hash)
                self.assertEqual(target.system_role, target_role)
                self.assertEqual(list(db.execute(select(Membership.__table__))), memberships)
                self.assertEqual(list(db.execute(select(AccessGrant.__table__))), grants)
                self.assertEqual(list(db.execute(select(Document.__table__))), documents)
                self.assertEqual(list(db.execute(select(UserLlmSettings.__table__))), settings)
                events = list(db.scalars(select(AuditEvent).where(AuditEvent.resource_id == 'beta', AuditEvent.action.in_(['account.activate', 'account.deactivate']))))
                self.assertEqual({event.action for event in events}, {'account.activate', 'account.deactivate'})
                self.assertTrue(all(event.actor_user_id == 'alpha' for event in events))
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            backend_socket.close()
