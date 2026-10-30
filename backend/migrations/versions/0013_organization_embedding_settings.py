"""Add an empty embedding connection; downgrade discards it without exporting keys."""
from alembic import op
import sqlalchemy as sa

revision = '0013_org_embedding_settings'
down_revision = '0012_organization_llm_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the singleton without reading environment or reply credentials."""
    op.create_table(
        'organization_embedding_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('base_url', sa.Text()),
        sa.Column('api_key_ciphertext', sa.Text()),
        sa.Column('model_id', sa.Text()),
        sa.Column('dimension', sa.Integer()),
        sa.Column('distance_metric', sa.Text()),
        sa.Column('updated_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('id = 1', name='ck_org_embedding_singleton'),
        sa.CheckConstraint('version >= 0', name='ck_org_embedding_version'),
        sa.CheckConstraint("(version = 0 AND base_url IS NULL AND api_key_ciphertext IS NULL AND model_id IS NULL AND dimension IS NULL AND distance_metric IS NULL) OR (version > 0 AND base_url IS NOT NULL AND model_id IS NOT NULL AND model_id = 'baai/bge-m3' AND dimension IS NOT NULL AND dimension = 1024 AND distance_metric IS NOT NULL AND distance_metric = 'cosine')", name='ck_org_embedding_state'),
    )
    op.execute('INSERT INTO organization_embedding_settings (id) VALUES (1)')


def downgrade() -> None:
    """Remove only the new settings; no plaintext/environment restoration."""
    op.drop_table('organization_embedding_settings')
