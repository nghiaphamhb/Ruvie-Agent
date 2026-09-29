from collections.abc import Iterator

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from ruvie.adapters.embedding import QueryEmbedder
from ruvie.adapters.llm import LlmAdapter
from ruvie.config import Settings
from ruvie.document_upload import BlobStore


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_authenticated_user_id(request: Request) -> str:
    user_id = getattr(request.state, "domain_user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="authentication required")
    return user_id


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def get_blob_store(request: Request) -> BlobStore:
    return request.app.state.blob_store


def get_query_embedder(request: Request) -> QueryEmbedder:
    embedder = request.app.state.query_embedder
    if embedder is None:
        raise HTTPException(status_code=503, detail="query embedding is not configured")
    return embedder


def get_llm_adapter(request: Request) -> LlmAdapter:
    adapter = request.app.state.llm_adapter
    if adapter is None:
        raise HTTPException(status_code=503, detail="LLM provider is not configured")
    return adapter
