"""Add independent DB-owned SOCKS5 routes. Existing rows remain pending."""
from alembic import op
import sqlalchemy as sa

revision = '0014_ai_network_connections'
down_revision = '0013_org_embedding_settings'
branch_labels = None
depends_on = None

def upgrade():
    for table, prefix in (
        ('organization_llm_settings', 'org_llm'),
        ('organization_embedding_settings', 'org_embedding'),
    ):
        # No default during ADD COLUMN: pre-existing rows must remain NULL/pending.
        op.add_column(table, sa.Column('network_mode', sa.Text(), nullable=True))
        op.add_column(table, sa.Column('proxy_url', sa.Text(), nullable=True))
        op.create_check_constraint(
            f'ck_{prefix}_network', table,
            "(network_mode IS NULL AND proxy_url IS NULL) OR "
            "(network_mode = 'direct' AND proxy_url IS NULL) OR "
            "(network_mode = 'proxy' AND proxy_url IS NOT NULL AND length(trim(proxy_url)) > 0)"
        )
        # Defaults apply to new rows only, not historical rows.
        op.alter_column(table, 'network_mode', server_default='direct')

def downgrade():
    for table, prefix in (
        ('organization_embedding_settings', 'org_embedding'),
        ('organization_llm_settings', 'org_llm'),
    ):
        op.drop_constraint(f'ck_{prefix}_network', table, type_='check')
        op.drop_column(table, 'proxy_url')
        op.drop_column(table, 'network_mode')
