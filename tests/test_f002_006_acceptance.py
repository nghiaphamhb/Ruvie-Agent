import sys
from pathlib import Path
import unittest

from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.document_retrieval import DocumentRetrievalService
from ruvie.domain import AccessGrant, AuditEvent, Base, Document, Membership, Project, Role, RoleCode, User


class F002AcceptanceTests(unittest.TestCase):
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
                        id="document-beta-grant",
                        project_id="project-beta",
                        title="Beta grant document",
                        allowed_role_codes=[RoleCode.BIM_CAD_SPECIALIST.value],
                    ),
                    Document(
                        id="document-beta-private",
                        project_id="project-beta",
                        title="Beta private document",
                        allowed_role_codes=[RoleCode.BIM_CAD_SPECIALIST.value],
                    ),
                )
            )
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_schema_rejects_duplicate_memberships_and_orphan_documents(self) -> None:
        with Session(self.engine) as session:
            session.add(
                Membership(
                    id="duplicate-membership",
                    user_id="user-alpha",
                    project_id="project-alpha",
                    role_id="role-bim",
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()

            session.add(Document(id="orphan-document", project_id="missing", title="Orphan"))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_default_deny_keeps_project_beta_out_of_retrieval_results(self) -> None:
        with Session(self.engine) as session:
            documents = DocumentRetrievalService.retrieve_documents(session, "user-alpha")
            denied = DocumentRetrievalService.retrieve_document(session, "user-alpha", "document-beta-private")

        self.assertEqual([document.id for document in documents], ["document-alpha"])
        self.assertIsNone(denied)

    def test_direct_grant_is_limited_to_the_granted_beta_document(self) -> None:
        with Session(self.engine) as session:
            session.add(
                AccessGrant(
                    id="grant-beta-document",
                    resource_type="document",
                    resource_id="document-beta-grant",
                    principal_type="user",
                    principal_id="user-alpha",
                    permission="read",
                )
            )
            session.commit()

            documents = DocumentRetrievalService.retrieve_documents(session, "user-alpha")
            still_denied = DocumentRetrievalService.retrieve_document(session, "user-alpha", "document-beta-private")

        self.assertEqual([document.id for document in documents], ["document-alpha", "document-beta-grant"])
        self.assertIsNone(still_denied)

    def test_allow_and_deny_retrievals_append_audit_events(self) -> None:
        with Session(self.engine) as session:
            DocumentRetrievalService.retrieve_document(session, "user-alpha", "document-alpha")
            DocumentRetrievalService.retrieve_document(session, "user-alpha", "document-beta-private")
            session.commit()

            events = list(session.scalars(select(AuditEvent).order_by(AuditEvent.resource_id)))

        self.assertEqual(
            [(event.resource_id, event.outcome) for event in events],
            [("document-alpha", "allow"), ("document-beta-private", "deny")],
        )


if __name__ == "__main__":
    unittest.main()
