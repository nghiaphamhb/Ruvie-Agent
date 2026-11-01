"""Durable private chat history. Source identifiers are retained after source deletion."""
from datetime import datetime
from sqlalchemy import (CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint,
                        Index, Integer, JSON, String, Text, UniqueConstraint, func, text)
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class ChatConversation(Base):
    """Owner metadata; activity timestamps change only for accepted writes."""
    __tablename__ = 'chat_conversations'
    __table_args__ = (
        UniqueConstraint('id', 'owner_user_id', name='uq_chat_conversation_owner'),
        CheckConstraint('length(trim(title)) BETWEEN 1 AND 120', name='ck_chat_title'),
        CheckConstraint('version > 0', name='ck_chat_version'),
        Index('ix_chat_owner_activity', 'owner_user_id', text('updated_at DESC'), text('id DESC')),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ChatTurn(Base):
    """An immutable question; the newest attempt is selected by its attempt ordinal."""
    __tablename__ = 'chat_turns'
    __table_args__ = (
        UniqueConstraint('conversation_id', 'ordinal', name='uq_chat_turn_order'),
        UniqueConstraint('id', 'conversation_id', name='uq_chat_turn_conversation'),
        CheckConstraint('ordinal > 0', name='ck_chat_turn_order'),
        CheckConstraint('length(trim(question)) > 0', name='ck_chat_question'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey('chat_conversations.id', ondelete='CASCADE'), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ChatGenerationAttempt(Base):
    """One fenced generation with an owner-scoped idempotency key and finite lease."""
    __tablename__ = 'chat_generation_attempts'
    __table_args__ = (
        ForeignKeyConstraint(['conversation_id', 'owner_user_id'],
            ['chat_conversations.id', 'chat_conversations.owner_user_id'], ondelete='CASCADE'),
        ForeignKeyConstraint(['turn_id', 'conversation_id'],
            ['chat_turns.id', 'chat_turns.conversation_id'], ondelete='CASCADE'),
        UniqueConstraint('owner_user_id', 'request_id', name='uq_chat_owner_request'),
        UniqueConstraint('turn_id', 'ordinal', name='uq_chat_attempt_order'),
        CheckConstraint('ordinal > 0', name='ck_chat_attempt_order'),
        CheckConstraint("state IN ('generating','completed','stopped','error','interrupted')", name='ck_chat_attempt_state'),
        CheckConstraint("(state = 'generating' AND finished_at IS NULL) OR (state <> 'generating' AND finished_at IS NOT NULL)", name='ck_chat_attempt_terminal'),
        Index('uq_chat_active_generation', 'conversation_id', unique=True,
              postgresql_where=text("state = 'generating'"), sqlite_where=text("state = 'generating'")),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    turn_id: Mapped[str] = mapped_column(String(36), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    model_id: Mapped[str] = mapped_column(String(500), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False, default='', server_default='')
    state: Mapped[str] = mapped_column(String(20), nullable=False, default='generating', server_default='generating')
    error_code: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChatAttemptSource(Base):
    """Snapshot provenance, never cascaded away by deletion of a document/chunk."""
    __tablename__ = 'chat_attempt_sources'
    __table_args__ = (CheckConstraint('ordinal > 0', name='ck_chat_source_order'),)
    attempt_id: Mapped[str] = mapped_column(ForeignKey('chat_generation_attempts.id', ondelete='CASCADE'), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    revision_id: Mapped[str] = mapped_column(String(36), nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(36), nullable=False)
    citation: Mapped[dict] = mapped_column(JSON, nullable=False)
