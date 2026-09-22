"""Create the F003 ingestion and authorized RAG schema."""

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_ingestion_rag_schema"
down_revision = "0002_domain_acl"
branch_labels = None
depends_on = None


revision_ingestion_state = postgresql.ENUM(
    "pending", "ready", "failed", name="revision_ingestion_state", create_type=False
)
ingestion_job_state = postgresql.ENUM(
    "pending", "running", "completed", "failed", name="ingestion_job_state", create_type=False
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    revision_ingestion_state.create(op.get_bind(), checkfirst=False)
    ingestion_job_state.create(op.get_bind(), checkfirst=False)
    op.create_unique_constraint("uq_document_id_project", "documents", ["id", "project_id"])
    op.create_table(
        "document_revisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("blob_uri", sa.String(length=2048), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("software", sa.String(length=255), nullable=False),
        sa.Column("software_version", sa.String(length=255), nullable=False),
        sa.Column("ingestion_state", revision_ingestion_state, server_default=sa.text("'pending'"), nullable=False),
        sa.Column("embedding_model_id", sa.String(length=255), nullable=False),
        sa.Column("embedding_model_version", sa.String(length=255), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("embedding_distance_metric", sa.String(length=32), server_default=sa.text("'cosine'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("revision_number > 0", name="ck_document_revision_number"),
        sa.CheckConstraint("size_bytes >= 0", name="ck_document_revision_size"),
        sa.CheckConstraint("embedding_dimension > 0", name="ck_document_revision_embedding_dimension"),
        sa.CheckConstraint("embedding_distance_metric = 'cosine'", name="ck_document_revision_distance_metric"),
        sa.ForeignKeyConstraint(
            ["document_id", "project_id"], ["documents.id", "documents.project_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "revision_number", name="uq_document_revision_number"),
        sa.UniqueConstraint("id", "document_id", "project_id", name="uq_document_revision_id_document_project"),
    )
    op.create_index("ix_document_revisions_project_state", "document_revisions", ["project_id", "ingestion_state"])
    op.create_index("ix_document_revisions_document_state", "document_revisions", ["document_id", "ingestion_state"])
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_revision_id", sa.String(length=36), nullable=False),
        sa.Column("state", ingestion_job_state, server_default=sa.text("'pending'"), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("attempt_count >= 0", name="ck_ingestion_job_attempt_count"),
        sa.ForeignKeyConstraint(["document_revision_id"], ["document_revisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_revision_id", name="uq_ingestion_job_revision"),
    )
    op.create_index("ix_ingestion_jobs_state_created", "ingestion_jobs", ["state", "created_at"])
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_revision_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("software", sa.String(length=255), nullable=False),
        sa.Column("software_version", sa.String(length=255), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("ordinal >= 0", name="ck_document_chunk_ordinal"),
        sa.CheckConstraint("start_offset >= 0 AND end_offset >= start_offset", name="ck_document_chunk_offsets"),
        sa.ForeignKeyConstraint(
            ["document_revision_id", "document_id", "project_id"],
            ["document_revisions.id", "document_revisions.document_id", "document_revisions.project_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_revision_id", "ordinal", name="uq_document_chunk_revision_ordinal"),
    )
    op.create_index("ix_document_chunks_project_revision", "document_chunks", ["project_id", "document_revision_id"])
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_embedding_hnsw", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_table("ingestion_jobs")
    op.drop_table("document_revisions")
    op.drop_constraint("uq_document_id_project", "documents", type_="unique")
    ingestion_job_state.drop(op.get_bind(), checkfirst=False)
    revision_ingestion_state.drop(op.get_bind(), checkfirst=False)
