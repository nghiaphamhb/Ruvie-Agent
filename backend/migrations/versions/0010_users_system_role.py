"""Add system roles without promoting existing accounts."""
from alembic import op
import sqlalchemy as sa


revision = "0010_users_system_role"
down_revision = "0009_users_email_lower_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Default existing and future accounts to user; only permit known roles."""
    op.add_column(
        "users",
        sa.Column("system_role", sa.String(length=10), nullable=False, server_default="user"),
    )
    op.create_check_constraint(
        "ck_users_system_role", "users", "system_role IN ('user', 'admin')"
    )


def downgrade() -> None:
    """Remove the role column; saved admin assignments are lost on downgrade."""
    op.drop_constraint("ck_users_system_role", "users", type_="check")
    op.drop_column("users", "system_role")
