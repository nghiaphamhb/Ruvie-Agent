"""Enforce network pairs and initialize routes only for a fresh migration chain."""
from alembic import op

revision = '0015_ai_network_constraints'
down_revision = '0014_ai_network_connections'
branch_labels = None
depends_on = None

_PAIRS = (
    "(network_mode IS NULL AND proxy_url IS NULL) OR "
    "(network_mode = 'direct' AND proxy_url IS NULL) OR "
    "(network_mode = 'proxy' AND proxy_url IS NOT NULL AND length(trim(proxy_url)) > 0)"
)


def upgrade():
    """Keep existing routes/pending states; CHECK must reject SQL UNKNOWN too."""
    for table, prefix in (('organization_llm_settings', 'org_llm'),
                          ('organization_embedding_settings', 'org_embedding')):
        op.drop_constraint(f'ck_{prefix}_network', table, type_='check')
        op.create_check_constraint(f'ck_{prefix}_network', table, f'({_PAIRS}) IS TRUE')
        if op.get_context().config.attributes.get('fresh_database', False):
            op.execute(f"UPDATE {table} SET network_mode = 'direct' "
                       "WHERE network_mode IS NULL AND proxy_url IS NULL AND version = 0")


def downgrade():
    """Restore the previous constraint without changing any route or credentials."""
    for table, prefix in (('organization_llm_settings', 'org_llm'),
                          ('organization_embedding_settings', 'org_embedding')):
        op.drop_constraint(f'ck_{prefix}_network', table, type_='check')
        op.create_check_constraint(f'ck_{prefix}_network', table, _PAIRS)
