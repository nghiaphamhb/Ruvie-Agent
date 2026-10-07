import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.config import LlmProviderSettings, load_settings
from ruvie import models

ENVIRONMENT = {
    "DATABASE_URL": "postgresql+psycopg://offline:offline@localhost/offline",
    "EMBEDDING_MODEL_ID": "BAAI/bge-m3",
    "EMBEDDING_DIMENSION": "1024",
    "EMBEDDING_DISTANCE_METRIC": "cosine",
}


class LlmSettingsConfigurationTests(unittest.TestCase):
    def load_with(self, **values):
        with patch.dict(os.environ, {**ENVIRONMENT, **values}, clear=True), patch("ruvie.config.load_dotenv"):
            return load_settings()

    def test_url_only_does_not_require_a_model_or_key(self):
        provider = self.load_with(LLM_BASE_URL=" https://llm.example.test/v1/ ").llm
        self.assertEqual(provider.base_url, "https://llm.example.test/v1")
        self.assertEqual(provider.model, "")
        self.assertEqual(provider.api_key, "")

    def test_provider_settings_constructor_accepts_url_only(self):
        provider = LlmProviderSettings(base_url="https://llm.example.test/v1")
        self.assertEqual(provider.model, "")
        self.assertEqual(provider.api_key, "")

    def test_optional_model_and_key_are_loaded_independently(self):
        for model, key in (("model-a", ""), ("", "test-secret"), ("model-a", "test-secret")):
            with self.subTest(model=model, has_key=bool(key)):
                provider = self.load_with(LLM_BASE_URL="https://llm.example.test/v1", LLM_MODEL=model, LLM_API_KEY=key).llm
                self.assertEqual(provider.model, model)
                self.assertEqual(provider.api_key, key)

    def test_no_llm_values_disables_server_fallback(self):
        self.assertIsNone(self.load_with(LLM_BASE_URL=" ", LLM_MODEL=" ", LLM_API_KEY=" ").llm)

    def test_model_or_key_without_url_is_rejected(self):
        for values in ({"LLM_MODEL": "model-a"}, {"LLM_API_KEY": "test-secret"}):
            with self.subTest(values=tuple(values)):
                with self.assertRaisesRegex(RuntimeError, "LLM_BASE_URL"):
                    self.load_with(**values)
        with self.assertRaisesRegex(RuntimeError, "LLM_BASE_URL"):
            LlmProviderSettings(base_url=" ")


class UserLlmSettingsTests(unittest.TestCase):
    def setUp(self):
        self.model = getattr(models, "UserLlmSettings", None)
        self.assertIsNotNone(self.model, "The active model must expose per-user LLM settings")
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        self.addCleanup(self.engine.dispose)
        event.listen(self.engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
        models.Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            session.add_all([
                models.User(id="user-a", email="a@example.test", display_name="A"),
                models.User(id="user-b", email="b@example.test", display_name="B"),
            ])
            session.commit()

    def test_two_users_keep_independent_connections_after_update(self):
        with Session(self.engine) as session:
            session.add_all([
                self.model(user_id="user-a", base_url="https://a.example.test/v1", api_key="key-a", models=[{"id": "a", "name": "A"}], selected_model_id="a"),
                self.model(user_id="user-b", base_url="https://b.example.test/v1", api_key="key-b", models=[{"id": "b", "name": "B"}], selected_model_id="b"),
            ])
            session.commit()
        with Session(self.engine) as session:
            record = session.get(self.model, "user-a")
            record.models = [{"id": "a2", "name": "A2"}]
            record.selected_model_id = "a2"
            session.commit()
        with Session(self.engine) as session:
            first, second = session.get(self.model, "user-a"), session.get(self.model, "user-b")
            self.assertEqual((first.base_url, first.api_key, first.selected_model_id, first.models), ("https://a.example.test/v1", "key-a", "a2", [{"id": "a2", "name": "A2"}]))
            self.assertEqual((second.base_url, second.api_key, second.selected_model_id, second.models), ("https://b.example.test/v1", "key-b", "b", [{"id": "b", "name": "B"}]))
            self.assertIsNotNone(first.created_at)
            self.assertIsNotNone(first.updated_at)

    def test_server_model_preference_stores_no_server_url_or_key(self):
        with Session(self.engine) as session:
            session.add(self.model(user_id="user-a", selected_model_id="server-model"))
            session.commit()
        with Session(self.engine) as session:
            record = session.get(self.model, "user-a")
            self.assertEqual(record.selected_model_id, "server-model")
            self.assertIsNone(record.base_url)
            self.assertIsNone(record.api_key)
            self.assertEqual(record.models, [])

    def test_duplicate_user_settings_are_rejected(self):
        with Session(self.engine) as session:
            session.add(self.model(user_id="user-a"))
            session.commit()
        with Session(self.engine) as session:
            session.add(self.model(user_id="user-a"))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_settings_for_missing_user_are_rejected(self):
        with Session(self.engine) as session:
            session.add(self.model(user_id="missing-user"))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_key_without_personal_url_is_rejected(self):
        with Session(self.engine) as session:
            session.add(self.model(user_id="user-a", api_key="personal-key"))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_failed_write_preserves_previous_settings(self):
        with Session(self.engine) as session:
            session.add(self.model(user_id="user-a", selected_model_id="old-model"))
            session.commit()
            record = session.get(self.model, "user-a")
            record.selected_model_id = "new-model"
            record.api_key = "invalid-without-url"
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()
            self.assertEqual(session.get(self.model, "user-a").selected_model_id, "old-model")

    def test_deleting_user_removes_only_their_settings(self):
        with Session(self.engine) as session:
            session.add_all([self.model(user_id="user-a"), self.model(user_id="user-b")])
            session.commit()
            session.delete(session.get(models.User, "user-a"))
            session.commit()
            self.assertEqual(list(session.scalars(select(self.model.user_id))), ["user-b"])


class UserLlmSettingsMigrationTests(unittest.TestCase):
    def test_upgrade_and_downgrade_generate_postgresql_sql(self):
        environment = {**os.environ, **ENVIRONMENT, "LLM_BASE_URL": "", "LLM_MODEL": "", "LLM_API_KEY": ""}
        for command, revision, expected in (
            ("upgrade", "head", "CREATE TABLE user_llm_settings"),
            ("downgrade", "0008_user_llm_settings:0007_audit_event_immutability", "DROP TABLE user_llm_settings"),
        ):
            with self.subTest(command=command):
                result = subprocess.run([sys.executable, "-m", "alembic", "-c", str(ROOT / "backend/alembic.ini"), command, revision, "--sql"], capture_output=True, text=True, cwd=ROOT, env=environment)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)
                if command == "upgrade":
                    self.assertIn("PRIMARY KEY (user_id)", result.stdout)
                    self.assertIn("FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE", result.stdout)
                    self.assertIn("ck_user_llm_settings_key_requires_url", result.stdout)


if __name__ == "__main__":
    unittest.main()
