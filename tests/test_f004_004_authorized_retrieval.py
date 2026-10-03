import sys
from pathlib import Path
import unittest

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.models import (
    AccessGrant,
    AuditEvent,
    Base,
    Document,
    DocumentChunk,
    DocumentRevision,
    Membership,
    Project,
    RevisionIngestionState,
    Role,
    RoleCode,
    User,
)
from ruvie.services.retrieval import AuthorizedRetrievalService


class AuthorizedRetrievalServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        event.listen(self.engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            session.add_all((
                User(id="alpha", email="alpha@example.com", display_name="Alpha"),
                User(id="beta", email="beta@example.com", display_name="Beta"),
                Role(id="role", code=RoleCode.BIM_CAD_SPECIALIST),
                Project(id="project-alpha", code="alpha", name="Alpha"),
                Project(id="project-beta", code="beta", name="Beta"),
            ))
            session.commit()
            session.add_all((
                Membership(id="membership", user_id="alpha", project_id="project-alpha", role_id="role"),
                Document(id="document-alpha", project_id="project-alpha", title="Alpha guide", allowed_role_codes=[RoleCode.BIM_CAD_SPECIALIST.value]),
                Document(id="document-granted", project_id="project-beta", title="Granted guide", allowed_role_codes=[]),
                Document(id="document-private", project_id="project-beta", title="Private guide", allowed_role_codes=[]),
            ))
            session.commit()
            session.add(AccessGrant(id="grant", resource_id="document-granted", principal_id="alpha"))
            session.commit()
            for revision_id, document_id, project_id in (
                ("revision-alpha", "document-alpha", "project-alpha"),
                ("revision-granted", "document-granted", "project-beta"),
                ("revision-private", "document-private", "project-beta"),
            ):
                session.add(DocumentRevision(
                    id=revision_id, document_id=document_id, project_id=project_id,
                    revision_number=1, content_hash=revision_id * 4,
                    blob_uri="file:///private", mime_type="text/plain", size_bytes=1,
                    software="Revit", software_version="2026",
                    ingestion_state=RevisionIngestionState.READY,
                    embedding_model_id="model",
                    embedding_dimension=1024, embedding_distance_metric="cosine",
                ))
            session.commit()
            for chunk_id, revision_id, document_id, project_id in (
                ("chunk-alpha", "revision-alpha", "document-alpha", "project-alpha"),
                ("chunk-granted", "revision-granted", "document-granted", "project-beta"),
                ("chunk-private", "revision-private", "document-private", "project-beta"),
            ):
                session.add(DocumentChunk(
                    id=chunk_id, document_revision_id=revision_id, document_id=document_id,
                    project_id=project_id, ordinal=0, text=chunk_id, content_hash=chunk_id * 4,
                    start_offset=0, end_offset=5, software="Revit", software_version="2026",
                    embedding=[0.0] * 1024,
                ))
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_retrieves_only_authorized_chunks_with_citations_and_allow_audit(self) -> None:
        with Session(self.engine) as session:
            hits = AuthorizedRetrievalService(session).retrieve("alpha", [0.0] * 1024)
        with Session(self.engine) as session:
            audits = list(session.scalars(select(AuditEvent)))

        self.assertEqual({hit.chunk_id for hit in hits}, {"chunk-alpha", "chunk-granted"})
        alpha_hit = next(hit for hit in hits if hit.chunk_id == "chunk-alpha")
        self.assertEqual(alpha_hit.citation.revision_id, "revision-alpha")
        self.assertEqual(alpha_hit.citation.source_hash, "revision-alpha" * 4)
        self.assertEqual([(audit.outcome, audit.reason) for audit in audits], [("allow", "authorized results")])

    def test_records_safe_deny_audit_when_no_authorized_chunk_exists(self) -> None:
        with Session(self.engine) as session:
            hits = AuthorizedRetrievalService(session).retrieve("beta", [0.0] * 1024)
        with Session(self.engine) as session:
            audit = session.scalar(select(AuditEvent))

        self.assertEqual(hits, [])
        self.assertEqual((audit.outcome, audit.reason, audit.project_id), ("deny", "no authorized results", None))
        self.assertNotIn("private", audit.resource_id)


if __name__ == "__main__":
    unittest.main()
