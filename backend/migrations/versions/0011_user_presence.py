"""Track recent session presence and retain the account's last activity."""
from alembic import op
import sqlalchemy as sa

revision = "0011_user_presence"
down_revision = "0010_users_system_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing sessions remain unknown until the browser sends a real heartbeat.
    op.add_column("users", sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("auth_sessions", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("auth_sessions", "last_seen_at")
    op.drop_column("users", "last_active_at")
