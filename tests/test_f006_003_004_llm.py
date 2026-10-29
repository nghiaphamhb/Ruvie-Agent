import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.adapters import llm
from ruvie.config import LlmProviderSettings, load_settings
from ruvie.models import Base, User, UserLlmSettings
from ruvie.services.auth import AuthService

PUBLIC_IP = "93.184.216.34"
ORIGIN = "https://ruvie.test"


def resolved(address):
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, 443))]


class LlmAdapterDiscoveryTests(unittest.TestCase):
    def feature(self, name):
        value = getattr(llm, name, None)
        self.assertIsNotNone(value, f"Missing LLM feature: {name}")
        return value

    def adapter(self, handler, key="", model="model-a"):
        client = httpx.Client(transport=httpx.MockTransport(handler), cookies={"ruvie_session": "private-cookie"})
        self.addCleanup(client.close)
        adapter = llm.OpenAICompatibleLlmAdapter(LlmProviderSettings("https://llm.test/v1", model, key), client)
        self.assertTrue(callable(getattr(adapter, "list_models", None)), "Adapter needs model discovery")
        return adapter

    def test_models_are_normalized_and_credentials_are_optional(self):
        for key in ("", "provider-key"):
            with self.subTest(has_key=bool(key)):
                def handler(request):
                    self.assertEqual(str(request.url), "https://llm.test/v1/models")
                    self.assertEqual(request.headers.get("authorization"), f"Bearer {key}" if key else None)
                    self.assertNotIn("cookie", request.headers)
                    self.assertEqual(request.extensions["timeout"]["read"], 10)
                    return httpx.Response(200, json={"data": [
                        {"id": "a", "name": "Model A"}, {"id": "b"}, {"id": "a", "name": "Duplicate"},
                        {"id": ""}, {"name": "Missing ID"}, {"id": 4}, None,
                    ]})
                self.assertEqual(self.adapter(handler, key).list_models(), [{"id": "a", "name": "Model A"}, {"id": "b", "name": "b"}])

    def test_provider_failures_are_safe_and_redirects_are_not_followed(self):
        error = self.feature("LlmProviderError")
        for status in (301, 401, 429, 500):
            with self.subTest(status=status):
                def handler(request):
                    self.assertEqual(request.url.host, "llm.test")
                    return httpx.Response(status, headers={"location": "https://other.test/models"}, json={"error": "secret-from-provider"})
                with self.assertRaises(error) as raised:
                    self.adapter(handler).list_models()
                self.assertNotIn("secret-from-provider", str(raised.exception))

    def test_empty_or_malformed_model_payload_is_rejected(self):
        error = self.feature("LlmProviderError")
        for payload in ({"data": []}, {"data": [{"name": "No ID"}]}, {"data": {}}, [], None):
            with self.subTest(payload=payload):
                with self.assertRaises(error):
                    self.adapter(lambda request: httpx.Response(200, json=payload)).list_models()
        with self.assertRaises(error):
            self.adapter(lambda request: httpx.Response(200, content=b"not-json")).list_models()

    def test_timeout_becomes_safe_provider_error(self):
        error = self.feature("LlmProviderError")
        def handler(request):
            raise httpx.ReadTimeout("provider-key-must-not-leak", request=request)
        with self.assertRaises(error) as raised:
            self.adapter(handler).list_models()
        self.assertNotIn("provider-key", str(raised.exception))

    def test_stream_uses_each_adapters_model_without_cookie_or_empty_bearer(self):
        for model, key in (("a", ""), ("b", "key-b")):
            def handler(request):
                self.assertEqual(json.loads(request.content)["model"], model)
                self.assertEqual(request.headers.get("authorization"), f"Bearer {key}" if key else None)
                self.assertNotIn("cookie", request.headers)
                return httpx.Response(200, content=b'data: {"choices":[{"delta":{"content":"answer"}}]}\n\ndata: [DONE]\n\n')
            client = httpx.Client(transport=httpx.MockTransport(handler), cookies={"ruvie_session": "private"})
            with client:
                adapter = llm.OpenAICompatibleLlmAdapter(LlmProviderSettings("https://llm.test/v1", model, key), client)
                self.assertEqual(list(adapter.stream([{"role": "user", "content": "hello"}])), ["answer"])

    def test_url_policy_and_local_allowlist(self):
        normalize = self.feature("normalize_llm_url")
        invalid = self.feature("InvalidLlmUrl")
        self.assertEqual(normalize(" https://LLM.test/v1/ "), "https://llm.test/v1")
        self.assertEqual(normalize("http://localhost:11434/v1", ("http://localhost:11434",)), "http://localhost:11434/v1")
        for url in ("http://localhost:11434/v1", "http://localhost:11435/v1", "ftp://llm.test/v1", "https://name:key@llm.test/v1", "https://@llm.test", "https://llm.test/v1?q=1", "https://llm.test/v1#part", "not-a-url"):
            with self.subTest(url=url), self.assertRaises(invalid):
                normalize(url)

    def test_dns_pin_keeps_original_host_and_tls_name(self):
        transport_type = self.feature("PinnedLlmTransport")
        def handle(transport, request):
            self.assertEqual(request.url.host, PUBLIC_IP)
            self.assertEqual(request.headers["host"], "llm.test")
            self.assertEqual(request.extensions["sni_hostname"], "llm.test")
            return httpx.Response(200, json={"data": [{"id": "a"}]})
        with patch.object(httpx.HTTPTransport, "handle_request", handle), patch("socket.getaddrinfo", return_value=resolved(PUBLIC_IP)):
            with httpx.Client(transport=transport_type(), trust_env=False) as client:
                self.assertEqual(client.get("https://llm.test/v1/models").status_code, 200)

    def test_forbidden_dns_targets_are_blocked_even_for_allowed_origin(self):
        transport_type = self.feature("PinnedLlmTransport")
        invalid = self.feature("InvalidLlmUrl")
        for address in ("169.254.169.254", "100.100.100.200", "168.63.129.16", "0.0.0.0", "224.0.0.1", "::ffff:169.254.169.254", "fd00:ec2::254"):
            with self.subTest(address=address), patch("socket.getaddrinfo", return_value=resolved(address)):
                with httpx.Client(transport=transport_type(("https://llm.test",)), trust_env=False) as client:
                    with self.assertRaises(invalid):
                        client.get("https://llm.test/models")
        with patch("socket.getaddrinfo", return_value=resolved("127.0.0.1")):
            with httpx.Client(transport=transport_type(), trust_env=False) as client:
                with self.assertRaises(invalid):
                    client.get("https://llm.test/models")

    def test_rebound_dns_is_checked_on_each_connection(self):
        transport_type = self.feature("PinnedLlmTransport")
        invalid = self.feature("InvalidLlmUrl")
        with patch("socket.getaddrinfo", side_effect=[resolved(PUBLIC_IP), resolved("127.0.0.1")]), patch.object(httpx.HTTPTransport, "handle_request", return_value=httpx.Response(200)):
            with httpx.Client(transport=transport_type(), trust_env=False) as client:
                self.assertEqual(client.get("https://llm.test/models").status_code, 200)
                with self.assertRaises(invalid):
                    client.get("https://llm.test/models")


class LlmLocalOriginConfigurationTests(unittest.TestCase):
    def test_local_origins_are_server_settings_with_empty_default(self):
        environment = {"DATABASE_URL": "postgresql://offline/offline", "EMBEDDING_MODEL_ID": "BAAI/bge-m3", "EMBEDDING_DIMENSION": "1024", "EMBEDDING_DISTANCE_METRIC": "cosine"}
        with patch.dict(os.environ, environment, clear=True), patch("ruvie.config.load_dotenv"):
            self.assertEqual(getattr(load_settings(), "llm_allowed_local_origins", None), ())
            os.environ["LLM_ALLOWED_LOCAL_ORIGINS"] = " http://localhost:11434/, http://127.0.0.1:11434 "
            self.assertEqual(load_settings().llm_allowed_local_origins, ("http://localhost:11434", "http://127.0.0.1:11434"))


# Personal connection API scenarios were replaced by F016 organization API/service tests.
