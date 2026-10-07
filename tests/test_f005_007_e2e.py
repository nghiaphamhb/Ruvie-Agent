"""End-to-end F005 coverage using disposable PostgreSQL and local fake providers."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4
import unittest
from unittest.mock import patch

import psycopg
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from ruvie.config import (
    EmbeddingProfile,
    EmbeddingProviderSettings,
    LlmProviderSettings,
    Settings,
)
from ruvie.models import DocumentChunk, DocumentRevision, IngestionJob, Membership, Project, Role, RoleCode, User
from ruvie.services.documents.ingestion import DocumentIngestionWorker
from ruvie.services.auth import hash_password


POSTGRES_IMAGE = "pgvector/pgvector:0.8.6-pg16-bookworm"
POSTGRES_USER = "f005_test"
POSTGRES_PASSWORD = "f005_test_only_password"
TEST_PASSWORD = "f005-test-password"
ORIGIN = "https://f005.test"


class FakeProviderState:
    def __init__(self) -> None:
        self.embedding_status = 200
        self.llm_status = 200
        self.models_status = 200
        self.models = [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}]
        self.model_headers = []
        self.embedding_inputs: list[object] = []
        self.prompts: list[object] = []
        self.chat_requests: list[tuple[dict, dict]] = []


class FakeProviderHandler(BaseHTTPRequestHandler):
    state: FakeProviderState

    def do_GET(self) -> None:
        if self.path == "/models":
            self.state.model_headers.append(dict(self.headers))
            self._json(self.state.models_status, {"data": self.state.models, "error": "private-provider-error"})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        size = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(size))
        if self.path == "/embeddings":
            self.state.embedding_inputs.append(body.get("input"))
            if self.state.embedding_status != 200:
                self._json(self.state.embedding_status, {"error": {"message": "fake provider failure"}})
                return
            inputs = body["input"]
            count = len(inputs) if isinstance(inputs, list) else 1
            self._json(200, {
                "data": [
                    {"object": "embedding", "index": index, "embedding": [1.0] + [0.0] * 1023}
                    for index in range(count)
                ]
            })
            return

        if self.path == "/chat/completions":
            self.state.prompts.append(body["messages"])
            self.state.chat_requests.append((body, dict(self.headers)))
            if self.state.llm_status != 200:
                self._json(self.state.llm_status, {"error": {"message": "fake provider failure"}})
                return
            payload = json.dumps({"choices": [{"delta": {"content": "Answer from Alpha's guide."}}]})
            data = f"data: {payload}\n\ndata: [DONE]\n\n".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self._json(404, {"error": "not found"})

    def _json(self, status: int, payload: dict[str, object]) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, _format: str, *_args: object) -> None:
        return


class F005007EndToEndTests(unittest.TestCase):
    container_id: str
    postgres_port: int

    @classmethod
    def setUpClass(cls) -> None:
        docker = shutil.which("docker")
        if docker is None:
            raise unittest.SkipTest("Docker is required for the disposable PostgreSQL E2E test")
        name = f"ruvie-f005-007-{uuid4().hex[:10]}"
        started = subprocess.run(
            [docker, "run", "--detach", "--rm", "--name", name,
             "--publish", "127.0.0.1::5432",
             "--env", f"POSTGRES_USER={POSTGRES_USER}",
             "--env", f"POSTGRES_PASSWORD={POSTGRES_PASSWORD}",
             "--env", f"POSTGRES_DB={POSTGRES_USER}", POSTGRES_IMAGE],
            capture_output=True, text=True, timeout=90,
        )
        if started.returncode != 0:
            raise RuntimeError(f"Could not start disposable pgvector container: {started.stderr.strip()}")
        cls.container_id = started.stdout.strip()
        mapped = subprocess.run(
            [docker, "port", cls.container_id, "5432/tcp"],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip().splitlines()[0]
        cls.postgres_port = int(mapped.rsplit(":", 1)[1])
        cls.docker = docker
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            try:
                with psycopg.connect(
                    host="127.0.0.1", port=cls.postgres_port, dbname=POSTGRES_USER,
                    user=POSTGRES_USER, password=POSTGRES_PASSWORD, connect_timeout=2,
                ):
                    return
            except psycopg.OperationalError:
                time.sleep(0.5)
        cls._stop_container()
        raise RuntimeError("Disposable PostgreSQL did not become ready within 45 seconds")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._stop_container()

    @classmethod
    def _stop_container(cls) -> None:
        container_id = getattr(cls, "container_id", None)
        docker = getattr(cls, "docker", shutil.which("docker"))
        if container_id and docker:
            subprocess.run([docker, "stop", container_id], capture_output=True, timeout=30)
            cls.container_id = ""

    def setUp(self) -> None:
        self.database = f"e2e_{uuid4().hex[:12]}"
        admin = psycopg.connect(
            host="127.0.0.1", port=self.postgres_port, dbname=POSTGRES_USER,
            user=POSTGRES_USER, password=POSTGRES_PASSWORD, autocommit=True,
        )
        with admin.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE "{self.database}"')
        admin.close()

        self.database_url = (
            f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
            f"@127.0.0.1:{self.postgres_port}/{self.database}"
        )
        settings_env = {
            "DATABASE_URL": self.database_url,
            "EMBEDDING_MODEL_ID": "fake-embedding-model",
            "EMBEDDING_DIMENSION": "1024",
            "EMBEDDING_DISTANCE_METRIC": "cosine",
        }
        with patch.dict(os.environ, settings_env):
            # Existing revision IDs exceed Alembic's default VARCHAR(32) bookkeeping column.
            with psycopg.connect(
                host="127.0.0.1", port=self.postgres_port, dbname=self.database,
                user=POSTGRES_USER, password=POSTGRES_PASSWORD,
            ) as connection:
                connection.execute(
                    "CREATE TABLE alembic_version (version_num VARCHAR(128) NOT NULL PRIMARY KEY)"
                )
            config = Config(str(BACKEND / "alembic.ini"))
            command.upgrade(config, "head")

        self.provider_state = FakeProviderState()
        FakeProviderHandler.state = self.provider_state
        self.provider = ThreadingHTTPServer(("127.0.0.1", 0), FakeProviderHandler)
        self.provider_thread = threading.Thread(target=self.provider.serve_forever, daemon=True)
        self.provider_thread.start()
        provider_url = f"http://127.0.0.1:{self.provider.server_port}"
        self.settings = Settings(
            database_url=self.database_url,
            embedding_profile=EmbeddingProfile("fake-embedding-model", 1024, "cosine"),
            embedding_provider=EmbeddingProviderSettings(provider_url, "e2e-embedding-key"),
            llm=LlmProviderSettings(provider_url, "fake-chat-model", "e2e-llm-key"),
            auth_allowed_origins=(ORIGIN,),
            llm_allowed_local_origins=(provider_url,),
        )
        self.blob_directory = TemporaryDirectory()

        from ruvie import main

        self.load_settings_patch = patch("ruvie.main.load_settings", return_value=self.settings)
        self.blob_root_patch = patch("ruvie.main.DEFAULT_BLOB_ROOT", Path(self.blob_directory.name))
        self.load_settings_patch.start()
        self.blob_root_patch.start()
        self.local_provider_proxy_patch = patch.dict(
            os.environ,
            {"NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"},
        )
        self.local_provider_proxy_patch.start()
        self.client = TestClient(main.app, base_url=ORIGIN)
        self.client.__enter__()
        self._seed_accounts()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.local_provider_proxy_patch.stop()
        self.load_settings_patch.stop()
        self.blob_root_patch.stop()
        self.blob_directory.cleanup()
        self.provider.shutdown()
        self.provider.server_close()
        self.provider_thread.join(timeout=5)
        admin = psycopg.connect(
            host="127.0.0.1", port=self.postgres_port, dbname=POSTGRES_USER,
            user=POSTGRES_USER, password=POSTGRES_PASSWORD, autocommit=True,
        )
        with admin.cursor() as cursor:
            cursor.execute(f'DROP DATABASE "{self.database}" WITH (FORCE)')
        admin.close()

    def test_user_llm_settings_persist_and_enforce_account_constraints(self):
        from sqlalchemy import inspect
        from sqlalchemy.exc import IntegrityError
        from ruvie import models

        model = getattr(models, "UserLlmSettings", None)
        self.assertIsNotNone(model, "Per-user LLM settings must be available after migration")
        factory = self.client.app.state.session_factory
        with factory() as session:
            session.add_all([
                model(user_id="alpha", base_url="https://alpha.example.test/v1", api_key="alpha-key", models=[{"id": "a", "name": "A"}], selected_model_id="a"),
                model(user_id="beta", selected_model_id="server-model"),
            ])
            session.commit()
        with factory() as session:
            alpha = session.get(model, "alpha")
            alpha.models = [{"id": "a2", "name": "A2"}]
            alpha.selected_model_id = "a2"
            session.commit()
        with factory() as session:
            alpha, beta = session.get(model, "alpha"), session.get(model, "beta")
            self.assertEqual((alpha.base_url, alpha.api_key, alpha.selected_model_id, alpha.models), ("https://alpha.example.test/v1", "alpha-key", "a2", [{"id": "a2", "name": "A2"}]))
            self.assertEqual((beta.base_url, beta.api_key, beta.selected_model_id, beta.models), (None, None, "server-model", []))
            beta.api_key = "invalid-without-url"
            beta.selected_model_id = "wrong-model"
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()
            self.assertEqual(session.get(model, "beta").selected_model_id, "server-model")
        for user_id in ("alpha", "missing-user"):
            with self.subTest(user_id=user_id), factory() as session:
                session.add(model(user_id=user_id))
                with self.assertRaises(IntegrityError):
                    session.commit()
        with factory() as session:
            session.add(User(id="temporary", email="temporary@example.test", display_name="Temporary"))
            session.commit()
            session.add(model(user_id="temporary"))
            session.commit()
            session.delete(session.get(User, "temporary"))
            session.commit()
            self.assertIsNone(session.get(model, "temporary"))
            self.assertIsNotNone(session.get(model, "alpha"))

        config = Config(str(BACKEND / "alembic.ini"))
        with patch.dict(os.environ, {"DATABASE_URL": self.database_url, "LLM_BASE_URL": "", "LLM_MODEL": "", "LLM_API_KEY": ""}):
            command.downgrade(config, "0007_audit_event_immutability")
            self.assertNotIn("user_llm_settings", inspect(self.client.app.state.engine).get_table_names())
            command.upgrade(config, "head")
        with factory() as session:
            session.add(model(user_id="beta", selected_model_id="restored-model"))
            session.commit()
            self.assertEqual(session.get(model, "beta").selected_model_id, "restored-model")

    def test_llm_connection_api_isolates_accounts_and_preserves_data_on_errors(self):
        from dataclasses import replace
        from ruvie.models import UserLlmSettings
        from sqlalchemy.exc import SQLAlchemyError

        self.assertTrue(hasattr(self.settings, "llm_allowed_local_origins"), "Local LLM origin settings are missing")
        provider_url = self.settings.llm.base_url
        self.client.app.state.settings = replace(self.settings, llm_allowed_local_origins=(provider_url,))
        alpha_login = self.client.post("/auth/login", headers={"Origin": ORIGIN}, json={"email": "alpha@example.test", "password": TEST_PASSWORD})
        self.assertEqual(alpha_login.status_code, 200, alpha_login.text)
        alpha = {"Origin": ORIGIN, "X-CSRF-Token": alpha_login.json()["csrf_token"], "Cookie": "ruvie_session=" + alpha_login.cookies["ruvie_session"]}
        beta_login = self.client.post("/auth/login", headers={"Origin": ORIGIN}, json={"email": "beta@example.test", "password": TEST_PASSWORD})
        beta = {"Origin": ORIGIN, "X-CSRF-Token": beta_login.json()["csrf_token"], "Cookie": "ruvie_session=" + beta_login.cookies["ruvie_session"]}
        for headers, key in ((alpha, "alpha-provider-key"), (beta, "beta-provider-key")):
            connected = self.client.put("/llm/connection", headers=headers, json={"base_url": provider_url, "api_key": key})
            self.assertEqual(connected.status_code, 200, connected.text)
        chosen = self.client.patch("/llm/connection/model", headers=alpha, json={"model_id": "b"})
        self.assertEqual(chosen.status_code, 200, chosen.text)
        self.assertEqual(self.client.get("/llm/connection", headers=alpha).json()["selected_model_id"], "b")
        self.assertEqual(self.client.get("/llm/connection", headers=beta).json()["selected_model_id"], "a")
        self.assertTrue(all("Cookie" not in headers for headers in self.provider_state.model_headers))
        self.assertEqual([headers.get("Authorization") for headers in self.provider_state.model_headers[:2]], ["Bearer alpha-provider-key", "Bearer beta-provider-key"])
        for headers in (alpha, beta):
            answer = self.client.post("/chat", headers=headers, json={"message": "Question"})
            self.assertEqual(answer.status_code, 200, answer.text)
            self.assertIn("event: completed", answer.text)
        self.assertEqual([body["model"] for body, _ in self.provider_state.chat_requests], ["b", "a"])
        self.assertEqual([headers.get("Authorization") for _, headers in self.provider_state.chat_requests], ["Bearer alpha-provider-key", "Bearer beta-provider-key"])
        self.assertTrue(all("Cookie" not in headers for _, headers in self.provider_state.chat_requests))
        self.provider_state.models = [{"id": "a"}]
        missing = self.client.get("/models", headers=alpha)
        self.assertTrue(missing.json()["selection_required"])
        before_queries = len(self.provider_state.embedding_inputs)
        rejected_chat = self.client.post("/chat", headers=alpha, json={"message": "Question"})
        self.assertEqual(rejected_chat.status_code, 422)
        self.assertEqual(len(self.provider_state.embedding_inputs), before_queries)
        self.assertEqual(len(self.provider_state.chat_requests), 2)
        self.assertEqual(self.client.patch("/llm/connection/model", headers=alpha, json={"model_id": "b"}).status_code, 422)
        self.provider_state.models_status = 401
        failed = self.client.put("/llm/connection", headers=alpha, json={"base_url": provider_url, "api_key": "invalid-key"})
        self.assertEqual(failed.status_code, 502)
        self.assertNotIn("private-provider-error", failed.text)
        self.provider_state.models_status = 200
        with patch("sqlalchemy.orm.Session.commit", side_effect=SQLAlchemyError("secret-database-error")):
            failed = self.client.put("/llm/connection", headers=alpha, json={"base_url": provider_url, "api_key": "new-key"})
        self.assertEqual(failed.status_code, 503)
        with self.client.app.state.session_factory() as session:
            stored = session.get(UserLlmSettings, "alpha")
            self.assertEqual((stored.api_key, stored.selected_model_id), ("alpha-provider-key", "b"))
        self.assertEqual(self.client.delete("/llm/connection", headers=alpha).status_code, 204)
        self.assertEqual(self.client.get("/llm/connection", headers=alpha).json()["source"], "server")
        self.assertEqual(self.client.get("/llm/connection", headers=beta).json()["source"], "personal")

    def _seed_accounts(self) -> None:
        with self.client.app.state.session_factory() as session:
            session.add_all((
                User(id="alpha", email="alpha@example.test", display_name="Alpha", password_hash=hash_password(TEST_PASSWORD)),
                User(id="beta", email="beta@example.test", display_name="Beta", password_hash=hash_password(TEST_PASSWORD)),
                Role(id="role-bim", code=RoleCode.BIM_CAD_SPECIALIST),
                Project(id="project-alpha", code="alpha", name="Alpha project"),
                Project(id="project-beta", code="beta", name="Beta project"),
            ))
            session.commit()
            session.add_all((
                Membership(id="membership-alpha", user_id="alpha", project_id="project-alpha", role_id="role-bim"),
                Membership(id="membership-beta", user_id="beta", project_id="project-beta", role_id="role-bim"),
            ))
            session.commit()

    def _login(self, email: str) -> tuple[str, str]:
        response = self.client.post(
            "/auth/login", json={"email": email, "password": TEST_PASSWORD}, headers={"Origin": ORIGIN}
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["csrf_token"], self.client.cookies.get("ruvie_session")

    def _use_session(self, token: str) -> None:
        self.client.cookies.set("ruvie_session", token, domain="f005.test", path="/")

    def _upload(self, csrf_token: str, project_id: str, title: str, content: bytes):
        return self.client.post(
            "/documents/upload",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf_token},
            data={
                "project_id": project_id, "title": title,
                "software": "Revit", "software_version": "2026",
            },
            files={"file": ("guide.txt", content, "text/plain")},
        )

    def _run_worker_once(self) -> str | None:
        factory = self.client.app.state.session_factory
        with factory() as session:
            return DocumentIngestionWorker(
                session,
                self.client.app.state.blob_store,
                self.client.app.state.query_embedder,
                self.settings.embedding_profile,
                session_factory=factory,
            ).run_next()

    def test_login_upload_worker_and_chat_return_only_alphas_citation(self) -> None:
        alpha_csrf, alpha_token = self._login("alpha@example.test")
        alpha_upload = self._upload(
            alpha_csrf, "project-alpha", "Alpha guide", b"ALPHA_PRIVATE_GUIDE: install from the Alpha portal."
        )
        beta_csrf, beta_token = self._login("beta@example.test")
        beta_upload = self._upload(
            beta_csrf, "project-beta", "Beta guide", b"BETA_PRIVATE_GUIDE: confidential Beta instructions."
        )
        self.assertEqual(alpha_upload.status_code, 202, alpha_upload.text)
        self.assertEqual(beta_upload.status_code, 202, beta_upload.text)
        alpha_revision = alpha_upload.json()["revision_id"]
        beta_revision = beta_upload.json()["revision_id"]

        self.assertEqual(
            {self._run_worker_once(), self._run_worker_once()},
            {alpha_upload.json()["job_id"], beta_upload.json()["job_id"]},
        )
        self._use_session(alpha_token)
        alpha_status = self.client.get(f"/documents/revisions/{alpha_revision}/status").json()
        with self.client.app.state.session_factory() as session:
            alpha_job = session.get(IngestionJob, alpha_upload.json()["job_id"])
            worker_diagnostic = (alpha_job.state.value, alpha_job.error_code, alpha_job.attempt_count)
        self.assertEqual(alpha_status["status"], "ready", (worker_diagnostic, self.provider_state.embedding_inputs))
        self._use_session(beta_token)
        self.assertEqual(self.client.get(f"/documents/revisions/{beta_revision}/status").json()["status"], "ready")
        self._use_session(alpha_token)
        self.assertEqual(self.client.get(f"/documents/revisions/{beta_revision}/status").status_code, 404)

        response = self.client.post("/chat", json={"message": "Where do I install the plugin?"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("event: citations", response.text)
        self.assertIn("event: completed", response.text)
        self.assertNotIn("BETA_PRIVATE_GUIDE", response.text)

        alpha_document_id = alpha_upload.json()["document_id"]
        beta_document_id = beta_upload.json()["document_id"]
        self.assertIn(alpha_document_id, response.text)
        self.assertNotIn(beta_document_id, response.text)
        self.assertIn(alpha_revision, response.text)
        alpha_prompt = str(self.provider_state.prompts[-1])
        self.assertIn("ALPHA_PRIVATE_GUIDE", alpha_prompt)
        self.assertNotIn("BETA_PRIVATE_GUIDE", alpha_prompt)
        self.assertEqual(self.client.get("/auth/session").status_code, 200)
        retrieved = self.client.post("/documents/retrieve", json={"query": "Where do I install the plugin?"})
        self.assertEqual(retrieved.status_code, 200, retrieved.text)
        self.assertIn(alpha_document_id, retrieved.text)
        self.assertNotIn(beta_document_id, retrieved.text)
        self.assertNotIn("BETA_PRIVATE_GUIDE", retrieved.text)

        with self.client.app.state.session_factory() as session:
            alpha_revision_row = session.get(DocumentRevision, alpha_revision)
            alpha_chunk = session.scalar(select(DocumentChunk).where(DocumentChunk.document_revision_id == alpha_revision))
            self.assertEqual(alpha_revision_row.ingestion_state.value, "ready")
            self.assertIn(alpha_chunk.id, response.text)
            self.assertIn(alpha_chunk.content_hash, response.text)
            self.assertIsNotNone(session.scalar(select(Role).where(Role.code == RoleCode.BIM_CAD_SPECIALIST)))
            self.assertIsNotNone(session.get(IngestionJob, alpha_upload.json()["job_id"]))

    def test_chat_hides_llm_http_failure_and_preserves_provider_credentials(self) -> None:
        csrf, _token = self._login("alpha@example.test")
        uploaded = self._upload(csrf, "project-alpha", "Alpha guide", b"ALPHA_PRIVATE_GUIDE")
        self.assertEqual(uploaded.status_code, 202, uploaded.text)
        self._run_worker_once()
        self.provider_state.llm_status = 503

        response = self.client.post("/chat", json={"message": "What is in the guide?"})

        self.assertEqual(response.status_code, 200)
        self.assertIn('"code":"provider_unavailable"', response.text)
        self.assertNotIn("fake provider failure", response.text)
        self.assertNotIn("e2e-llm-key", response.text)
        self.assertNotIn("ALPHA_PRIVATE_GUIDE", response.text)

    def test_worker_provider_http_failure_is_recorded_as_safe_retryable_status(self) -> None:
        csrf, _token = self._login("alpha@example.test")
        uploaded = self._upload(csrf, "project-alpha", "Alpha guide", b"ALPHA_PRIVATE_GUIDE")
        self.assertEqual(uploaded.status_code, 202, uploaded.text)
        self.provider_state.embedding_status = 503

        self.assertEqual(self._run_worker_once(), uploaded.json()["job_id"])
        status = self.client.get(f"/documents/revisions/{uploaded.json()['revision_id']}/status")

        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["status"], "pending")
        with self.client.app.state.session_factory() as session:
            job = session.get(IngestionJob, uploaded.json()["job_id"])
            self.assertEqual(job.error_code, "provider_unavailable")
            self.assertEqual(job.attempt_count, 1)


if __name__ == "__main__":
    unittest.main()
