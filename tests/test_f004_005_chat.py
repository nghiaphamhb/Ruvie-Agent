import importlib.util
import json
import sys
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.models import (
    AccessGrant, AuditEvent, Base, Document, DocumentChunk, DocumentRevision, Membership,
    Project, RevisionIngestionState, Role, RoleCode, User,
)


class TrackedSession(Session):
    last: "TrackedSession | None" = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.closed = False
        TrackedSession.last = self

    def close(self) -> None:
        self.closed = True
        super().close()


class FakeEmbedder:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_query(self, query: str) -> list[float]:
        self.queries.append(query)
        return [0.0] * 1024


class CapturingLlm:
    def __init__(self, deltas: list[str] | None = None, error: Exception | None = None) -> None:
        self.deltas = deltas if deltas is not None else ["Install", " the plugin."]
        self.error = error
        self.messages: list[dict[str, str]] | None = None

    def stream(self, messages: list[dict[str, str]]):
        self.messages = messages
        yield from self.deltas
        if self.error:
            raise self.error


def parse_events(response) -> list[tuple[str, dict[str, object]]]:
    frames = response.text.strip().split("\n\n")
    return [
        (frame.splitlines()[0].removeprefix("event: "), json.loads(frame.splitlines()[1].removeprefix("data: ")))
        for frame in frames
    ]


class ChatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        event.listen(self.engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, class_=TrackedSession)
        self._seed_documents()

    def tearDown(self) -> None:
        self.engine.dispose()

    def _seed_documents(self) -> None:
        with Session(self.engine) as session:
            session.add_all((
                User(id="alpha", email="alpha@example.test", display_name="Alpha"),
                User(id="beta", email="beta@example.test", display_name="Beta"),
                User(id="outsider", email="outsider@example.test", display_name="Outsider"),
                Role(id="role", code=RoleCode.BIM_CAD_SPECIALIST),
                Project(id="project-alpha", code="alpha", name="Alpha"),
                Project(id="project-beta", code="beta", name="Beta"),
            ))
            session.commit()
            for name in ("alpha", "beta"):
                session.add(Membership(id=f"membership-{name}", user_id=name, project_id=f"project-{name}", role_id="role"))
                session.add(Document(id=f"document-{name}", project_id=f"project-{name}", title=f"{name} guide", allowed_role_codes=[RoleCode.BIM_CAD_SPECIALIST.value]))
            session.commit()
            for name in ("alpha", "beta"):
                session.add(DocumentRevision(
                    id=f"revision-{name}", document_id=f"document-{name}", project_id=f"project-{name}",
                    revision_number=1, content_hash=name[0] * 64, blob_uri="file:///private",
                    mime_type="text/plain", size_bytes=20, software="Revit", software_version="2026",
                    ingestion_state=RevisionIngestionState.READY, embedding_model_id="model",
                    embedding_dimension=1024,
                    embedding_distance_metric="cosine",
                ))
            session.commit()
            for name in ("alpha", "beta"):
                session.add(DocumentChunk(
                    id=f"chunk-{name}", document_revision_id=f"revision-{name}",
                    document_id=f"document-{name}", project_id=f"project-{name}", ordinal=0,
                    text=f"{name}-private-text", content_hash=name[0] * 64,
                    start_offset=0, end_offset=18, software="Revit", software_version="2026",
                    embedding=[0.0] * 1024,
                ))
            session.commit()

    def _client(self, embedder=None, llm=None) -> TestClient:
        self.assertIsNotNone(importlib.util.find_spec("ruvie.api.chat"))
        from ruvie.api.chat import router

        app = FastAPI()
        app.include_router(router)
        app.state.session_factory = self.session_factory
        app.state.query_embedder = embedder
        app.state.settings = SimpleNamespace(llm=None, llm_allowed_local_origins=())
        def resolve(_service, _user_id, _model_id=None):
            if llm is None:
                from ruvie.services.llm import LlmNotConfiguredError
                raise LlmNotConfiguredError
            return llm
        provider_patch = patch("ruvie.services.llm.LlmConnectionService.resolve_chat_adapter", resolve)
        provider_patch.start()
        self.addCleanup(provider_patch.stop)

        @app.middleware("http")
        async def trusted_test_identity(request: Request, call_next):
            request.state.domain_user_id = request.headers.get("x-test-user")
            return await call_next(request)

        return TestClient(app)

    def test_prepare_closes_session_before_stream_and_returns_only_authorized_hits(self) -> None:
        self.assertIsNotNone(importlib.util.find_spec("ruvie.services.chat"))
        from ruvie.services.chat import ChatService

        llm = CapturingLlm()
        service = ChatService(FakeEmbedder(), SimpleNamespace(), self.session_factory)
        with patch("ruvie.services.llm.LlmConnectionService.resolve_chat_adapter", return_value=llm):
            hits = service.prepare("alpha", "Install plugin").hits

        self.assertEqual([hit.chunk_id for hit in hits], ["chunk-alpha"])
        self.assertTrue(TrackedSession.last.closed)
        with Session(self.engine) as session:
            audits = list(session.scalars(select(AuditEvent)))
        self.assertEqual([(audit.actor_user_id, audit.outcome) for audit in audits], [("alpha", "allow")])

    def test_http_streams_deltas_then_authorized_citation_then_completed(self) -> None:
        llm = CapturingLlm()
        with self._client(FakeEmbedder(), llm) as client:
            response = client.post("/chat", json={"message": "  Install plugin  "}, headers={"x-test-user": "alpha"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        events = parse_events(response)
        self.assertEqual([name for name, _ in events], ["delta", "delta", "citations", "completed"])
        self.assertEqual("".join(data["text"] for name, data in events if name == "delta"), "Install the plugin.")
        self.assertEqual(events[2][1]["citations"][0]["citation_id"], "document-alpha:revision-alpha:chunk-alpha")
        self.assertEqual(events[2][1]["citations"][0]["source_hash"], "a" * 64)
        self.assertIn("alpha-private-text", str(llm.messages))
        self.assertNotIn("beta-private-text", str(llm.messages))
        self.assertIn("Install plugin", str(llm.messages))

    def test_beta_chat_excludes_alpha_and_preserves_citation_provenance(self) -> None:
        llm = CapturingLlm(["Beta answer"])
        with self._client(FakeEmbedder(), llm) as client:
            response = client.post("/chat", json={"message": "Install plugin"}, headers={"x-test-user": "beta"})

        self.assertEqual(response.status_code, 200)
        events = parse_events(response)
        self.assertEqual([name for name, _ in events], ["delta", "citations", "completed"])
        self.assertEqual(events[1][1]["citations"], [{
            "citation_id": "document-beta:revision-beta:chunk-beta",
            "document_id": "document-beta",
            "revision_id": "revision-beta",
            "chunk_id": "chunk-beta",
            "ordinal": 0,
            "start_offset": 0,
            "end_offset": 18,
            "title": "beta guide",
            "source_hash": "b" * 64,
            "software": "Revit",
            "software_version": "2026",
        }])
        self.assertIn("beta-private-text", str(llm.messages))
        self.assertNotIn("alpha-private-text", str(llm.messages))
        self.assertNotIn("alpha-private-text", response.text)

    def test_direct_grant_allows_its_document_across_projects(self) -> None:
        with Session(self.engine) as session:
            session.add(AccessGrant(id="beta-to-alpha", resource_id="document-beta", principal_id="alpha"))
            session.commit()

        llm = CapturingLlm(["Granted answer"])
        with self._client(FakeEmbedder(), llm) as client:
            response = client.post("/chat", json={"message": "Install plugin"}, headers={"x-test-user": "alpha"})

        events = parse_events(response)
        self.assertEqual([name for name, _ in events], ["delta", "citations", "completed"])
        self.assertEqual(
            {citation["document_id"] for citation in events[1][1]["citations"]},
            {"document-alpha", "document-beta"},
        )
        self.assertIn("alpha-private-text", str(llm.messages))
        self.assertIn("beta-private-text", str(llm.messages))

    def test_rejects_missing_identity_and_client_scope_fields(self) -> None:
        with self._client(FakeEmbedder(), CapturingLlm()) as client:
            unauthenticated = client.post("/chat", json={"message": "Install plugin"})
            injected = client.post("/chat", json={"message": "Install plugin", "project_id": "project-beta"}, headers={"x-test-user": "alpha"})
            blank = client.post("/chat", json={"message": "   "}, headers={"x-test-user": "alpha"})

        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(injected.status_code, 422)
        self.assertEqual(blank.status_code, 422)
        with Session(self.engine) as session:
            self.assertEqual(list(session.scalars(select(AuditEvent))), [])

    def test_rejects_client_scope_and_provider_fields_before_provider_calls(self) -> None:
        embedder = FakeEmbedder()
        llm = CapturingLlm()
        injected_fields = {
            "user_id": "beta",
            "project_id": "project-beta",
            "document_id": "document-beta",
            "document_ids": ["document-beta"],
            "authorized_scope": {"project_id": "project-beta"},
            "model": "attacker-model",
            "base_url": "https://attacker.example.test",
            "api_key": "attacker-key",
        }
        with self._client(embedder, llm) as client:
            for field, value in injected_fields.items():
                with self.subTest(field=field):
                    response = client.post(
                        "/chat", json={"message": "Install plugin", field: value}, headers={"x-test-user": "alpha"}
                    )
                    self.assertEqual(response.status_code, 422)
            self.assertEqual(client.post("/chat", json={}, headers={"x-test-user": "alpha"}).status_code, 422)

        self.assertEqual(embedder.queries, [])
        self.assertIsNone(llm.messages)
        with Session(self.engine) as session:
            self.assertEqual(list(session.scalars(select(AuditEvent))), [])

    def test_no_authorized_hits_still_streams_answer_without_citations(self) -> None:
        llm = CapturingLlm(["General answer"])
        with self._client(FakeEmbedder(), llm) as client:
            response = client.post("/chat", json={"message": "Install plugin"}, headers={"x-test-user": "outsider"})

        self.assertEqual([name for name, _ in parse_events(response)], ["delta", "completed"])
        self.assertNotIn("private-text", str(llm.messages))
        self.assertNotIn("citations", response.text)
        with Session(self.engine) as session:
            audit = session.scalar(select(AuditEvent))
        self.assertEqual((audit.actor_user_id, audit.outcome), ("outsider", "deny"))

    def test_missing_provider_returns_safe_sse_error(self) -> None:
        with self._client(None, CapturingLlm()) as client:
            response = client.post("/chat", json={"message": "Install plugin"}, headers={"x-test-user": "alpha"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([name for name, _ in parse_events(response)], ["error"])
        self.assertEqual(parse_events(response)[0][1]["code"], "provider_unavailable")

    def test_missing_llm_provider_returns_safe_sse_error_without_retrieval(self) -> None:
        embedder = FakeEmbedder()
        with self._client(embedder, None) as client:
            response = client.post("/chat", json={"message": "Install plugin"}, headers={"x-test-user": "alpha"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([name for name, _ in parse_events(response)], ["error"])
        self.assertEqual(parse_events(response)[0][1]["code"], "provider_unavailable")
        self.assertEqual(embedder.queries, [])
        with Session(self.engine) as session:
            self.assertEqual(list(session.scalars(select(AuditEvent))), [])

    def test_embedding_failure_returns_safe_error_before_retrieval(self) -> None:
        class FailingEmbedder:
            def embed_query(self, query: str) -> list[float]:
                raise httpx.ConnectError("secret embedding url")

        with self._client(FailingEmbedder(), CapturingLlm()) as client:
            response = client.post("/chat", json={"message": "Install plugin"}, headers={"x-test-user": "alpha"})

        self.assertEqual([name for name, _ in parse_events(response)], ["error"])
        self.assertEqual(parse_events(response)[0][1]["code"], "provider_unavailable")
        self.assertNotIn("secret embedding url", response.text)
        with Session(self.engine) as session:
            self.assertEqual(list(session.scalars(select(AuditEvent))), [])

    def test_llm_failure_after_delta_ends_with_safe_error(self) -> None:
        llm = CapturingLlm(["Partial"], httpx.ConnectError("secret upstream url"))
        with self._client(FakeEmbedder(), llm) as client:
            response = client.post("/chat", json={"message": "Install plugin"}, headers={"x-test-user": "alpha"})

        self.assertEqual([name for name, _ in parse_events(response)], ["delta", "error"])
        self.assertEqual(parse_events(response)[1][1]["code"], "provider_unavailable")
        self.assertNotIn("secret upstream url", response.text)

    def test_invalid_llm_stream_returns_generation_failed(self) -> None:
        llm = CapturingLlm([], ValueError("secret upstream body"))
        with self._client(FakeEmbedder(), llm) as client:
            response = client.post("/chat", json={"message": "Install plugin"}, headers={"x-test-user": "alpha"})

        self.assertEqual([name for name, _ in parse_events(response)], ["error"])
        self.assertEqual(parse_events(response)[0][1]["code"], "generation_failed")
        self.assertNotIn("secret upstream body", response.text)

    def test_empty_llm_stream_returns_error_without_citation_or_completion(self) -> None:
        with self._client(FakeEmbedder(), CapturingLlm([])) as client:
            response = client.post("/chat", json={"message": "Install plugin"}, headers={"x-test-user": "alpha"})

        self.assertEqual(response.status_code, 200)
        events = parse_events(response)
        self.assertEqual([name for name, _ in events], ["error"])
        self.assertEqual(events[0][1]["code"], "generation_failed")
        self.assertTrue(events[0][1]["message"])

    def test_unusable_embedding_is_safe_provider_error(self):
        class InvalidEmbedder:
            def embed_query(self, _query):
                raise ValueError("private vector details")
        with self._client(InvalidEmbedder(), CapturingLlm()) as client:
            response = client.post("/chat", json={"message": "Question"}, headers={"x-test-user": "alpha"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(parse_events(response)[0][1]["code"], "provider_unavailable")
        self.assertNotIn("private vector details", response.text)

    def test_active_application_registers_chat_route(self) -> None:
        from ruvie.main import app

        response = TestClient(app).post(
            "/chat", json={"message": "Install plugin"},
            headers={"x-test-user": "alpha", "x-user-id": "alpha", "x-project-id": "project-alpha"},
        )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
