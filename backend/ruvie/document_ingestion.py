from hashlib import sha256
from io import BytesIO
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ruvie.config import EmbeddingProfile
from ruvie.document_upload import BlobStore
from ruvie.domain import DocumentChunk, DocumentRevision, IngestionJob, IngestionJobState, RevisionIngestionState


class EmbeddingAdapter(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class TextExtractor:
    def extract(self, content: bytes, mime_type: str) -> str:
        if mime_type.startswith("text/"):
            return content.decode("utf-8", errors="replace")
        if mime_type == "application/pdf":
            from pypdf import PdfReader

            return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
        raise ValueError("unsupported document MIME type")


class DocumentIngestionWorker:
    def __init__(self, session: Session, blob_store: BlobStore, embedder: EmbeddingAdapter, profile: EmbeddingProfile, *, chunk_size: int = 800, chunk_overlap: int = 120) -> None:
        if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
            raise ValueError("chunk overlap must be non-negative and smaller than chunk size")
        self.session, self.blob_store, self.embedder, self.profile = session, blob_store, embedder, profile
        self.chunk_size, self.chunk_overlap, self.extractor = chunk_size, chunk_overlap, TextExtractor()

    def run_next(self) -> str | None:
        job = self.session.scalar(select(IngestionJob).where(IngestionJob.state == IngestionJobState.PENDING).order_by(IngestionJob.created_at).with_for_update(skip_locked=True).limit(1))
        if job is None:
            return None
        job.state, job.attempt_count = IngestionJobState.RUNNING, job.attempt_count + 1
        self.session.commit()
        try:
            self._ingest(job.id)
        except Exception as error:
            self._fail(job.id, error)
        return job.id

    def _ingest(self, job_id: str) -> None:
        job = self.session.get(IngestionJob, job_id)
        revision = self.session.get(DocumentRevision, job.document_revision_id)
        if (revision.embedding_model_id, revision.embedding_model_version, revision.embedding_dimension, revision.embedding_distance_metric) != (self.profile.model_id, self.profile.model_version, self.profile.dimension, self.profile.distance_metric):
            raise ValueError("revision embedding profile does not match worker profile")
        text = TextExtractor().extract(self.blob_store.get(revision.blob_uri), revision.mime_type)
        pieces = self._chunks(text)
        vectors = self.embedder.embed([piece[0] for piece in pieces])
        if len(vectors) != len(pieces) or any(len(vector) != self.profile.dimension for vector in vectors):
            raise ValueError("embedder returned vectors with the wrong dimension")
        for ordinal, ((chunk_text, start, end), vector) in enumerate(zip(pieces, vectors, strict=True)):
            self.session.add(DocumentChunk(id=str(uuid4()), document_revision_id=revision.id, document_id=revision.document_id, project_id=revision.project_id, ordinal=ordinal, text=chunk_text, content_hash=sha256(chunk_text.encode()).hexdigest(), start_offset=start, end_offset=end, software=revision.software, software_version=revision.software_version, embedding=vector))
        revision.ingestion_state, job.state = RevisionIngestionState.READY, IngestionJobState.COMPLETED
        self.session.commit()

    def _fail(self, job_id: str, error: Exception) -> None:
        self.session.rollback()
        job = self.session.get(IngestionJob, job_id)
        revision = self.session.get(DocumentRevision, job.document_revision_id)
        job.state, job.error_code, revision.ingestion_state = IngestionJobState.FAILED, type(error).__name__, RevisionIngestionState.FAILED
        self.session.commit()

    def _chunks(self, text: str) -> list[tuple[str, int, int]]:
        chunks, start = [], 0
        while start < len(text):
            end, chunk = min(start + self.chunk_size, len(text)), text[start : min(start + self.chunk_size, len(text))]
            if chunk.strip():
                left, right = len(chunk) - len(chunk.lstrip()), len(chunk.rstrip())
                chunks.append((chunk[left:right], start + left, start + right))
            if end == len(text):
                break
            start = end - self.chunk_overlap
        return chunks
