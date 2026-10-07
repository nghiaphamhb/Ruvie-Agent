from uuid import uuid4

from sqlalchemy.orm import Session

from ruvie.models import AuditEvent


class DocumentRetrievalAuditWriter:
    @staticmethod
    def append(
        session: Session,
        actor_user_id: str,
        document_id: str,
        outcome: str,
        reason: str,
        project_id: str | None = None,
    ) -> AuditEvent:
        """Add a retrieval decision to the caller transaction; return the audit row."""
        return AuditEventWriter.append(
            session,
            actor_user_id,
            action="document.retrieve",
            resource_type="document",
            resource_id=document_id,
            outcome=outcome,
            reason=reason,
            project_id=project_id,
        )


class AuditEventWriter:
    @staticmethod
    def append(
        session: Session,
        actor_user_id: str,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        outcome: str,
        reason: str,
        project_id: str | None = None,
    ) -> AuditEvent:
        """Add/flush one audit event; the caller owns commit or rollback."""
        event = AuditEvent(
            id=str(uuid4()),
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            project_id=project_id,
            outcome=outcome,
            reason=reason,
        )
        session.add(event)
        session.flush()
        return event
