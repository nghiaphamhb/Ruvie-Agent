import sys
from pathlib import Path
import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.domain import (
    AccessGrant,
    AuditEvent,
    Base,
    Document,
    Membership,
    Project,
    Role,
    RoleCode,
    User,
)


class DomainSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        event.listen(self.engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
        Base.metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_domain_schema_enforces_identity_membership_and_document_scope(self) -> None:
        with Session(self.engine) as session:
            user = User(id="user-1", email="member@example.com", display_name="Member")
            role = Role(id="role-1", code=RoleCode.BIM_CAD_SPECIALIST)
            project = Project(id="project-1", code="alpha", name="Project Alpha")
            session.add_all((user, role, project))
            session.commit()

            session.add(Membership(id="membership-1", user_id=user.id, project_id=project.id, role_id=role.id))
            session.add(
                Document(
                    id="document-1",
                    project_id=project.id,
                    title="Alpha guide",
                    document_type="guide",
                    status="active",
                    allowed_role_codes=[RoleCode.BIM_CAD_SPECIALIST.value],
                )
            )
            session.commit()

            session.add(
                AccessGrant(
                    id="grant-1",
                    resource_type="document",
                    resource_id="document-1",
                    principal_type="user",
                    principal_id=user.id,
                    permission="read",
                )
            )
            session.add(
                AuditEvent(
                    id="audit-1",
                    actor_user_id=user.id,
                    action="document.retrieve",
                    resource_type="document",
                    resource_id="document-1",
                    project_id=project.id,
                    outcome="allow",
                    reason="project membership",
                )
            )
            session.commit()

            session.add(User(id="user-2", email="member@example.com", display_name="Duplicate"))
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()

            session.add(Membership(id="membership-2", user_id=user.id, project_id=project.id, role_id=role.id))
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()

            session.add(Document(id="document-2", project_id="missing", title="Orphan"))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_role_code_rejects_values_outside_the_domain_vocabulary(self) -> None:
        with Session(self.engine) as session:
            session.add(Role(id="role-invalid", code="ADMIN"))

            with self.assertRaises(IntegrityError):
                session.commit()

    def test_access_grant_must_reference_an_existing_document(self) -> None:
        with Session(self.engine) as session:
            session.add(User(id="user-1", email="member@example.com", display_name="Member"))
            session.commit()
            session.add(
                AccessGrant(
                    id="grant-orphan",
                    resource_type="document",
                    resource_id="missing-document",
                    principal_type="user",
                    principal_id="user-1",
                    permission="read",
                )
            )

            with self.assertRaises(IntegrityError):
                session.commit()


if __name__ == "__main__":
    unittest.main()
