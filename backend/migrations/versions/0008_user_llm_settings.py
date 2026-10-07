"""Store per-user LLM connections and model preferences."""

from alembic import op
import sqlalchemy as sa


revision = "0008_user_llm_settings"
down_revision = "0007_audit_event_immutability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_llm_settings",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("api_key", sa.Text(), nullable=True),
        sa.Column("models", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("selected_model_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("base_url IS NOT NULL OR api_key IS NULL", name="ck_user_llm_settings_key_requires_url"),
    )


def downgrade() -> None:
    op.drop_table("user_llm_settings")
