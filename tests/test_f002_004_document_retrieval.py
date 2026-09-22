import sys
from pathlib import Path
import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.document_retrieval import DocumentRetrievalService
from ruvie.domain import Base, Document, Membership, Project, Role, RoleCode, User


class DocumentRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        event.listen(self.engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
        Base.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            session.add_all(
                (
                    User(id="user-alpha", email="alpha@example.com", display_name="Alpha user"),
                    Role(id="role-bim", code=RoleCode.BIM_CAD_SPECIALIST),
                    Project(id="project-alpha", code="alpha", name="Project Alpha"),
                    Project(id="project-beta", code="beta", name="Project Beta"),
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
            session.add_all(
                (
                    Document(
                        id="document-alpha",
                        project_id="project-alpha",
                        title="Alpha document",
                        allowed_role_codes=[RoleCode.BIM_CAD_SPECIALIST.value],
                    ),
                    Document(
                        id="document-beta",
                        project_id="project-beta",
                        title="Beta document",
                        allowed_role_codes=[RoleCode.BIM_CAD_SPECIALIST.value],
                    ),
                )
            )
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_retrieval_never_materializes_documents_outside_the_users_project(self) -> None:
        with Session(self.engine) as session:
            documents = DocumentRetrievalService.retrieve_documents(session, "user-alpha")

        self.assertEqual([document.id for document in documents], ["document-alpha"])


if __name__ == "__main__":
    unittest.main()
