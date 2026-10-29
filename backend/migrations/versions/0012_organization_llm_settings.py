"""Replace personal credentials with one organization connection; keep preferences.

Downgrade restores empty credential columns, never the removed secrets.
"""
from alembic import op
import sqlalchemy as sa

revision = '0012_organization_llm_settings'
down_revision = '0011_user_presence'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'organization_llm_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('base_url', sa.Text()),
        sa.Column('api_key_ciphertext', sa.Text()),
        sa.Column('allowed_model_ids', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('default_model_id', sa.Text()),
        sa.Column('updated_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('id = 1', name='ck_org_llm_singleton'),
        sa.CheckConstraint('version >= 0', name='ck_org_llm_version'),
        sa.CheckConstraint("(version = 0 AND base_url IS NULL AND api_key_ciphertext IS NULL AND default_model_id IS NULL) OR (version > 0 AND base_url IS NOT NULL AND default_model_id IS NOT NULL)", name='ck_org_llm_state'),
    )
    op.execute('INSERT INTO organization_llm_settings (id) VALUES (1)')
    op.drop_constraint('ck_user_llm_settings_key_requires_url', 'user_llm_settings', type_='check')
    for column in ('base_url', 'api_key', 'models'):
        op.drop_column('user_llm_settings', column)


def downgrade() -> None:
    op.add_column('user_llm_settings', sa.Column('base_url', sa.Text()))
    op.add_column('user_llm_settings', sa.Column('api_key', sa.Text()))
    op.add_column('user_llm_settings', sa.Column('models', sa.JSON(), nullable=False, server_default='[]'))
    op.create_check_constraint('ck_user_llm_settings_key_requires_url', 'user_llm_settings',
                               'base_url IS NOT NULL OR api_key IS NULL')
    op.drop_table('organization_llm_settings')
