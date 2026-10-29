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

    def test_environment_fallback_is_retired_even_for_partial_values(self):
        for values in ({"LLM_BASE_URL":"https://obsolete.test"}, {"LLM_API_KEY":"obsolete"},
                       {"LLM_MODEL":"old"}):
            self.assertIsNone(self.load_with(**values).llm)

    def test_low_level_provider_settings_still_accept_url_only(self):
        provider = LlmProviderSettings("https://provider.test/v1")
        self.assertEqual((provider.model, provider.api_key), ("", ""))


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

    def test_two_users_keep_independent_preferences_after_update(self):
        with Session(self.engine) as session:
            session.add_all([self.model(user_id="user-a", selected_model_id="a"),
                             self.model(user_id="user-b", selected_model_id="b")])
            session.commit()
            session.get(self.model,"user-a").selected_model_id="a2"
            session.commit()
        with Session(self.engine) as session:
            self.assertEqual(session.get(self.model,"user-a").selected_model_id,"a2")
            self.assertEqual(session.get(self.model,"user-b").selected_model_id,"b")

    def test_preference_cannot_store_credentials(self):
        for field in ("base_url","api_key","models"):
            with self.assertRaises(TypeError):
                self.model(user_id="user-a", **{field:"forbidden"})

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

    def test_failed_write_preserves_previous_preference(self):
        with Session(self.engine) as session:
            session.add(self.model(user_id="user-a",selected_model_id="old"))
            session.commit()
            session.get(self.model,"user-a").selected_model_id="new"
            session.add(self.model(user_id="missing"))
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()
            self.assertEqual(session.get(self.model,"user-a").selected_model_id,"old")

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
