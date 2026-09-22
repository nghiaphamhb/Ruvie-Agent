from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.document_access import DocumentAccessService, MembershipRepository
from ruvie.domain import AccessGrant, Base, Document, Membership, Project, Role, RoleCode, User


class DocumentAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        event.listen(self.engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
        Base.metadata.create_all(self.engine)
        self.now = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)

        with Session(self.engine) as session:
            session.add_all(
                (
                    User(id="user-alpha", email="alpha@example.com", display_name="Alpha user"),
                    Role(id="role-bim", code=RoleCode.BIM_CAD_SPECIALIST),
                    Role(id="role-developer", code=RoleCode.DEVELOPER),
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
                        id="alpha-readable",
                        project_id="project-alpha",
                        title="Alpha BIM guide",
                        allowed_role_codes=[RoleCode.BIM_CAD_SPECIALIST.value],
                    ),
                    Document(
                        id="alpha-developer-only",
                        project_id="project-alpha",
                        title="Alpha developer guide",
                        allowed_role_codes=[RoleCode.DEVELOPER.value],
                    ),
                    Document(
                        id="beta-expired-grant",
                        project_id="project-beta",
                        title="Beta expired grant",
                        allowed_role_codes=[RoleCode.BIM_CAD_SPECIALIST.value],
                    ),
                    Document(
                        id="beta-active-grant",
                        project_id="project-beta",
                        title="Beta active grant",
                        allowed_role_codes=[RoleCode.BIM_CAD_SPECIALIST.value],
                    ),
                )
            )
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def readable_document_ids(self, session: Session) -> list[str]:
        statement = DocumentAccessService.readable_documents_statement(session, "user-alpha", at=self.now)
        return [document.id for document in session.scalars(statement.order_by(Document.id))]

    def test_membership_and_matching_role_limit_documents_to_the_project(self) -> None:
        with Session(self.engine) as session:
            self.assertTrue(MembershipRepository.has_membership(session, "user-alpha", "project-alpha"))
            self.assertFalse(MembershipRepository.has_membership(session, "user-alpha", "project-beta"))
            self.assertEqual(self.readable_document_ids(session), ["alpha-readable"])
            self.assertFalse(
                DocumentAccessService.can_read_document(session, "user-alpha", "beta-active-grant", at=self.now)
            )

    def test_only_a_nonexpired_direct_grant_expands_document_access(self) -> None:
        with Session(self.engine) as session:
            session.add(
                AccessGrant(
                    id="grant-expired",
                    resource_type="document",
                    resource_id="beta-expired-grant",
                    principal_type="user",
                    principal_id="user-alpha",
                    permission="read",
                    expires_at=self.now - timedelta(seconds=1),
                )
            )
            session.commit()
            self.assertEqual(self.readable_document_ids(session), ["alpha-readable"])

            session.add(
                AccessGrant(
                    id="grant-active",
                    resource_type="document",
                    resource_id="beta-active-grant",
                    principal_type="user",
                    principal_id="user-alpha",
                    permission="read",
                    expires_at=self.now + timedelta(seconds=1),
                )
            )
            session.commit()
            self.assertEqual(self.readable_document_ids(session), ["alpha-readable", "beta-active-grant"])


if __name__ == "__main__":
    unittest.main()
