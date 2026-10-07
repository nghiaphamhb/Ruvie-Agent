from datetime import datetime
from enum import Enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base



class RevisionIngestionState(str, Enum):
    """Revision visibility state: only ready revisions participate in retrieval."""
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class IngestionJobState(str, Enum):
    """Worker lifecycle, separate from whether revision content is searchable."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    """Project document metadata and allowed membership roles."""
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_document_id_project"),
        Index("ix_documents_project_status", "project_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="document", server_default="document"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active", server_default="active"
    )
    # Empty roles grant no membership-based access; direct read grants are checked separately.
    allowed_role_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DocumentRevision(Base):
    """Immutable upload content/profile metadata; only ingestion status may change."""
    __tablename__ = "document_revisions"
    __table_args__ = (
        UniqueConstraint("document_id", "revision_number", name="uq_document_revision_number"),
        UniqueConstraint(
            "id", "document_id", "project_id", name="uq_document_revision_id_document_project"
        ),
        CheckConstraint("revision_number > 0", name="ck_document_revision_number"),
        CheckConstraint("size_bytes >= 0", name="ck_document_revision_size"),
        CheckConstraint(
            "embedding_dimension > 0", name="ck_document_revision_embedding_dimension"
        ),
        CheckConstraint(
            "embedding_distance_metric = 'cosine'", name="ck_document_revision_distance_metric"
        ),
        ForeignKeyConstraint(
            ["document_id", "project_id"],
            ["documents.id", "documents.project_id"],
            ondelete="CASCADE",
        ),
        Index("ix_document_revisions_project_state", "project_id", "ingestion_state"),
        Index("ix_document_revisions_document_state", "document_id", "ingestion_state"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    uploaded_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Private storage reference; only backend services use it after authorization.
    blob_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    software: Mapped[str] = mapped_column(String(255), nullable=False)
    software_version: Mapped[str] = mapped_column(String(255), nullable=False)
    ingestion_state: Mapped[RevisionIngestionState] = mapped_column(
        SqlEnum(
            RevisionIngestionState,
            name="revision_ingestion_state",
            create_constraint=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
        default=RevisionIngestionState.PENDING,
        server_default=RevisionIngestionState.PENDING.value,
    )
    embedding_model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_distance_metric: Mapped[str] = mapped_column(
        String(32), nullable=False, default="cosine", server_default="cosine"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class IngestionJob(Base):
    """One job per revision with bounded attempts and a heartbeat timestamp."""
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        UniqueConstraint("document_revision_id", name="uq_ingestion_job_revision"),
        CheckConstraint("attempt_count >= 0", name="ck_ingestion_job_attempt_count"),
        Index("ix_ingestion_jobs_state_created", "state", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_revision_id: Mapped[str] = mapped_column(
        ForeignKey("document_revisions.id", ondelete="CASCADE"), nullable=False
    )
    state: Mapped[IngestionJobState] = mapped_column(
        SqlEnum(
            IngestionJobState,
            name="ingestion_job_state",
            create_constraint=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
        default=IngestionJobState.PENDING,
        server_default=IngestionJobState.PENDING.value,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DocumentChunk(Base):
    """Immutable text/vector and character offsets belonging to one source revision."""
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_revision_id", "ordinal", name="uq_document_chunk_revision_ordinal"),
        CheckConstraint("ordinal >= 0", name="ck_document_chunk_ordinal"),
        CheckConstraint("start_offset >= 0 AND end_offset >= start_offset", name="ck_document_chunk_offsets"),
        ForeignKeyConstraint(
            ["document_revision_id", "document_id", "project_id"],
            ["document_revisions.id", "document_revisions.document_id", "document_revisions.project_id"],
            ondelete="CASCADE",
        ),
        Index("ix_document_chunks_project_revision", "project_id", "document_revision_id"),
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_revision_id: Mapped[str] = mapped_column(String(36), nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Character positions in the extracted source text; end_offset is exclusive.
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    software: Mapped[str] = mapped_column(String(255), nullable=False)
    software_version: Mapped[str] = mapped_column(String(255), nullable=False)
    # Pinned 1024-dimensional vectors match the cosine index and embedding profile.
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
