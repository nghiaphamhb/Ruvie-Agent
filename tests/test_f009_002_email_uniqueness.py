"""Verify the PostgreSQL migration SQL and behavior against a disposable database."""
import os
import sys
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

import test_f005_007_e2e as fixtures
from ruvie.models import User

ROOT = Path(__file__).resolve().parents[1]


class EmailMigrationSqlTests(unittest.TestCase):
    def test_offline_sql_enforces_case_insensitive_uniqueness(self):
        environment = {**os.environ, "DATABASE_URL": "postgresql+psycopg://test:test@localhost/test",
                       "EMBEDDING_MODEL_ID": "test", "EMBEDDING_DIMENSION": "1024",
                       "EMBEDDING_DISTANCE_METRIC": "cosine"}
        result = subprocess.run([sys.executable, "-m", "alembic", "-c", "backend/alembic.ini",
                                 "upgrade", "head", "--sql"], cwd=ROOT, env=environment,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email))", result.stdout)


class EmailPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.F005007EndToEndTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.F005007EndToEndTests.tearDownClass()

    def setUp(self):
        self.fixture = fixtures.F005007EndToEndTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.factory = self.fixture.client.app.state.session_factory

    def test_database_rejects_email_case_collision(self):
        with self.factory() as db:
            db.add(User(id="collision", display_name="Collision", email="ALPHA@example.test"))
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()
            self.assertIsNone(db.get(User, "collision"))

    def test_upgrade_downgrade_and_conflicting_existing_data(self):
        config = Config(str(ROOT / "backend/alembic.ini"))
        with patch.dict(os.environ, {"DATABASE_URL": self.fixture.database_url}):
            command.downgrade(config, "0008_user_llm_settings")
            with self.factory() as db:
                db.add(User(id="collision", display_name="Collision", email="ALPHA@example.test"))
                db.commit()
            with self.assertRaises(Exception):
                command.upgrade(config, "head")
            with self.factory() as db:
                self.assertEqual(db.get(User, "alpha").email, "alpha@example.test")
                self.assertEqual(db.get(User, "collision").email, "ALPHA@example.test")
                db.delete(db.get(User, "collision"))
                db.commit()
            command.upgrade(config, "head")
            indexes = inspect(self.fixture.client.app.state.engine).get_indexes("users")
            self.assertTrue(any(item["name"] == "uq_users_email_lower" and item["unique"] for item in indexes))
            command.downgrade(config, "0008_user_llm_settings")
            self.assertFalse(any(item["name"] == "uq_users_email_lower" for item in
                inspect(self.fixture.client.app.state.engine).get_indexes("users")))
            command.upgrade(config, "head")
            with self.factory() as db:
                self.assertEqual(db.scalar(select(User).where(User.id == "alpha")).email, "alpha@example.test")


if __name__ == "__main__":
    unittest.main()
