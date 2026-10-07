from contextlib import suppress
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ruvie.config import EmbeddingProfile
from ruvie.models import (
    Document,
    DocumentRevision,
    IngestionJob,
    Membership,
    Project,
    RevisionIngestionState,
    RoleCode,
)
from ruvie.services.audit import AuditEventWriter


class BlobStore(Protocol):
    """Private storage contract; returned URIs stay inside backend services."""

    def put(self, *, key: str, content: bytes, mime_type: str) -> str: ...

    def get(self, uri: str) -> bytes: ...

    def delete(self, uri: str) -> None: ...


class UploadValidationError(ValueError):
    pass


class UploadAuthorizationError(PermissionError):
    pass


@dataclass(frozen=True)
class UploadRequest:
    """Upload metadata/bytes with actor ID from the session; document_id enables a new revision."""
    actor_user_id: str
    project_id: str
    title: str
    filename: str
    content: bytes
    mime_type: str
    software: str
    software_version: str
    document_id: str | None = None


@dataclass(frozen=True)
class UploadResult:
    """Internal upload result; API omits blob_uri and content_hash from its response."""
    document_id: str
    revision_id: str
    job_id: str
    blob_uri: str
    content_hash: str


class DocumentUploadService:
    def __init__(
        self,
        session: Session,
        blob_store: BlobStore,
        embedding_profile: EmbeddingProfile,
    ) -> None:
        self.session = session
        self.blob_store = blob_store
        self.embedding_profile = embedding_profile

    def create_revision(self, request: UploadRequest) -> UploadResult:
        """Validate membership, store a new revision/job/audit, and return internal IDs."""
        self._validate(request)
        self._require_membership(request.actor_user_id, request.project_id)

        document = self._document_for(request)
        revision_number = self._next_revision_number(document.id)
        revision_id = str(uuid4())
        # Hash and unique revision key identify this upload without overwriting older content.
        content_hash = sha256(request.content).hexdigest()
        suffix = Path(request.filename).suffix.lower()
        key = f"projects/{request.project_id}/documents/{document.id}/revisions/{revision_number}/{revision_id}{suffix}"
        blob_uri = self.blob_store.put(key=key, content=request.content, mime_type=request.mime_type)
        revision = DocumentRevision(
            id=revision_id,
            document_id=document.id,
            project_id=request.project_id,
            uploaded_by_user_id=request.actor_user_id,
            revision_number=revision_number,
            content_hash=content_hash,
            blob_uri=blob_uri,
            mime_type=request.mime_type,
            size_bytes=len(request.content),
            software=request.software,
            software_version=request.software_version,
            ingestion_state=RevisionIngestionState.PENDING,
            embedding_model_id=self.embedding_profile.model_id,
            embedding_dimension=self.embedding_profile.dimension,
            embedding_distance_metric=self.embedding_profile.distance_metric,
        )
        job = IngestionJob(id=str(uuid4()), document_revision_id=revision.id)

        try:
            if request.document_id is None:
                self.session.add(document)
            self.session.add_all((revision, job))
            AuditEventWriter.append(
                self.session,
                request.actor_user_id,
                action="document.upload",
                resource_type="document",
                resource_id=document.id,
                project_id=request.project_id,
                outcome="allow",
                reason="revision_created",
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            # If DB persistence fails, best-effort cleanup removes the newly written private blob.
            with suppress(Exception):
                self.blob_store.delete(blob_uri)
            raise

        return UploadResult(document.id, revision.id, job.id, blob_uri, content_hash)

    def _validate(self, request: UploadRequest) -> None:
        """Reject blank required metadata and empty bytes before writing a blob."""
        for name, value in (
            ("project_id", request.project_id),
            ("title", request.title),
            ("filename", request.filename),
            ("mime_type", request.mime_type),
            ("software", request.software),
            ("software_version", request.software_version),
        ):
            if not value.strip():
                raise UploadValidationError(f"{name} is required")
        if not request.content:
            raise UploadValidationError("content is required")

    def _require_membership(self, user_id: str, project_id: str) -> None:
        """Require project membership; audit and reject unauthorized uploads."""
        membership_id = self.session.scalar(
            select(Membership.id).where(Membership.user_id == user_id, Membership.project_id == project_id).limit(1)
        )
        if membership_id is None:
            project_exists = self.session.scalar(select(Project.id).where(Project.id == project_id)) is not None
            AuditEventWriter.append(
                self.session,
                user_id,
                action="document.upload",
                resource_type="project",
                resource_id=project_id,
                project_id=project_id if project_exists else None,
                outcome="deny",
                reason="project_membership_required",
            )
            self.session.commit()
            raise UploadAuthorizationError("project membership is required for upload")

    def _document_for(self, request: UploadRequest) -> Document:
        """Create a document or verify the existing document belongs to the requested project."""
        if request.document_id is None:
            return Document(
                id=str(uuid4()),
                project_id=request.project_id,
                title=request.title,
                allowed_role_codes=[role.value for role in RoleCode],
            )

        document = self.session.get(Document, request.document_id)
        if document is None or document.project_id != request.project_id:
            raise UploadValidationError("document does not belong to project")
        return document

    def _next_revision_number(self, document_id: str) -> int:
        """Return the next revision number without overwriting previous content."""
        previous = self.session.scalar(
            select(func.max(DocumentRevision.revision_number)).where(DocumentRevision.document_id == document_id)
        )
        return (previous or 0) + 1
