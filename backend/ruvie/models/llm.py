from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserLlmSettings(Base):
    """One personal connection or server-model preference per account."""

    __tablename__ = "user_llm_settings"
    __table_args__ = (
        CheckConstraint("base_url IS NOT NULL OR api_key IS NULL", name="ck_user_llm_settings_key_requires_url"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    # NULL URL means a server-model preference, so no server key is copied into this row.
    base_url: Mapped[str | None] = mapped_column(Text)
    # Private provider secret; public responses expose only has_api_key.
    api_key: Mapped[str | None] = mapped_column(Text)
    # Last verified catalog; GET /models fetches fresh data without overwriting this snapshot.
    models: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    selected_model_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
