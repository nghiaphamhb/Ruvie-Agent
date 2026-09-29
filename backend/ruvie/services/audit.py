from uuid import uuid4

from sqlalchemy.orm import Session

from ruvie.domain import AuditEvent


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
        event = AuditEvent(
            id=str(uuid4()),
            actor_user_id=actor_user_id,
            action="document.retrieve",
            resource_type="document",
            resource_id=document_id,
            project_id=project_id,
            outcome=outcome,
            reason=reason,
        )
        session.add(event)
        session.flush()
        return event
