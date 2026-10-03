import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.config import EmbeddingProfile
from ruvie.models import AuditEvent, Base, Document, DocumentRevision, IngestionJob, Membership, Project, Role, RoleCode, User
from ruvie.services.documents.upload import DocumentUploadService, UploadAuthorizationError, UploadRequest
from ruvie.adapters.blob_storage import LocalBlobStore


class F005006UploadAuditTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        event.listen(self.engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            session.add_all((
                User(id="member", email="member@example.test", display_name="Member"),
                User(id="outsider", email="outsider@example.test", display_name="Outsider"),
                Role(id="role-bim", code=RoleCode.BIM_CAD_SPECIALIST),
                Project(id="project-alpha", code="alpha", name="Alpha"),
                Project(id="project-beta", code="beta", name="Beta"),
            ))
            session.commit()
            session.add(Membership(id="membership-alpha", user_id="member", project_id="project-alpha", role_id="role-bim"))
            session.commit()
        self.directory = TemporaryDirectory()
        self.blobs = LocalBlobStore(Path(self.directory.name))
        self.profile = EmbeddingProfile("test-model", 1024, "cosine")

    def tearDown(self):
        self.directory.cleanup()
        self.engine.dispose()

    def upload(self, actor="member", project="project-alpha"):
        return UploadRequest(actor, project, "Plan", "plan.txt", b"plan text", "text/plain", "Revit", "2026")

    def test_member_upload_persists_allow_audit_with_document(self):
        with Session(self.engine) as session:
            result = DocumentUploadService(session, self.blobs, self.profile).create_revision(self.upload())
            audit = session.scalar(select(AuditEvent).where(AuditEvent.action == "document.upload"))

            self.assertIsNotNone(session.get(Document, result.document_id))
            self.assertIsNotNone(session.get(DocumentRevision, result.revision_id))
            self.assertIsNotNone(session.scalar(select(IngestionJob).where(IngestionJob.document_revision_id == result.revision_id)))
            self.assertEqual((audit.actor_user_id, audit.resource_type, audit.resource_id, audit.project_id),
                             ("member", "document", result.document_id, "project-alpha"))
            self.assertEqual((audit.outcome, audit.reason), ("allow", "revision_created"))

    def test_denied_upload_persists_deny_audit_without_creating_upload_data(self):
        with Session(self.engine) as session:
            with self.assertRaises(UploadAuthorizationError):
                DocumentUploadService(session, self.blobs, self.profile).create_revision(self.upload("outsider", "project-beta"))
            audit = session.scalar(select(AuditEvent).where(AuditEvent.action == "document.upload"))

            self.assertEqual((audit.actor_user_id, audit.resource_type, audit.resource_id, audit.project_id),
                             ("outsider", "project", "project-beta", "project-beta"))
            self.assertEqual((audit.outcome, audit.reason), ("deny", "project_membership_required"))
            self.assertEqual(session.scalar(select(Document.id)), None)
            self.assertEqual(session.scalar(select(DocumentRevision.id)), None)
            self.assertEqual(session.scalar(select(IngestionJob.id)), None)
        self.assertEqual(list(Path(self.directory.name).rglob("*.*")), [])

    def test_database_failure_after_blob_write_rolls_back_and_removes_blob(self):
        def fail_once(session):
            event.remove(Session, "before_commit", fail_once)
            raise RuntimeError("simulated commit failure")

        event.listen(Session, "before_commit", fail_once)
        with Session(self.engine) as session:
            with self.assertRaisesRegex(RuntimeError, "simulated commit failure"):
                DocumentUploadService(session, self.blobs, self.profile).create_revision(self.upload())

        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(Document.id)), None)
            self.assertEqual(session.scalar(select(DocumentRevision.id)), None)
            self.assertEqual(session.scalar(select(IngestionJob.id)), None)
            self.assertEqual(session.scalar(select(AuditEvent.id)), None)
        self.assertEqual([path for path in Path(self.directory.name).rglob("*") if path.is_file()], [])


if __name__ == "__main__":
    unittest.main()
