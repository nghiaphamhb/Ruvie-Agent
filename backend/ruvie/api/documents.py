from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from ruvie.adapters.embedding import QueryEmbedder
from ruvie.api.security import check_origin, verify_csrf
from ruvie.config import Settings
from ruvie.contracts.documents import RetrievalBody
from ruvie.dependencies import get_authenticated_user_id, get_blob_store, get_query_embedder, get_session, get_settings
from ruvie.services.documents.upload import (
    BlobStore,
    DocumentUploadService,
    UploadAuthorizationError,
    UploadRequest,
    UploadValidationError,
)
from ruvie.services.documents.status import DocumentStatusService
from ruvie.services.retrieval import AuthorizedRetrievalService


router = APIRouter(prefix="/documents", tags=["documents"])
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MiB


@router.post("/upload", status_code=202)
async def upload_document(
    request: Request,
    project_id: str = Form(..., max_length=36),
    title: str = Form(..., max_length=500),
    software: str = Form(..., max_length=255),
    software_version: str = Form(..., max_length=255),
    file: UploadFile = File(...),
    user_id: str = Depends(get_authenticated_user_id),
    session: Session = Depends(get_session),
    blob_store: BlobStore = Depends(get_blob_store),
    settings: Settings = Depends(get_settings),
) -> dict[str, str | None]:
    check_origin(request, settings)
    verify_csrf(request, user_id, session)
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="file too large")
    try:
        mime_type = _detect_mime_type(content)
        filename = Path((file.filename or "").replace("\\", "/")).name
        if len(filename) > 255:
            raise UploadValidationError("filename is too long")
        result = DocumentUploadService(session, blob_store, settings.embedding_profile).create_revision(
            UploadRequest(user_id, project_id, title, filename, content, mime_type, software, software_version)
        )
    except UploadAuthorizationError as error:
        raise HTTPException(status_code=404, detail="project not found") from error
    except UploadValidationError as error:
        raise HTTPException(status_code=422, detail="upload rejected") from error
    return {
        "document_id": result.document_id,
        "revision_id": result.revision_id,
        "job_id": result.job_id,
        "status": "pending",
    }


def _detect_mime_type(content: bytes) -> str:
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise UploadValidationError("file must be PDF or UTF-8 text") from error
    if not text or any((ord(char) < 32 and char not in "\t\n\r") or 127 <= ord(char) <= 159 for char in text):
        raise UploadValidationError("file must be PDF or UTF-8 text")
    return "text/plain"


@router.get("/revisions/{revision_id}/status")
def get_revision_status(
    revision_id: str,
    user_id: str = Depends(get_authenticated_user_id),
    session: Session = Depends(get_session),
) -> dict[str, str | None]:
    result = DocumentStatusService(session).get_revision_status(user_id, revision_id)
    if result is None:
        raise HTTPException(status_code=404, detail="revision not found")
    return {"revision_id": result.revision_id, "status": result.status, "error_code": result.error_code}


@router.post("/retrieve")
def retrieve_chunks(body: RetrievalBody, user_id: str = Depends(get_authenticated_user_id), session: Session = Depends(get_session), embedder: QueryEmbedder = Depends(get_query_embedder)) -> list[dict[str, object]]:
    if not body.query.strip():
        raise HTTPException(status_code=422, detail="query is required")
    hits = AuthorizedRetrievalService(session).retrieve(
        user_id, embedder.embed_query(body.query), limit=body.limit
    )
    return [
        {"chunk_id": hit.chunk_id, "document_id": hit.document_id, "text": hit.text,
         "citation": hit.citation.to_dict()}
        for hit in hits
    ]
