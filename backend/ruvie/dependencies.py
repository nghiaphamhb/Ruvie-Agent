from collections.abc import Iterator

from fastapi import HTTPException, Request
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


def get_blob_store(request: Request) -> BlobStore:
    """Provide private storage to authorized services, not a public download URL."""
    return request.app.state.blob_store


def get_query_embedder(request: Request) -> QueryEmbedder:
    """Provide the configured embedding adapter or report HTTP 503."""
    embedder = request.app.state.query_embedder
    if embedder is None:
        raise HTTPException(status_code=503, detail="query embedding is not configured")
    return embedder
