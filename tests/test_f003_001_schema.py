import sys
from pathlib import Path
import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.domain import Base, Document, Project, User


class IngestionSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        event.listen(self.engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_chunk_cannot_use_a_project_other_than_its_document_revision(self) -> None:
        self.assertIn("document_revisions", Base.metadata.tables)
        self.assertIn("ingestion_jobs", Base.metadata.tables)
        self.assertIn("document_chunks", Base.metadata.tables)

        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            session.add_all(
                (
                    User(id="user-1", email="member@example.com", display_name="Member"),
                    Project(id="project-alpha", code="alpha", name="Project Alpha"),
                    Project(id="project-beta", code="beta", name="Project Beta"),
                )
            )
            session.commit()
            session.add(
                Document(
                    id="document-alpha",
                    project_id="project-alpha",
                    title="Alpha guide",
                    allowed_role_codes=[],
                )
            )
            session.commit()

            revision = Base.metadata.tables["document_revisions"]
            session.execute(
                revision.insert().values(
                    id="revision-1",
                    document_id="document-alpha",
                    project_id="project-alpha",
                    revision_number=1,
                    content_hash="a" * 64,
                    blob_uri="file:///uploads/alpha.pdf",
                    mime_type="application/pdf",
                    size_bytes=42,
                    software="Revit",
                    software_version="2026",
                    ingestion_state="pending",
                    embedding_model_id="BAAI/bge-m3",
                    embedding_model_version="v1",
                    embedding_dimension=1024,
                    embedding_distance_metric="cosine",
                )
            )
            session.commit()

            chunks = Base.metadata.tables["document_chunks"]
            session.execute(
                chunks.insert().values(
                    id="chunk-1",
                    document_revision_id="revision-1",
                    document_id="document-alpha",
                    project_id="project-alpha",
                    ordinal=0,
                    text="Alpha-only content",
                    content_hash="b" * 64,
                    start_offset=0,
                    end_offset=18,
                    software="Revit",
                    software_version="2026",
                    embedding=[0.0] * 1024,
                )
            )
            session.commit()

            with self.assertRaises(IntegrityError):
                session.execute(
                    chunks.insert().values(
                        id="chunk-beta",
                        document_revision_id="revision-1",
                        document_id="document-alpha",
                        project_id="project-beta",
                        ordinal=1,
                        text="Wrong project",
                        content_hash="c" * 64,
                        start_offset=0,
                        end_offset=13,
                        software="Revit",
                        software_version="2026",
                        embedding=[0.0] * 1024,
                    )
                )

    def test_chunk_ordinal_is_unique_and_offsets_are_valid_per_revision(self) -> None:
        self.assertIn("document_chunks", Base.metadata.tables)
        Base.metadata.create_all(self.engine)

        chunks = Base.metadata.tables["document_chunks"]
        self.assertTrue(
            any(constraint.name == "uq_document_chunk_revision_ordinal" for constraint in chunks.constraints)
        )
        self.assertTrue(any(constraint.name == "ck_document_chunk_offsets" for constraint in chunks.constraints))


if __name__ == "__main__":
    unittest.main()
