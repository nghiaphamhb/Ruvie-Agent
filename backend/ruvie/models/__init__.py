"""Import all models so Base.metadata and Alembic see every active table."""

from .base import Base
from .auth import AuthSession, User
from .projects import Membership, Project, Role, RoleCode
from .documents import (
    Document,
    DocumentChunk,
    DocumentRevision,
    IngestionJob,
    IngestionJobState,
    RevisionIngestionState,
)
from .access import AccessGrant
from .audit import AuditEvent
from .llm import OrganizationLlmSettings, UserLlmSettings
from .embedding import OrganizationEmbeddingSettings

__all__ = [
    "Base",
    "AuthSession",
    "User",
    "UserLlmSettings",
    "OrganizationLlmSettings",
    "OrganizationEmbeddingSettings",
    "Membership",
    "Project",
    "Role",
    "RoleCode",
    "Document",
    "DocumentChunk",
    "DocumentRevision",
    "IngestionJob",
    "IngestionJobState",
    "RevisionIngestionState",
    "AccessGrant",
    "AuditEvent",
]
