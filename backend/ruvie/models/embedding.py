"""Versioned organization embedding connection; document profiles remain immutable."""
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class OrganizationEmbeddingSettings(Base):
    """One connection, initially empty, restricted to the existing vector space."""
    __tablename__ = 'organization_embedding_settings'
    __table_args__ = (
        CheckConstraint('id = 1', name='ck_org_embedding_singleton'),
        CheckConstraint('version >= 0', name='ck_org_embedding_version'),
        CheckConstraint("((network_mode IS NULL AND proxy_url IS NULL) OR (network_mode = 'direct' AND proxy_url IS NULL) OR (network_mode = 'proxy' AND proxy_url IS NOT NULL AND length(trim(proxy_url)) > 0)) IS TRUE", name='ck_org_embedding_network'),
        CheckConstraint("(version = 0 AND base_url IS NULL AND api_key_ciphertext IS NULL AND model_id IS NULL AND dimension IS NULL AND distance_metric IS NULL) OR (version > 0 AND base_url IS NOT NULL AND model_id IS NOT NULL AND model_id = 'baai/bge-m3' AND dimension IS NOT NULL AND dimension = 1024 AND distance_metric IS NOT NULL AND distance_metric = 'cosine')", name='ck_org_embedding_state'),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')
    network_mode: Mapped[str | None] = mapped_column(Text, default='direct', server_default='direct')
    proxy_url: Mapped[str | None] = mapped_column(Text)
    base_url: Mapped[str | None] = mapped_column(Text)
    api_key_ciphertext: Mapped[str | None] = mapped_column(Text)
    model_id: Mapped[str | None] = mapped_column(Text)
    dimension: Mapped[int | None] = mapped_column(Integer)
    distance_metric: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[str | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
