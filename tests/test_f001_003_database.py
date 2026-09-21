import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DATABASE_URL = "postgresql+psycopg://ruvie:test-password@localhost:5432/ruvie"


class DatabaseFoundationTests(unittest.TestCase):
    def environment(self, include_backend: bool = True) -> dict[str, str]:
        environment = {
            **os.environ,
            "DATABASE_URL": DATABASE_URL,
        }
        environment.pop("PYTHONPATH", None)
        if include_backend:
            environment["PYTHONPATH"] = str(BACKEND)
        return environment

    def test_creates_psycopg_postgresql_engine(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from ruvie.database import create_database_engine; "
                "print(create_database_engine().url.drivername)",
            ],
            capture_output=True,
            check=False,
            env=self.environment(),
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "postgresql+psycopg")

    def test_baseline_migration_generates_sql(self) -> None:
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
            env=self.environment(include_backend=False),
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CREATE TABLE alembic_version", result.stdout)
        self.assertIn("0001_initial_baseline", result.stdout)


if __name__ == "__main__":
    unittest.main()
