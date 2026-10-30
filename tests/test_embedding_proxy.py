"""Embedding proxy configuration reaches both API queries and worker batches."""
import asyncio
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import httpcore
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from ruvie.config import load_settings
from ruvie.main import app, lifespan
from ruvie import worker_cli
from ruvie.adapters.embedding import create_query_embedder
from ruvie.contracts.network import NetworkConfig
from ruvie.adapters.network import normalize_proxy_url, InvalidNetworkConfiguration
from test_llm_proxy import RecordingStream

PROXY = "socks5://127.0.0.1:3066"
ENVIRONMENT = {
    "DATABASE_URL": "postgresql://offline/offline",
    "EMBEDDING_MODEL_ID": "baai/bge-m3",
    "EMBEDDING_DIMENSION": "1024",
    "EMBEDDING_DISTANCE_METRIC": "cosine",
    "EMBEDDING_BASE_URL": "https://embed.test/v1",
    "EMBEDDING_API_KEY": "test-key",
}


def settings(extra=None):
    with patch.dict(os.environ, {**ENVIRONMENT, **(extra or {})}, clear=True), patch("ruvie.config.load_dotenv"):
        return load_settings()


class EmbeddingProxyTests(unittest.TestCase):
    def test_embedding_proxy_is_optional_and_independent_of_llm_proxy(self):
        self.assertIsNone(getattr(settings(), "embedding_proxy_url", None))
        configured = settings({"EMBEDDING_PROXY_URL": " " + PROXY + " ", "LLM_PROXY_URL": "socks5://127.0.0.1:12334"})
        self.assertIsNone(configured.embedding_proxy_url)  # runtime ignores legacy env
        self.assertIsNone(configured.llm_proxy_url)
        self.assertIsNone(getattr(settings({"LLM_PROXY_URL": PROXY}), "embedding_proxy_url", None))

    def test_invalid_embedding_proxy_is_rejected_without_credentials_in_error(self):
        for value in ("http://user:secret@proxy:8080", "socks5://", "socks5://proxy:bad", "socks5://proxy:0", "socks5://proxy:1080/path", "socks5://proxy:1080?q=secret"):
            with self.subTest(value=value):
                with self.assertRaises(InvalidNetworkConfiguration) as raised:
                    normalize_proxy_url(value)
                self.assertNotIn("secret", str(raised.exception))

    def exercise_embedding(self, owner, configured, proxy_url=None):
        """Exercise the guarded operation adapter used by both runtime resolvers."""
        from ruvie.services.embedding import EmbeddingConnectionService
        from ruvie.config import LlmProviderSettings
        adapter=EmbeddingConnectionService(None,configured)._adapter(
            LlmProviderSettings('https://embed.test/v1',api_key='test-key'),
            NetworkConfig(mode='proxy' if proxy_url else 'direct', proxy_url=proxy_url))
        with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('93.184.216.34',443))]):
            return adapter.embed_query('diagnostic') if owner=='api' else adapter.embed(['diagnostic'])[0]

    def test_api_queries_and_worker_batches_use_the_explicit_proxy(self):
        body = json.dumps({"data": [{"embedding": [0.25] * 1024}]}).encode()
        for owner in ("api", "worker"):
            with self.subTest(owner=owner):
                stream = RecordingStream(body)
                configured = settings({"EMBEDDING_PROXY_URL": PROXY})
                with patch.dict(os.environ, {}, clear=True), patch.object(httpcore.SyncBackend, "connect_tcp", return_value=stream) as connect:
                    vector = self.exercise_embedding(owner, configured, PROXY)
                self.assertEqual(vector, [0.25] * 1024)
                self.assertEqual((connect.call_args.kwargs["host"], connect.call_args.kwargs["port"]), ("127.0.0.1", 3066))
                self.assertEqual(stream.tls_hostname, "embed.test")

    def test_empty_proxy_uses_direct_connection_even_with_ambient_proxy(self):
        body = json.dumps({"data": [{"embedding": [0.0] * 1024}]}).encode()
        for owner in ("api", "worker"):
            with self.subTest(owner=owner):
                # A direct response has no SOCKS negotiation frames.
                stream = httpcore.MockStream([b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body])
                with patch.dict(os.environ, {"ALL_PROXY": "socks5://ambient.test:9999"}, clear=True), patch.object(httpcore.SyncBackend, "connect_tcp", return_value=stream) as connect:
                    vector = self.exercise_embedding(owner, settings())
                self.assertEqual(len(vector), 1024)
                self.assertEqual((connect.call_args.kwargs["host"], connect.call_args.kwargs["port"]), ("93.184.216.34", 443))

    def test_proxy_failure_never_falls_back_to_direct(self):
        for owner in ("api", "worker"):
            with self.subTest(owner=owner):
                with patch.dict(os.environ, {}, clear=True), patch.object(httpcore.SyncBackend, "connect_tcp", side_effect=httpcore.ConnectError("unavailable")) as connect:
                    with self.assertRaises(httpx.ConnectError):
                        self.exercise_embedding(owner, settings({"EMBEDDING_PROXY_URL": PROXY}), PROXY)
                self.assertEqual(connect.call_count, 1)
                self.assertEqual(connect.call_args.kwargs["host"], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
