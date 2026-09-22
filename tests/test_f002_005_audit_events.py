import sys
from pathlib import Path
import unittest

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.document_retrieval import DocumentRetrievalService
from ruvie.domain import AuditEvent, Base, Document, Membership, Project, Role, RoleCode, User


class DocumentRetrievalAuditTests(unittest.TestCase):
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

    def test_retrieval_appends_allow_and_deny_audit_events_without_leaking_denied_document(self) -> None:
        with Session(self.engine) as session:
            allowed = DocumentRetrievalService.retrieve_document(session, "user-alpha", "document-alpha")
            denied = DocumentRetrievalService.retrieve_document(session, "user-alpha", "document-beta")
            allowed_id = allowed.id if allowed else None
            session.commit()

            events = list(session.scalars(select(AuditEvent).order_by(AuditEvent.resource_id)))

        self.assertEqual(allowed_id, "document-alpha")
        self.assertIsNone(denied)
        self.assertEqual(
            [(event.resource_id, event.outcome, event.project_id) for event in events],
            [
                ("document-alpha", "allow", "project-alpha"),
                ("document-beta", "deny", None),
            ],
        )


if __name__ == "__main__":
    unittest.main()
