"""Make registration email identity unique regardless of letter case."""
from alembic import op
import sqlalchemy as sa

revision = "0009_users_email_lower_unique"
down_revision = "0008_user_llm_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL rejects existing collisions atomically; never merge or delete accounts.
    op.create_index("uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True)


def downgrade() -> None:
    op.drop_index("uq_users_email_lower", table_name="users")
