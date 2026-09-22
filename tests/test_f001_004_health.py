import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


class HealthEndpointTests(unittest.TestCase):
    def request(self, path: str) -> subprocess.CompletedProcess[str]:
        script = "\n".join(
            [
                "import json",
                "import os",
                "import sys",
                f"sys.path.insert(0, {str(BACKEND)!r})",
                "os.environ['DATABASE_URL'] = 'postgresql+psycopg://localhost/ruvie'",
                "os.environ['EMBEDDING_MODEL_ID'] = 'BAAI/bge-m3'",
                "os.environ['EMBEDDING_MODEL_VERSION'] = 'a' * 40",
                "os.environ['EMBEDDING_DIMENSION'] = '1024'",
                "os.environ['EMBEDDING_DISTANCE_METRIC'] = 'cosine'",
                "from fastapi.testclient import TestClient",
                "from ruvie.main import app",
                f"response = TestClient(app).get({path!r})",
                "print(response.status_code)",
                "print(json.dumps(response.json(), sort_keys=True))",
            ]
        )
        return subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            check=False,
            env=os.environ.copy(),
            text=True,
        )

    def test_health_endpoint_returns_ok(self) -> None:
        result = self.request("/health")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '200\n{"status": "ok"}\n')

    def test_ready_endpoint_returns_ok(self) -> None:
        result = self.request("/ready")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '200\n{"status": "ok"}\n')


if __name__ == "__main__":
    unittest.main()
