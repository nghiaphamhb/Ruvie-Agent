from datetime import datetime, timezone

from sqlalchemy import Text, cast, exists, false, func, or_, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from ruvie.domain import AccessGrant, Document, Membership, Role


class MembershipRepository:
    @staticmethod
    def has_membership(session: Session, user_id: str, project_id: str) -> bool:
        statement = select(Membership.id).where(
            Membership.user_id == user_id,
            Membership.project_id == project_id,
        )
        return session.scalar(statement) is not None

    @staticmethod
    def allowed_document_predicate(user_id: str, dialect_name: str):
        membership = select(1).select_from(Membership).join(Role, Role.id == Membership.role_id)
        if dialect_name == "postgresql":
            membership = membership.where(
                cast(Document.allowed_role_codes, postgresql.JSONB).op("@>")(
                    func.jsonb_build_array(cast(Role.code, Text))
                )
            )
        elif dialect_name == "sqlite":
            allowed_roles = func.json_each(Document.allowed_role_codes).table_valued("value").alias("allowed_roles")
            membership = membership.join(allowed_roles, allowed_roles.c.value == Role.code)
        else:
            return false()

        return exists(membership.where(
            Membership.user_id == user_id,
            Membership.project_id == Document.project_id,
        ))


class AccessGrantRepository:
    @staticmethod
    def active_document_read_predicate(user_id: str, at: datetime):
        return exists(
            select(1).where(
                AccessGrant.resource_type == "document",
                AccessGrant.resource_id == Document.id,
                AccessGrant.principal_type == "user",
                AccessGrant.principal_id == user_id,
                AccessGrant.permission == "read",
                or_(AccessGrant.expires_at.is_(None), AccessGrant.expires_at > at),
            )
        )


class DocumentAccessService:
    @staticmethod
    def readable_documents_statement(session: Session, user_id: str, *, at: datetime | None = None):
        now = at or datetime.now(timezone.utc)
        return select(Document).where(
            or_(
                MembershipRepository.allowed_document_predicate(user_id, session.get_bind().dialect.name),
                AccessGrantRepository.active_document_read_predicate(user_id, now),
            )
        )

    @staticmethod
    def can_read_document(session: Session, user_id: str, document_id: str, *, at: datetime | None = None) -> bool:
        statement = DocumentAccessService.readable_documents_statement(session, user_id, at=at).where(
            Document.id == document_id
        )
        return session.scalar(statement) is not None
