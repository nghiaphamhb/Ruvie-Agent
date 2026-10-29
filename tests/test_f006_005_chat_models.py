"""Model selection, isolation and snapshots through the real chat API/adapter."""
import json
from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import httpx
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import test_f004_005_chat as fixtures
from ruvie.config import LlmProviderSettings
from ruvie.models import UserLlmSettings, OrganizationLlmSettings, AuditEvent
from ruvie.services.llm_secrets import LlmSecretStore
from cryptography.fernet import Fernet
from ruvie.api.chat import router
from sqlalchemy import select

class ChatModelTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ChatTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.factory = self.fixture.session_factory
        self.embedder = fixtures.FakeEmbedder()
        self.settings = SimpleNamespace(llm=LlmProviderSettings("https://server.test/v1", "a", "server-key"), llm_allowed_local_origins=())
        self.settings.llm_settings_encryption_key = Fernet.generate_key().decode()
        with self.factory() as db:
            db.add(OrganizationLlmSettings(id=1,version=1,base_url="https://server.test/v1",
                api_key_ciphertext=LlmSecretStore(self.settings.llm_settings_encryption_key).encrypt("server-key"),
                allowed_model_ids=["a","b"],default_model_id="a"))
            db.commit()
        app = FastAPI()
        app.include_router(router)
        app.state.settings = self.settings
        app.state.session_factory = self.factory
        app.state.query_embedder = self.embedder
        app.state.llm_adapter = fixtures.CapturingLlm(["wrong shared answer"])
        @app.middleware("http")
        async def identity(request: Request, call_next):
            request.state.domain_user_id = request.headers.get("x-test-user")
            return await call_next(request)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.catalog = [{"id": "a"}, {"id": "b"}]
        self.calls = []
        self.models_status = 200
        self.http = httpx.Client(transport=httpx.MockTransport(self.provider))
        self.addCleanup(self.http.close)
        @contextmanager
        def request_client(adapter):
            yield self.http
        adapter_patch = patch("ruvie.adapters.llm.OpenAICompatibleLlmAdapter._request_client", request_client)
        adapter_patch.start()
        self.addCleanup(adapter_patch.stop)

    def provider(self, request):
        if request.url.path.endswith("/models"):
            return httpx.Response(self.models_status, json={"data": self.catalog})
        self.assertTrue(fixtures.TrackedSession.last.closed)
        body = json.loads(request.content)
        self.calls.append((str(request.url), request.headers.get("authorization"), body))
        delta = json.dumps({"choices": [{"delta": {"content": body["model"]}}]})
        return httpx.Response(200, text=f"data: {delta}\n\ndata: [DONE]\n\n")

    def save(self, user="alpha", model="b"):
        with self.factory() as db:
            db.merge(UserLlmSettings(user_id=user, selected_model_id=model))
            db.commit()

    def chat(self, user="alpha", **body):
        return self.client.post("/chat", json={"message": "Install plugin", **body}, headers={"x-test-user": user})

    def test_shared_credentials_keep_preferences_and_document_context_isolated(self):
        self.save()
        self.save("beta", "a")
        first, second = self.chat(), self.chat("beta")
        self.assertEqual([name for name, _ in fixtures.parse_events(first)], ["delta", "citations", "completed"])
        self.assertEqual(fixtures.parse_events(second)[0][1]["text"], "a")
        self.assertEqual([(url, key, body["model"]) for url, key, body in self.calls], [("https://server.test/v1/chat/completions", "Bearer server-key", "b"), ("https://server.test/v1/chat/completions", "Bearer server-key", "a")])
        self.assertNotIn("beta-private-text", str(self.calls[0]))
        self.assertNotIn("alpha-private-text", str(self.calls[1]))

    def test_explicit_id_wins_without_changing_saved_preference(self):
        self.save()
        response = self.chat(model_id="a")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.calls[0][2]["model"], "a")
        with self.factory() as db:
            self.assertEqual(db.get(UserLlmSettings, "alpha").selected_model_id, "b")

    def test_invalid_or_missing_saved_model_stops_before_embedding_and_retrieval(self):
        self.save(model="gone")
        for body in ({}, {"model_id": "invented"}, {"model_id": " "}):
            with self.subTest(body=body):
                self.assertEqual(self.chat(**body).status_code, 422)
        self.assertEqual(self.embedder.queries, [])
        self.assertEqual(self.calls, [])
        with self.factory() as db:
            self.assertEqual(list(db.scalars(select(AuditEvent))), [])

    def test_organization_default_is_used_without_writing_preferences(self):
        self.chat()
        with self.factory() as db:
            db.get(OrganizationLlmSettings,1).default_model_id="b"
            db.commit()
        self.chat()
        self.assertEqual([body["model"] for _, _, body in self.calls], ["a", "b"])
        with self.factory() as db:
            self.assertIsNone(db.get(UserLlmSettings, "alpha"))

    def test_provider_catalog_failure_is_safe_and_stops_before_embedding(self):
        self.models_status = 401
        response = self.chat()
        self.assertEqual([name for name, _ in fixtures.parse_events(response)], ["error"])
        self.assertEqual(fixtures.parse_events(response)[0][1]["code"], "provider_unavailable")
        self.assertEqual(self.embedder.queries, [])
        self.assertEqual(self.calls, [])
        self.assertNotIn("server-key", response.text)

    def test_prepared_request_keeps_snapshot_and_returns_structured_events(self):
        from ruvie.services.chat import ChatService
        from ruvie.contracts.chat import ChatStreamEvent
        self.save()
        service = ChatService(self.embedder, self.settings, self.factory)
        prepared = service.prepare("alpha", "Install plugin")
        with self.factory() as db:
            row = db.get(OrganizationLlmSettings, 1)
            row.base_url = "https://changed.test/v1"
            row.api_key_ciphertext = LlmSecretStore(self.settings.llm_settings_encryption_key).encrypt("changed-key")
            row.default_model_id = "a"
            row.version += 1
            db.commit()
        events = list(service.stream("Install plugin", prepared))
        self.assertTrue(all(isinstance(event, ChatStreamEvent) for event in events))
        self.assertEqual(events[0].data, {"text": "b"})
        self.assertEqual(self.calls[0][:2], ("https://server.test/v1/chat/completions", "Bearer server-key"))
        self.assertEqual([event.event for event in events], ["delta", "citations", "completed"])

    def test_server_model_preference_uses_server_key_without_copying_it(self):
        with self.factory() as db:
            db.add(UserLlmSettings(user_id="alpha", selected_model_id="b"))
            db.commit()
        self.chat()
        self.assertEqual(self.calls[0][:2], ("https://server.test/v1/chat/completions", "Bearer server-key"))
        self.assertEqual(self.calls[0][2]["model"], "b")
        with self.factory() as db:
            row = db.get(UserLlmSettings, "alpha")
            self.assertFalse(hasattr(row, "base_url"))
            self.assertFalse(hasattr(row, "api_key"))

    def test_explicit_valid_id_can_replace_a_missing_saved_model_for_one_request(self):
        self.save(model="gone")
        response = self.chat(model_id="a")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.calls[0][2]["model"], "a")
        with self.factory() as db:
            self.assertEqual(db.get(UserLlmSettings, "alpha").selected_model_id, "gone")