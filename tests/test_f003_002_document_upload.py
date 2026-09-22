import hashlib
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.document_upload import DocumentUploadService, LocalBlobStore, S3BlobStore, UploadRequest
from ruvie.config import EmbeddingProfile
from ruvie.domain import (
    Base,
    Document,
    DocumentRevision,
    IngestionJob,
    IngestionJobState,
    Membership,
    Project,
    RevisionIngestionState,
    Role,
    RoleCode,
    User,
)


class InMemoryS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict[str, object]] = {}

    def put_object(self, **kwargs: object) -> None:
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs


class DocumentUploadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        event.listen(self.engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
        Base.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            session.add_all(
                (
                    User(id="user-alpha", email="alpha@example.com", display_name="Alpha member"),
                    Role(id="role-bim", code=RoleCode.BIM_CAD_SPECIALIST),
                    Project(id="project-alpha", code="alpha", name="Project Alpha"),
                )
            )
            session.commit()
            session.add(
                Membership(
                    id="membership-alpha",
                    user_id="user-alpha",
                    project_id="project-alpha",
                    role_id="role-bim",
                )
            )
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_member_upload_creates_private_blob_pending_revision_and_job(self) -> None:
        content = b"Project Alpha technical design"
        with TemporaryDirectory() as directory, Session(self.engine) as session:
            result = DocumentUploadService(session, LocalBlobStore(Path(directory)), EmbeddingProfile("BAAI/bge-m3", "a" * 40, 1024, "cosine")).create_revision(
                UploadRequest(
                    actor_user_id="user-alpha",
                    project_id="project-alpha",
                    title="Alpha design",
                    filename="../../alpha.pdf",
                    content=content,
                    mime_type="application/pdf",
                    software="Revit",
                    software_version="2026",
                    allowed_role_codes=[RoleCode.BIM_CAD_SPECIALIST.value],
                )
            )

            self.assertEqual(result.content_hash, hashlib.sha256(content).hexdigest())
            stored_paths = [path for path in Path(directory).rglob("*") if path.is_file()]
            self.assertEqual(len(stored_paths), 1)
            self.assertEqual(stored_paths[0].read_bytes(), content)
            self.assertNotIn("..", stored_paths[0].relative_to(directory).parts)

            document = session.get(Document, result.document_id)
            revision = session.get(DocumentRevision, result.revision_id)
            job = session.get(IngestionJob, result.job_id)
            self.assertEqual(document.project_id, "project-alpha")
            self.assertEqual(document.allowed_role_codes, ["BIM_CAD_SPECIALIST"])
            self.assertEqual(revision.ingestion_state, RevisionIngestionState.PENDING)
            self.assertEqual(revision.software_version, "2026")
            self.assertEqual(job.state, IngestionJobState.PENDING)

    def test_s3_adapter_stores_a_private_object_under_its_prefix(self) -> None:
        client = InMemoryS3()

        uri = S3BlobStore(client, bucket="ruvie-private", prefix="ingestion").put(
            key="projects/alpha/document.pdf", content=b"alpha", mime_type="application/pdf"
        )

        self.assertEqual(uri, "s3://ruvie-private/ingestion/projects/alpha/document.pdf")
        stored = client.objects[("ruvie-private", "ingestion/projects/alpha/document.pdf")]
        self.assertEqual(stored["Body"], b"alpha")
        self.assertEqual(stored["ACL"], "private")


if __name__ == "__main__":
    unittest.main()
