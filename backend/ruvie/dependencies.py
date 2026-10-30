from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ruvie.adapters.embedding import QueryEmbedder
from ruvie.config import Settings
from ruvie.services.documents.upload import BlobStore


def get_settings(request: Request) -> Settings:
    """Read server settings from app state, never from the request body."""
    return request.app.state.settings


def get_authenticated_user_id(request: Request) -> str:
    """Resolve the session cookie to an active user ID; reject invalid sessions."""
    # Only trusted server code sets this cached identity; clients cannot supply it.
    user_id = getattr(request.state, "domain_user_id", None)
    if user_id:
        return user_id
    token = request.cookies.get("ruvie_session")
    factory = getattr(request.app.state, "session_factory", None)
    if token and factory:
        from ruvie.services.auth import AuthService

        with factory() as session:
            resolved = AuthService(session).resolve_session(token)
            if resolved is not None:
                request.state.domain_user_id = resolved.user.id
                return resolved.user.id
    raise HTTPException(status_code=401, detail="authentication required")


def get_session(request: Request) -> Iterator[Session]:
    """Yield one DB session for the request; close it after the response."""
    with request.app.state.session_factory() as session:
        yield session


def get_admin_user_id(request: Request, db: Session = Depends(get_session)) -> str:
    """Resolve the cookie identity and ask the service to verify current administrator rights."""
    from ruvie.services.admin import AdminAccountService

    try:
        user_id = get_authenticated_user_id(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail={"code": "authentication_required"}) from None
    return AdminAccountService(db).require_admin(user_id).id


def get_blob_store(request: Request) -> BlobStore:
    """Provide private storage to authorized services, not a public download URL."""
    return request.app.state.blob_store


def get_query_embedder(request: Request) -> QueryEmbedder:
    """Resolve a fresh database snapshot; trusted dependency overrides remain injectable."""
    from ruvie.services.embedding import EmbeddingConnectionService, EmbeddingUnavailableError
    from ruvie.services.llm_secrets import LlmSecretError
    from sqlalchemy.exc import SQLAlchemyError
    try:
        with request.app.state.session_factory() as session:
            return EmbeddingConnectionService(session, request.app.state.settings).resolve_embedder()
    except (EmbeddingUnavailableError, LlmSecretError, SQLAlchemyError):
        raise HTTPException(503, detail={'code':'embedding_unavailable'}) from None
