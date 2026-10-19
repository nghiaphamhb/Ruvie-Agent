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
        self.assertEqual(getattr(configured, "embedding_proxy_url", None), PROXY)
        self.assertEqual(configured.llm_proxy_url, "socks5://127.0.0.1:12334")
        self.assertIsNone(getattr(settings({"LLM_PROXY_URL": PROXY}), "embedding_proxy_url", None))

    def test_invalid_embedding_proxy_is_rejected_without_credentials_in_error(self):
        for value in ("http://user:secret@proxy:8080", "socks5://", "socks5://proxy:bad", "socks5://proxy:0", "socks5://proxy:1080/path", "socks5://proxy:1080?q=secret"):
            with self.subTest(value=value):
                with self.assertRaises(RuntimeError) as raised:
                    settings({"EMBEDDING_PROXY_URL": value})
                self.assertIn("EMBEDDING_PROXY_URL", str(raised.exception))
                self.assertNotIn("secret", str(raised.exception))

    def exercise_embedding(self, owner, configured):
        """Run real resource setup; replace only DB resources and the worker loop."""
        if owner == "api":
            async def query():
                with patch("ruvie.main.load_settings", return_value=configured), patch("ruvie.main.create_database_engine"), patch("ruvie.main.create_session_factory"):
                    async with lifespan(app):
                        return app.state.query_embedder.embed_query("diagnostic")
            return asyncio.run(query())
        captured = []
        def capture(current, client):
            adapter = create_query_embedder(current, client)
            captured.append(adapter)
            return adapter
        results = []
        with patch("ruvie.worker_cli.logging.basicConfig"), patch("ruvie.worker_cli.load_settings", return_value=configured), patch("ruvie.worker_cli.create_database_engine"), patch("ruvie.worker_cli.create_session_factory"), patch("ruvie.worker_cli.create_query_embedder", side_effect=capture), patch("ruvie.worker_cli.run_worker_loop", side_effect=lambda run, stop: results.extend(captured[0].embed(["diagnostic"]))):
            self.assertEqual(worker_cli.main(), 0)
        return results[0]

    def test_api_queries_and_worker_batches_use_the_explicit_proxy(self):
        body = json.dumps({"data": [{"embedding": [0.25] * 1024}]}).encode()
        for owner in ("api", "worker"):
            with self.subTest(owner=owner):
                stream = RecordingStream(body)
                configured = settings({"EMBEDDING_PROXY_URL": PROXY})
                with patch.dict(os.environ, {}, clear=True), patch.object(httpcore.SyncBackend, "connect_tcp", return_value=stream) as connect:
                    vector = self.exercise_embedding(owner, configured)
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
                self.assertEqual((connect.call_args.kwargs["host"], connect.call_args.kwargs["port"]), ("embed.test", 443))

    def test_proxy_failure_never_falls_back_to_direct(self):
        for owner in ("api", "worker"):
            with self.subTest(owner=owner):
                with patch.dict(os.environ, {}, clear=True), patch.object(httpcore.SyncBackend, "connect_tcp", side_effect=httpcore.ConnectError("unavailable")) as connect:
                    with self.assertRaises(httpx.ConnectError):
                        self.exercise_embedding(owner, settings({"EMBEDDING_PROXY_URL": PROXY}))
                self.assertEqual(connect.call_count, 1)
                self.assertEqual(connect.call_args.kwargs["host"], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
