import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
LOAD_CHAT_SETTINGS = "from ruvie.config import load_settings; s = load_settings(); print(s.llm is None, s.embedding_provider is None); print(s.embedding_profile.model_id, s.embedding_profile.dimension, s.embedding_profile.distance_metric)"


class ChatConfigurationTests(unittest.TestCase):
    def test_legacy_provider_environment_cannot_bypass_database_configuration(self) -> None:
        environment = os.environ.copy()
        environment.update(
            DATABASE_URL="postgresql://localhost/ruvie",
            EMBEDDING_MODEL_ID="BAAI/bge-m3",
            EMBEDDING_DIMENSION="1024",
            EMBEDDING_DISTANCE_METRIC="cosine",
            LLM_BASE_URL="https://llm.example.test/v1/",
            LLM_MODEL="gpt-test",
            LLM_API_KEY="test-secret",
            EMBEDDING_BASE_URL="https://embedding.example.test/v1",
            EMBEDDING_API_KEY="embedding-test-secret",
            PYTHONPATH=str(BACKEND),
        )

        result = subprocess.run(
            [sys.executable, "-c", LOAD_CHAT_SETTINGS],
            capture_output=True,
            check=False,
            env=environment,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "True True\nbaai/bge-m3 1024 cosine")


class ChatSseContractTests(unittest.TestCase):
    def test_serializes_delta_event_for_the_stream(self) -> None:
        self.assertIsNotNone(importlib.util.find_spec("ruvie.contracts.chat"))
        from ruvie.contracts.chat import ChatRequest, ChatStreamEvent

        request = ChatRequest(message="How do I install it?")
        frame = ChatStreamEvent("delta", {"text": "Install it"}).to_sse()

        self.assertEqual(request.message, "How do I install it?")
        self.assertEqual(frame, 'event: delta\ndata: {"text":"Install it"}\n\n')


if __name__ == "__main__":
    unittest.main()
