from contextlib import suppress
from dataclasses import dataclass
from hashlib import sha256
from os import name as os_name
from pathlib import Path
from typing import Protocol
from urllib.parse import unquote, urlparse
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ruvie.config import EmbeddingProfile
from ruvie.domain import (
    Document,
    DocumentRevision,
    IngestionJob,
    Membership,
    RevisionIngestionState,
    Role,
)


class BlobStore(Protocol):
    def put(self, *, key: str, content: bytes, mime_type: str) -> str: ...

    def get(self, uri: str) -> bytes: ...

    def delete(self, uri: str) -> None: ...


class S3Client(Protocol):
    def put_object(self, **kwargs: object) -> object: ...

    def delete_object(self, **kwargs: object) -> object: ...

    def get_object(self, **kwargs: object) -> object: ...


class UploadValidationError(ValueError):
    pass


class UploadAuthorizationError(PermissionError):
    pass


class LocalBlobStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def put(self, *, key: str, content: bytes, mime_type: str) -> str:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path.as_uri()

    def delete(self, uri: str) -> None:
        path = Path(uri.removeprefix("file://")).resolve()
        if path.is_relative_to(self.root):
            path.unlink(missing_ok=True)

    def get(self, uri: str) -> bytes:
        path = unquote(urlparse(uri).path)
        return Path(path[1:] if os_name == "nt" and path.startswith("/") else path).read_bytes()

    def _path_for(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise UploadValidationError("blob key must stay inside local storage")
        return path


class S3BlobStore:
    def __init__(self, client: S3Client, *, bucket: str, prefix: str = "") -> None:
        self.client = client
        self.bucket = bucket
        self.prefix = prefix.strip("/")

    def put(self, *, key: str, content: bytes, mime_type: str) -> str:
        object_key = self._object_key(key)
        self.client.put_object(Bucket=self.bucket, Key=object_key, Body=content, ContentType=mime_type, ACL="private")
        return f"s3://{self.bucket}/{object_key}"

    def delete(self, uri: str) -> None:
        object_key = uri.removeprefix(f"s3://{self.bucket}/")
        self.client.delete_object(Bucket=self.bucket, Key=object_key)

    def get(self, uri: str) -> bytes:
        object_key = uri.removeprefix(f"s3://{self.bucket}/")
        return self.client.get_object(Bucket=self.bucket, Key=object_key)["Body"].read()

    def _object_key(self, key: str) -> str:
        key = key.lstrip("/")
        return f"{self.prefix}/{key}" if self.prefix else key


@dataclass(frozen=True)
class UploadRequest:
    actor_user_id: str
    project_id: str
    title: str
    filename: str
    content: bytes
    mime_type: str
    software: str
    software_version: str
    allowed_role_codes: list[str]
    document_id: str | None = None


@dataclass(frozen=True)
class UploadResult:
    document_id: str
    revision_id: str
    job_id: str
    blob_uri: str
    content_hash: str


class DocumentUploadService:
    def __init__(self, session: Session, blob_store: BlobStore, embedding_profile: EmbeddingProfile) -> None:
        self.session = session
        self.blob_store = blob_store
        self.embedding_profile = embedding_profile

    def create_revision(self, request: UploadRequest) -> UploadResult:
        self._validate(request)
        self._require_membership(request.actor_user_id, request.project_id)
        self._require_known_roles(request.allowed_role_codes)

        document = self._document_for(request)
        revision_number = self._next_revision_number(document.id)
        revision_id = str(uuid4())
        content_hash = sha256(request.content).hexdigest()
        suffix = Path(request.filename).suffix.lower()
        key = f"projects/{request.project_id}/documents/{document.id}/revisions/{revision_number}/{revision_id}{suffix}"
        blob_uri = self.blob_store.put(key=key, content=request.content, mime_type=request.mime_type)
        revision = DocumentRevision(
            id=revision_id,
            document_id=document.id,
            project_id=request.project_id,
            revision_number=revision_number,
            content_hash=content_hash,
            blob_uri=blob_uri,
            mime_type=request.mime_type,
            size_bytes=len(request.content),
            software=request.software,
            software_version=request.software_version,
            ingestion_state=RevisionIngestionState.PENDING,
            embedding_model_id=self.embedding_profile.model_id,
            embedding_model_version=self.embedding_profile.model_version,
            embedding_dimension=self.embedding_profile.dimension,
            embedding_distance_metric=self.embedding_profile.distance_metric,
        )
        job = IngestionJob(id=str(uuid4()), document_revision_id=revision.id)

        try:
            if request.document_id is None:
                self.session.add(document)
            self.session.add_all((revision, job))
            self.session.commit()
        except Exception:
            self.session.rollback()
            with suppress(Exception):
                self.blob_store.delete(blob_uri)
            raise

        return UploadResult(document.id, revision.id, job.id, blob_uri, content_hash)

    def _validate(self, request: UploadRequest) -> None:
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
        membership_id = self.session.scalar(
            select(Membership.id).where(Membership.user_id == user_id, Membership.project_id == project_id).limit(1)
        )
        if membership_id is None:
            raise UploadAuthorizationError("project membership is required for upload")

    def _require_known_roles(self, role_codes: list[str]) -> None:
        known_codes = {role.value for role in self.session.scalars(select(Role.code))}
        if not set(role_codes).issubset(known_codes):
            raise UploadValidationError("allowed_role_codes contains an unknown role")

    def _document_for(self, request: UploadRequest) -> Document:
        if request.document_id is None:
            return Document(
                id=str(uuid4()),
                project_id=request.project_id,
                title=request.title,
                allowed_role_codes=request.allowed_role_codes,
            )

        document = self.session.get(Document, request.document_id)
        if document is None or document.project_id != request.project_id:
            raise UploadValidationError("document does not belong to project")
        return document

    def _next_revision_number(self, document_id: str) -> int:
        previous = self.session.scalar(
            select(func.max(DocumentRevision.revision_number)).where(DocumentRevision.document_id == document_id)
        )
        return (previous or 0) + 1
