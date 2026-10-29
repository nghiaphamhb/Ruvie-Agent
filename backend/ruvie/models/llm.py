"""Organization provider configuration and private per-user model preferences."""
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class UserLlmSettings(Base):
    """A preference never authorizes a model and never contains credentials."""
    __tablename__ = 'user_llm_settings'
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    selected_model_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class OrganizationLlmSettings(Base):
    """One versioned connection for this deployment; version zero is unconfigured."""
    __tablename__ = 'organization_llm_settings'
    __table_args__ = (
        CheckConstraint('id = 1', name='ck_org_llm_singleton'),
        CheckConstraint('version >= 0', name='ck_org_llm_version'),
        CheckConstraint("(version = 0 AND base_url IS NULL AND api_key_ciphertext IS NULL AND default_model_id IS NULL) OR (version > 0 AND base_url IS NOT NULL AND default_model_id IS NOT NULL)", name='ck_org_llm_state'),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')
    base_url: Mapped[str | None] = mapped_column(Text)
    api_key_ciphertext: Mapped[str | None] = mapped_column(Text)
    allowed_model_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, server_default='[]')
    default_model_id: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[str | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
