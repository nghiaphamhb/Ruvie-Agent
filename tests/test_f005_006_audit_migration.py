import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


class AuditImmutabilityMigrationTests(unittest.TestCase):
    def test_upgrade_sql_adds_immutable_audit_trigger_and_restricts_project_deletion(self):
        environment = {
            **os.environ,
            "DATABASE_URL": "postgresql+psycopg://offline:offline@localhost:5432/offline",
            "EMBEDDING_MODEL_ID": "BAAI/bge-m3",
            "EMBEDDING_DIMENSION": "1024",
            "EMBEDDING_DISTANCE_METRIC": "cosine",
        }
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", str(BACKEND / "alembic.ini"), "upgrade", "head", "--sql"],
            capture_output=True,
            check=False,
            cwd=ROOT,
            env=environment,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CREATE FUNCTION ruvie_reject_audit_event_mutation()", result.stdout)
        self.assertIn("BEFORE UPDATE OR DELETE ON audit_events", result.stdout)
        self.assertIn("BEFORE TRUNCATE ON audit_events", result.stdout)
        self.assertIn("ON DELETE RESTRICT", result.stdout)


if __name__ == "__main__":
    unittest.main()
