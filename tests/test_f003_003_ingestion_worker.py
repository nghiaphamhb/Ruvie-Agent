import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.config import EmbeddingProfile
from ruvie.document_ingestion import DocumentIngestionWorker
from ruvie.document_upload import DocumentUploadService, LocalBlobStore, UploadRequest
from ruvie.domain import Base, DocumentChunk, DocumentRevision, IngestionJob, IngestionJobState, Membership, Project, RevisionIngestionState, Role, RoleCode, User


class FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text))] + [0.0] * 1023 for text in texts]


class IngestionWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        event.listen(self.engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            session.add_all((User(id="user-1", email="member@example.com", display_name="Member"), Role(id="role-1", code=RoleCode.BIM_CAD_SPECIALIST), Project(id="project-1", code="alpha", name="Project Alpha")))
            session.commit()
            session.add(Membership(id="membership-1", user_id="user-1", project_id="project-1", role_id="role-1"))
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_worker_creates_deterministic_chunks_and_marks_revision_ready(self) -> None:
        profile = EmbeddingProfile("BAAI/bge-m3", "a" * 40, 1024, "cosine")
        with TemporaryDirectory() as directory, Session(self.engine) as session:
            upload = DocumentUploadService(session, LocalBlobStore(Path(directory)), profile).create_revision(
                UploadRequest("user-1", "project-1", "Alpha", "alpha.txt", b"alpha bravo charlie", "text/plain", "Revit", "2026", ["BIM_CAD_SPECIALIST"])
            )
            worker = DocumentIngestionWorker(session, LocalBlobStore(Path(directory)), FakeEmbedder(), profile, chunk_size=8, chunk_overlap=2)

            self.assertEqual(worker.run_next(), upload.job_id)
            self.assertIsNone(worker.run_next())

            revision = session.get(DocumentRevision, upload.revision_id)
            job = session.get(IngestionJob, upload.job_id)
            chunks = session.scalars(select(DocumentChunk).where(DocumentChunk.document_revision_id == upload.revision_id).order_by(DocumentChunk.ordinal)).all()
            self.assertEqual(revision.ingestion_state, RevisionIngestionState.READY)
            self.assertEqual(job.state, IngestionJobState.COMPLETED)
            self.assertEqual([(chunk.text, chunk.start_offset, chunk.end_offset) for chunk in chunks], [("alpha br", 0, 8), ("bravo ch", 6, 14), ("charlie", 12, 19)])


if __name__ == "__main__":
    unittest.main()
