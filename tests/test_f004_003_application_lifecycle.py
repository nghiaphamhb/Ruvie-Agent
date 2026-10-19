import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient
from ruvie.config import EmbeddingProfile, EmbeddingProviderSettings, LlmProviderSettings, Settings
from ruvie.main import app


TEST_SETTINGS = Settings(
    "postgresql+psycopg://localhost/ruvie",
    EmbeddingProfile("BAAI/bge-m3", 1024, "cosine"),
    EmbeddingProviderSettings("https://embeddings.example.test/v1", "embedding-secret"),
    LlmProviderSettings("https://llm.example.test/v1", "chat-model", "llm-secret"),
)


class ApplicationLifecycleTests(unittest.TestCase):
    def test_lifecycle_shares_resources_with_server_adapters(self) -> None:
        with patch("ruvie.main.load_settings", return_value=TEST_SETTINGS):
            with TestClient(app) as client:
                self.assertEqual(client.get("/health").json(), {"status": "ok"})
                self.assertTrue(hasattr(app.state, "session_factory"))
                with app.state.session_factory() as session:
                    self.assertIs(session.bind, app.state.engine)
                self.assertIs(app.state.query_embedder.client, app.state.http_client)
                self.assertIs(app.state.settings, TEST_SETTINGS)

        self.assertTrue(app.state.http_client.is_closed)

    def test_lifecycle_creates_once_and_releases_on_normal_shutdown(self) -> None:
        engine = Mock()
        http_client = Mock()
        with (
            patch("ruvie.main.load_settings", return_value=TEST_SETTINGS),
            patch("ruvie.main.create_database_engine", return_value=engine) as create_engine,
            patch("ruvie.main.create_session_factory", return_value=Mock()),
            patch("ruvie.main.httpx.Client", return_value=http_client) as create_http_client,
        ):
            with TestClient(app) as client:
                self.assertEqual(client.get("/health").json(), {"status": "ok"})
                self.assertIs(app.state.query_embedder.client, http_client)
                self.assertIs(app.state.settings, TEST_SETTINGS)

        create_engine.assert_called_once_with(TEST_SETTINGS.database_url)
        create_http_client.assert_called_once_with(proxy=None, trust_env=False)
        http_client.close.assert_called_once_with()
        engine.dispose.assert_called_once_with()

    def test_startup_failure_closes_resources_already_created(self) -> None:
        engine = Mock()
        http_client = Mock()
        with (
            patch("ruvie.main.load_settings", return_value=TEST_SETTINGS),
            patch("ruvie.main.create_database_engine", return_value=engine),
            patch("ruvie.main.create_session_factory", return_value=Mock()),
            patch("ruvie.main.httpx.Client", return_value=http_client),
            patch("ruvie.main.create_query_embedder", side_effect=RuntimeError("adapter setup failed")),
        ):
            with self.assertRaisesRegex(RuntimeError, "adapter setup failed"):
                with TestClient(app):
                    pass

        http_client.close.assert_called_once_with()
        engine.dispose.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
