import base64
from pathlib import Path
from typing import Protocol

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ruvie.config import load_settings
from ruvie.database import create_database_engine
from ruvie.document_retrieval import AuthorizedScope, PgvectorChunkRepository
from ruvie.document_citation import CitationBuilder
from ruvie.domain import Document, DocumentRevision
from ruvie.document_upload import DocumentUploadService, LocalBlobStore, UploadRequest


router = APIRouter(prefix="/documents", tags=["documents"])


class UploadBody(BaseModel):
    project_id: str
    title: str
    filename: str
    content_base64: str
    mime_type: str
    software: str
    software_version: str
    allowed_role_codes: list[str]


class RetrievalBody(BaseModel):
    query: str
    limit: int = 10


class QueryEmbedder(Protocol):
    def embed_query(self, query: str) -> list[float]: ...


def get_authenticated_user_id(request: Request) -> str:
    user_id = getattr(request.state, "domain_user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="authentication required")
    return user_id


def get_session():
    with Session(create_database_engine()) as session:
        yield session


def get_blob_store() -> LocalBlobStore:
    return LocalBlobStore(Path("data/uploads"))


def get_query_embedder() -> QueryEmbedder:
    raise HTTPException(status_code=501, detail="query embedding is not configured")


@router.post("/upload")
def upload_document(body: UploadBody, user_id: str = Depends(get_authenticated_user_id), session: Session = Depends(get_session), blob_store: LocalBlobStore = Depends(get_blob_store)) -> dict[str, str]:
    try:
        content = base64.b64decode(body.content_base64, validate=True)
        result = DocumentUploadService(session, blob_store, load_settings().embedding_profile).create_revision(UploadRequest(user_id, body.project_id, body.title, body.filename, content, body.mime_type, body.software, body.software_version, body.allowed_role_codes))
        return {"document_id": result.document_id, "revision_id": result.revision_id, "job_id": result.job_id}
    except (ValueError, PermissionError) as error:
        raise HTTPException(status_code=403 if isinstance(error, PermissionError) else 422, detail="upload rejected") from error


@router.post("/retrieve")
def retrieve_chunks(body: RetrievalBody, user_id: str = Depends(get_authenticated_user_id), session: Session = Depends(get_session), embedder: QueryEmbedder = Depends(get_query_embedder)) -> list[dict[str, object]]:
    if not body.query.strip():
        raise HTTPException(status_code=422, detail="query is required")
    chunks = PgvectorChunkRepository(session).search(AuthorizedScope.for_user(user_id), embedder.embed_query(body.query), limit=body.limit)
    results = []
    for chunk in chunks:
        revision = session.get(DocumentRevision, chunk.document_revision_id)
        document = session.get(Document, chunk.document_id)
        citation = CitationBuilder.build(document.id, revision.id, chunk.id, chunk.ordinal, chunk.start_offset, chunk.end_offset, document.title, revision.content_hash, chunk.software, chunk.software_version)
        results.append({"chunk_id": chunk.id, "document_id": chunk.document_id, "text": chunk.text, "citation": citation.to_dict()})
    return results
