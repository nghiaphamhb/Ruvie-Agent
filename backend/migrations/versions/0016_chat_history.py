"""Private relational chat history with fenced generation attempts."""
from alembic import op
import sqlalchemy as sa

revision = '0016_chat_history'
down_revision = '0015_ai_network_constraints'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('chat_conversations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(120), nullable=False),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('id', 'owner_user_id', name='uq_chat_conversation_owner'),
        sa.CheckConstraint('length(trim(title)) BETWEEN 1 AND 120', name='ck_chat_title'),
        sa.CheckConstraint('version > 0', name='ck_chat_version'))
    op.create_index('ix_chat_owner_activity', 'chat_conversations', ['owner_user_id', sa.text('updated_at DESC'), sa.text('id DESC')])
    op.create_table('chat_turns',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('chat_conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ordinal', sa.Integer, nullable=False),
        sa.Column('question', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('conversation_id', 'ordinal', name='uq_chat_turn_order'),
        sa.UniqueConstraint('id', 'conversation_id', name='uq_chat_turn_conversation'),
        sa.CheckConstraint('ordinal > 0', name='ck_chat_turn_order'),
        sa.CheckConstraint('length(trim(question)) > 0', name='ck_chat_question'))
    op.create_table('chat_generation_attempts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('turn_id', sa.String(36), nullable=False),
        sa.Column('conversation_id', sa.String(36), nullable=False),
        sa.Column('owner_user_id', sa.String(36), nullable=False),
        sa.Column('request_id', sa.String(36), nullable=False),
        sa.Column('request_fingerprint', sa.String(64), nullable=False),
        sa.Column('ordinal', sa.Integer, nullable=False, server_default='1'),
        sa.Column('model_id', sa.String(500), nullable=False),
        sa.Column('answer', sa.Text, nullable=False, server_default=''),
        sa.Column('state', sa.String(20), nullable=False, server_default='generating'),
        sa.Column('error_code', sa.String(100)),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('finished_at', sa.DateTime(timezone=True)),
        sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id', 'owner_user_id'], ['chat_conversations.id', 'chat_conversations.owner_user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['turn_id', 'conversation_id'], ['chat_turns.id', 'chat_turns.conversation_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('owner_user_id', 'request_id', name='uq_chat_owner_request'),
        sa.UniqueConstraint('turn_id', 'ordinal', name='uq_chat_attempt_order'),
        sa.CheckConstraint('ordinal > 0', name='ck_chat_attempt_order'),
        sa.CheckConstraint("state IN ('generating','completed','stopped','error','interrupted')", name='ck_chat_attempt_state'),
        sa.CheckConstraint("(state = 'generating' AND finished_at IS NULL) OR (state <> 'generating' AND finished_at IS NOT NULL)", name='ck_chat_attempt_terminal'))
    op.create_index('uq_chat_active_generation', 'chat_generation_attempts', ['conversation_id'], unique=True, postgresql_where=sa.text("state = 'generating'"))
    op.create_table('chat_attempt_sources',
        sa.Column('attempt_id', sa.String(36), sa.ForeignKey('chat_generation_attempts.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('ordinal', sa.Integer, primary_key=True),
        sa.Column('document_id', sa.String(36), nullable=False),
        sa.Column('revision_id', sa.String(36), nullable=False),
        sa.Column('chunk_id', sa.String(36), nullable=False),
        sa.Column('citation', sa.JSON, nullable=False),
        sa.CheckConstraint('ordinal > 0', name='ck_chat_source_order'))


def downgrade():
    for table in ('chat_attempt_sources', 'chat_generation_attempts', 'chat_turns', 'chat_conversations'):
        op.drop_table(table)
