"""Record the user who uploaded each new document revision."""

from alembic import op
import sqlalchemy as sa


revision = "0006_revision_uploader"
down_revision = "0005_auth_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_revisions",
        sa.Column("uploaded_by_user_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_document_revisions_uploaded_by_user_id_users",
        "document_revisions",
        "users",
        ["uploaded_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_document_revisions_uploaded_by_user_id_users",
        "document_revisions",
        type_="foreignkey",
    )
    op.drop_column("document_revisions", "uploaded_by_user_id")
