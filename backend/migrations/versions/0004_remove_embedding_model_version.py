"""Remove the provider-specific embedding model version requirement."""

from alembic import op
import sqlalchemy as sa


revision = "0004_remove_embedding_model_version"
down_revision = "0003_ingestion_rag_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("document_revisions", "embedding_model_version")


def downgrade() -> None:
    op.add_column(
        "document_revisions",
        sa.Column(
            "embedding_model_version",
            sa.String(length=255),
            server_default=sa.text("'legacy-unspecified'"),
            nullable=False,
        ),
    )
    op.alter_column("document_revisions", "embedding_model_version", server_default=None)
