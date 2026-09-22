import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
LOAD_SETTINGS = "from ruvie.config import load_settings; print(load_settings().database_url)"


class ConfigurationTests(unittest.TestCase):
    def run_settings(self, database_url: str | None) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.pop("DATABASE_URL", None)
        environment["EMBEDDING_MODEL_ID"] = "BAAI/bge-m3"
        environment["EMBEDDING_MODEL_VERSION"] = "a" * 40
        environment["EMBEDDING_DIMENSION"] = "1024"
        environment["EMBEDDING_DISTANCE_METRIC"] = "cosine"
        environment["PYTHONPATH"] = str(BACKEND)
        if database_url is not None:
            environment["DATABASE_URL"] = database_url
        return subprocess.run(
            [sys.executable, "-c", LOAD_SETTINGS],
            capture_output=True,
            check=False,
            env=environment,
            text=True,
        )

    def test_loads_required_database_url(self) -> None:
        result = self.run_settings("postgresql://localhost/ruvie")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "postgresql://localhost/ruvie")

    def test_rejects_missing_database_url(self) -> None:
        result = self.run_settings("   ")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DATABASE_URL is required", result.stderr)


if __name__ == "__main__":
    unittest.main()
