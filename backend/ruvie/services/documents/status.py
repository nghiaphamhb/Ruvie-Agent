from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ruvie.models import DocumentRevision, IngestionJob, IngestionJobState, RevisionIngestionState
from ruvie.services.access import DocumentAccessService


@dataclass(frozen=True)
class RevisionStatus:
    """Safe ingestion status/error code for the uploader or an authorized reader."""
    revision_id: str
    status: str
    error_code: str | None


class DocumentStatusService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_revision_status(self, user_id: str, revision_id: str) -> RevisionStatus | None:
        """Return status for the uploader/readable document; otherwise return None."""
        row = self.session.execute(
            select(DocumentRevision, IngestionJob.state, IngestionJob.error_code)
            .outerjoin(IngestionJob, IngestionJob.document_revision_id == DocumentRevision.id)
            .where(DocumentRevision.id == revision_id)
        ).one_or_none()
        if row is None:
            return None

        revision, job_state, job_error_code = row
        # The uploader can follow their job; other users must pass document-read authorization.
        if revision.uploaded_by_user_id != user_id and not DocumentAccessService.can_read_document(
            self.session, user_id, revision.document_id
        ):
            return None

        if job_state == IngestionJobState.RUNNING:
            status = "running"
        elif revision.ingestion_state == RevisionIngestionState.READY:
            status = "ready"
        elif revision.ingestion_state == RevisionIngestionState.FAILED:
            status = "failed"
        else:
            status = "pending"

        error_code = job_error_code if status == "failed" else None
        return RevisionStatus(revision.id, status, error_code)
