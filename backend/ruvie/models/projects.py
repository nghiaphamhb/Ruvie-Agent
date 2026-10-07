from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base



class RoleCode(str, Enum):
    """Supported project roles used by document access rules."""
    BIM_CAD_SPECIALIST = "BIM_CAD_SPECIALIST"
    DEVELOPER = "DEVELOPER"
    IT_SUPPORT = "IT_SUPPORT"


class Role(Base):
    """Named role referenced by memberships and document role lists."""
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[RoleCode] = mapped_column(
        SqlEnum(RoleCode, name="role_code", create_constraint=True), unique=True, nullable=False
    )


class Project(Base):
    """Project metadata; membership controls project listing and uploads."""
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Membership(Base):
    """User/project/role link used for document access and upload permissions."""
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "project_id", "role_id", name="uq_membership_user_project_role"),
        Index("ix_memberships_project_user", "project_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
