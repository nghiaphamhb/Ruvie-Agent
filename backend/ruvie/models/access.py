from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base



class AccessGrant(Base):
    """Direct document-read permission for a user, optionally limited by expiry."""
    __tablename__ = "access_grants"
    __table_args__ = (
        CheckConstraint("resource_type = 'document'", name="ck_access_grant_document_resource"),
        CheckConstraint("principal_type = 'user'", name="ck_access_grant_user_principal"),
        CheckConstraint("permission = 'read'", name="ck_access_grant_read_permission"),
        UniqueConstraint(
            "resource_type",
            "resource_id",
            "principal_type",
            "principal_id",
            "permission",
            name="uq_access_grant_resource_principal_permission",
        ),
        Index("ix_access_grants_principal_resource", "principal_id", "resource_type", "resource_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, default="document", server_default="document")
    resource_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    principal_type: Mapped[str] = mapped_column(String(50), nullable=False, default="user", server_default="user")
    principal_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    permission: Mapped[str] = mapped_column(String(50), nullable=False, default="read", server_default="read")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
