import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DATABASE_URL = "postgresql+psycopg://ruvie:test-password@localhost:5432/ruvie"


class DomainMigrationTests(unittest.TestCase):
    def test_upgrade_head_generates_the_complete_f002_postgresql_schema(self) -> None:
        environment = {**os.environ, "DATABASE_URL": DATABASE_URL, "EMBEDDING_MODEL_ID": "BAAI/bge-m3", "EMBEDDING_MODEL_VERSION": "a" * 40, "EMBEDDING_DIMENSION": "1024", "EMBEDDING_DISTANCE_METRIC": "cosine"}
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                str(BACKEND / "alembic.ini"),
                "upgrade",
                "head",
                "--sql",
            ],
            capture_output=True,
            check=False,
            cwd=ROOT,
            env=environment,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CREATE TYPE role_code AS ENUM", result.stdout)
        for table_name in (
            "users",
            "roles",
            "projects",
            "memberships",
            "documents",
            "access_grants",
            "audit_events",
        ):
            self.assertIn(f"CREATE TABLE {table_name}", result.stdout)


if __name__ == "__main__":
    unittest.main()
