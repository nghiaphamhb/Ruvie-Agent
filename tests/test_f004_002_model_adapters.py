import importlib.util
import json
import sys
from pathlib import Path
import unittest

import httpx


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


class ModelAdapterTests(unittest.TestCase):
    def test_openai_compatible_query_embedder_uses_pinned_profile_model(self) -> None:
        self.assertIsNotNone(importlib.util.find_spec("ruvie.adapters.embedding"))
        from ruvie.config import EmbeddingProfile, EmbeddingProviderSettings
        from ruvie.adapters.embedding import OpenAICompatibleQueryEmbedder

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "https://embeddings.example.test/v1/embeddings")
            self.assertEqual(request.headers["authorization"], "Bearer embedding-secret")
            self.assertEqual(json.loads(request.content), {"input": "Find Alpha", "model": "BAAI/bge-m3"})
            return httpx.Response(200, json={"data": [{"embedding": [0.25] * 1024}]})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        embedder = OpenAICompatibleQueryEmbedder(
            EmbeddingProviderSettings("https://embeddings.example.test/v1", "embedding-secret"),
            EmbeddingProfile("BAAI/bge-m3", 1024, "cosine"),
            client,
        )

        self.assertEqual(embedder.embed_query("Find Alpha"), [0.25] * 1024)

    def test_openai_compatible_llm_adapter_streams_content_deltas(self) -> None:
        self.assertIsNotNone(importlib.util.find_spec("ruvie.adapters.llm"))
        from ruvie.config import LlmProviderSettings
        from ruvie.adapters.llm import OpenAICompatibleLlmAdapter

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "https://llm.example.test/v1/chat/completions")
            self.assertEqual(request.headers["authorization"], "Bearer llm-secret")
            self.assertEqual(
                json.loads(request.content),
                {"messages": [{"role": "user", "content": "Hello"}], "model": "chat-model", "stream": True},
            )
            return httpx.Response(
                200,
                content=(
                    b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
                    b'data: {"choices":[{"delta":{"content":" world"}}]}\n\n'
                    b"data: [DONE]\n\n"
                ),
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        adapter = OpenAICompatibleLlmAdapter(LlmProviderSettings("https://llm.example.test/v1", "chat-model", "llm-secret"), client)

        self.assertEqual(list(adapter.stream([{"role": "user", "content": "Hello"}])), ["Hello", " world"])

    def test_factories_use_only_server_settings(self) -> None:
        from ruvie.config import EmbeddingProfile, EmbeddingProviderSettings, LlmProviderSettings, Settings
        from ruvie.adapters.embedding import OpenAICompatibleQueryEmbedder, create_query_embedder
        from ruvie.adapters.llm import OpenAICompatibleLlmAdapter, create_llm_adapter

        settings = Settings(
            "postgresql://localhost/ruvie",
            EmbeddingProfile("BAAI/bge-m3", 1024, "cosine"),
            EmbeddingProviderSettings("https://embeddings.example.test/v1", "embedding-secret"),
            LlmProviderSettings("https://llm.example.test/v1", "chat-model", "llm-secret"),
        )

        self.assertIsInstance(create_query_embedder(settings), OpenAICompatibleQueryEmbedder)
        self.assertIsInstance(create_llm_adapter(settings), OpenAICompatibleLlmAdapter)


if __name__ == "__main__":
    unittest.main()
