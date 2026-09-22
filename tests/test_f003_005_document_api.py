import os
import sys
from pathlib import Path
import unittest

os.environ.update(EMBEDDING_MODEL_ID="BAAI/bge-m3", EMBEDDING_MODEL_VERSION="a" * 40, EMBEDDING_DIMENSION="1024", EMBEDDING_DISTANCE_METRIC="cosine", DATABASE_URL="postgresql+psycopg://localhost/ruvie")
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "backend"))
from fastapi.testclient import TestClient
from ruvie.main import app

class DocumentApiTests(unittest.TestCase):
    def test_retrieval_rejects_a_request_without_server_authenticated_identity(self) -> None:
        response = TestClient(app).post("/documents/retrieve", json={"query": "alpha", "authorized_scope": {"user_id": "beta"}})
        self.assertEqual(response.status_code, 401)

if __name__ == "__main__": unittest.main()
