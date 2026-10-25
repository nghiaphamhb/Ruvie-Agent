"""F012-001: system roles, migration preservation and document isolation."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import test_f005_007_e2e as fixtures
from ruvie.models import AccessGrant, Document, User, UserLlmSettings
from ruvie.services.access import DocumentAccessService


class SystemRoleModelTests(unittest.TestCase):
    def setUp(self):
        self.assertIn("system_role", User.__table__.c, "User must persist its system role")
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        self.addCleanup(self.engine.dispose)
        User.__table__.create(self.engine)

    def test_orm_creation_without_role_defaults_to_user(self):
        with Session(self.engine) as db:
            user = User(id="ordinary", email="ordinary@example.test", display_name="Ordinary")
            db.add(user)
            db.commit()
            self.assertEqual(user.system_role, "user")

    def test_sql_creation_without_role_uses_database_default(self):
        with self.engine.begin() as db:
            db.execute(text(
                "INSERT INTO users (id, email, display_name) "
                "VALUES ('direct', 'direct@example.test', 'Direct')"
            ))
            self.assertEqual(db.scalar(text("SELECT system_role FROM users")), "user")

    def test_both_supported_roles_persist(self):
        with Session(self.engine) as db:
            for role in ("user", "admin"):
                db.add(User(id=role, email=f"{role}@example.test",
                            display_name=role, system_role=role))
            db.commit()
            self.assertEqual(
                list(db.execute(select(User.id, User.system_role).order_by(User.id))),
                [("admin", "admin"), ("user", "user")],
            )

    def test_database_rejects_unknown_roles_and_explicit_null(self):
        for role in ("pending", "superadmin", "Admin", "DEVELOPER", "", None):
            with self.subTest(role=role):
                with self.assertRaises(IntegrityError), self.engine.begin() as db:
                    db.execute(text(
                        "INSERT INTO users (id, email, display_name, system_role) "
                        "VALUES ('invalid', 'invalid@example.test', 'Invalid', :role)"
                    ), {"role": role})


class SystemRoleMigrationSqlTests(unittest.TestCase):
    def test_offline_upgrade_adds_role_default_and_constraints(self):
        environment = {
            **os.environ,
            "DATABASE_URL": "postgresql+psycopg://offline:offline@localhost/offline",
            "EMBEDDING_MODEL_ID": "test",
            "EMBEDDING_DIMENSION": "1024",
            "EMBEDDING_DISTANCE_METRIC": "cosine",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        result = subprocess.run(
            [sys.executable, "-B", "-m", "alembic", "-c", "backend/alembic.ini",
             "upgrade", "head", "--sql"],
            cwd=ROOT, env=environment, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        sql = " ".join(result.stdout.split())
        self.assertIn("ADD COLUMN system_role", sql)
        self.assertIn("DEFAULT 'user' NOT NULL", sql)
        self.assertIn(
            "CONSTRAINT ck_users_system_role CHECK (system_role IN ('user', 'admin'))", sql
        )


class SystemRolePostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.F005007EndToEndTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.F005007EndToEndTests.tearDownClass()

    def setUp(self):
        self.assertIn("system_role", User.__table__.c, "User must persist its system role")
        self.fixture = fixtures.F005007EndToEndTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.factory = self.fixture.client.app.state.session_factory
        self.engine = self.fixture.client.app.state.engine

    def snapshot_without_system_role(self):
        """Compare revision-0009 fields; later role/presence columns are intentionally removed."""
        tables = (
            "users", "auth_sessions", "projects", "roles", "memberships", "access_grants",
            "documents", "document_revisions", "document_chunks", "ingestion_jobs",
            "audit_events", "user_llm_settings",
        )
        with self.engine.connect() as db:
            return {
                table: list(db.execute(text(
                    "SELECT to_jsonb(entry) - 'system_role' - 'last_active_at' - 'last_seen_at' FROM " + table + " AS entry "
                    "ORDER BY " + ("user_id" if table == "user_llm_settings" else "id")
                )).scalars())
                for table in tables
            }

    def test_upgrade_downgrade_preserve_legacy_data_and_do_not_promote_users(self):
        csrf, _ = self.fixture._login("alpha@example.test")
        uploaded = self.fixture._upload(
            csrf, "project-alpha", "Role migration guide", b"Migration preserves private content."
        )
        self.assertEqual(uploaded.status_code, 202, uploaded.text)
        self.fixture._run_worker_once()
        with self.factory() as db:
            document = db.scalar(select(Document))
            db.add(AccessGrant(id="migration-grant", resource_id=document.id, principal_id="beta"))
            db.add(UserLlmSettings(user_id="alpha", selected_model_id="server-model"))
            beta = db.get(User, "beta")
            beta.system_role = "admin"
            beta.is_active = False
            db.commit()
        expected = self.snapshot_without_system_role()
        config = Config(str(ROOT / "backend/alembic.ini"))
        with patch.dict(os.environ, {"DATABASE_URL": self.fixture.database_url}):
            command.downgrade(config, "0009_users_email_lower_unique")
            self.assertNotIn("system_role", {
                column["name"] for column in inspect(self.engine).get_columns("users")
            })
            self.assertEqual(self.snapshot_without_system_role(), expected)
            command.upgrade(config, "head")
            self.assertIn("last_active_at", {
                column["name"] for column in inspect(self.engine).get_columns("users")
            })
            self.assertIn("last_seen_at", {
                column["name"] for column in inspect(self.engine).get_columns("auth_sessions")
            })
            self.assertEqual(self.snapshot_without_system_role(), expected)
            with self.factory() as db:
                self.assertEqual(
                    list(db.execute(select(User.id, User.system_role).order_by(User.id))),
                    [("alpha", "user"), ("beta", "user")],
                )
                self.assertFalse(db.get(User, "beta").is_active)
            indexes = inspect(self.engine).get_indexes("users")
            self.assertTrue(any(index["name"] == "uq_users_email_lower" for index in indexes))
            with self.assertRaises(IntegrityError), self.engine.begin() as db:
                db.execute(text(
                    "INSERT INTO users (id, email, display_name) "
                    "VALUES ('collision', 'ALPHA@example.test', 'Collision')"
                ))
            command.downgrade(config, "0009_users_email_lower_unique")
            command.upgrade(config, "head")
            self.assertEqual(self.snapshot_without_system_role(), expected)

    def test_postgres_enforces_default_non_null_and_supported_roles(self):
        columns = {column["name"]: column for column in inspect(self.engine).get_columns("users")}
        self.assertFalse(columns["system_role"]["nullable"])
        checks = inspect(self.engine).get_check_constraints("users")
        self.assertTrue(any(check["name"] == "ck_users_system_role" for check in checks))
        with self.engine.begin() as db:
            db.execute(text(
                "INSERT INTO users (id, email, display_name) "
                "VALUES ('sql-default', 'sql-default@example.test', 'SQL Default')"
            ))
            self.assertEqual(db.scalar(text(
                "SELECT system_role FROM users WHERE id = 'sql-default'"
            )), "user")
            db.execute(text(
                "INSERT INTO users (id, email, display_name, system_role) "
                "VALUES ('sql-admin', 'sql-admin@example.test', 'SQL Admin', 'admin')"
            ))
            self.assertEqual(db.scalar(text(
                "SELECT system_role FROM users WHERE id = 'sql-admin'"
            )), "admin")
        for role in ("pending", "superadmin", "Admin", "DEVELOPER", "", None):
            with self.subTest(role=role):
                with self.assertRaises(IntegrityError), self.engine.begin() as db:
                    db.execute(text(
                        "INSERT INTO users (id, email, display_name, system_role) "
                        "VALUES ('invalid', 'invalid@example.test', 'Invalid', :role)"
                    ), {"role": role})

    def test_admin_role_does_not_bypass_project_or_document_permissions(self):
        with self.factory() as db:
            db.add(User(id="administrator", email="admin@example.test", display_name="Admin",
                        system_role="admin"))
            db.add(Document(id="restricted", project_id="project-alpha", title="Restricted",
                            allowed_role_codes=["BIM_CAD_SPECIALIST"]))
            db.commit()
            self.assertTrue(DocumentAccessService.can_read_document(db, "alpha", "restricted"))
            self.assertFalse(DocumentAccessService.can_read_document(db, "administrator", "restricted"))
            db.add(AccessGrant(id="explicit-grant", resource_id="restricted", principal_id="administrator"))
            db.commit()
            self.assertTrue(DocumentAccessService.can_read_document(db, "administrator", "restricted"))
            self.assertFalse(DocumentAccessService.can_read_document(db, "beta", "restricted"))


if __name__ == "__main__":
    unittest.main()
