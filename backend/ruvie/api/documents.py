import base64

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ruvie.adapters.embedding import QueryEmbedder
from ruvie.config import Settings
from ruvie.contracts.documents import RetrievalBody, UploadBody
from ruvie.dependencies import get_authenticated_user_id, get_blob_store, get_query_embedder, get_session, get_settings
from ruvie.document_upload import BlobStore, DocumentUploadService, UploadRequest
from ruvie.services.retrieval import AuthorizedRetrievalService


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload")
def upload_document(body: UploadBody, user_id: str = Depends(get_authenticated_user_id), session: Session = Depends(get_session), blob_store: BlobStore = Depends(get_blob_store), settings: Settings = Depends(get_settings)) -> dict[str, str]:
    try:
        content = base64.b64decode(body.content_base64, validate=True)
        result = DocumentUploadService(session, blob_store, settings.embedding_profile).create_revision(UploadRequest(user_id, body.project_id, body.title, body.filename, content, body.mime_type, body.software, body.software_version, body.allowed_role_codes))
        return {"document_id": result.document_id, "revision_id": result.revision_id, "job_id": result.job_id}
    except (ValueError, PermissionError) as error:
        raise HTTPException(status_code=403 if isinstance(error, PermissionError) else 422, detail="upload rejected") from error


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
