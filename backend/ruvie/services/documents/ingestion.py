from hashlib import sha256
from io import BytesIO
import logging
from datetime import datetime, timedelta, timezone
import math
import threading
from collections.abc import Callable
from typing import Protocol
from uuid import uuid4

import httpx
from ruvie.adapters.network import ProxyUnavailableError, NetworkConfigurationPendingError
from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from ruvie.config import EmbeddingProfile
from ruvie.models import DocumentChunk, DocumentRevision, IngestionJob, IngestionJobState, RevisionIngestionState
from ruvie.services.documents.upload import BlobStore


class EmbeddingAdapter(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


logger = logging.getLogger(__name__)
# Total attempts include the first run; retries stop after this limit.
MAX_ATTEMPTS = 3
EMBED_BATCH_SIZE = 64  # Text chunks per embedding request, not ingestion jobs.
# Wait times after failed attempts; running jobs refresh updated_at as a heartbeat.
RETRY_DELAYS = {1: timedelta(seconds=5), 2: timedelta(seconds=30)}
# A running job without a heartbeat for this long is considered interrupted.
STALE_AFTER = timedelta(minutes=5)
HEARTBEAT_INTERVAL = 60.0


class _IngestionFailure(Exception):
    def __init__(self, code: str, *, retryable: bool = False):
        self.code, self.retryable = code, retryable
        super().__init__(code)


class TextExtractor:
    def extract(self, content: bytes, mime_type: str) -> str:
        """Convert UTF-8 text or PDF bytes into text; unsupported MIME types fail."""
        if mime_type.startswith("text/"):
            return content.decode("utf-8")
        if mime_type == "application/pdf":
            from pypdf import PdfReader

            return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
        raise ValueError("unsupported document MIME type")


class DocumentIngestionWorker:
    """Process private revision blobs into chunks/vectors; expose fully ready revisions only."""

    def __init__(
        self,
        session: Session,
        blob_store: BlobStore,
        embedder: EmbeddingAdapter,
        profile: EmbeddingProfile,
        *,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        session_factory: Callable[[], Session] | None = None,
        embedder_resolver: Callable[[], EmbeddingAdapter] | None = None,
    ) -> None:
        if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
            raise ValueError("chunk overlap must be non-negative and smaller than chunk size")
        self.session, self.blob_store, self.embedder, self.profile = session, blob_store, embedder, profile
        self.session_factory = session_factory
        self.embedder_resolver = embedder_resolver
        self.chunk_size, self.chunk_overlap, self.extractor = chunk_size, chunk_overlap, TextExtractor()

    def run_next(self) -> str | None:
        """Claim one eligible job, run it, handle failure, and return its ID or None."""
        self._recover_stale_jobs()
        now = datetime.now(timezone.utc)
        # Pending retries become claimable only after their delay has elapsed.
        eligible = or_(
            IngestionJob.attempt_count == 0,
            (IngestionJob.attempt_count == 1) & (IngestionJob.updated_at <= now - RETRY_DELAYS[1]),
            (IngestionJob.attempt_count == 2) & (IngestionJob.updated_at <= now - RETRY_DELAYS[2]),
        )
        job = self.session.scalar(
            select(IngestionJob)
            .where(IngestionJob.state == IngestionJobState.PENDING, eligible)
            .order_by(IngestionJob.created_at)
            # PostgreSQL skips jobs another worker has already locked.
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        job_id = job.id
        job.state, job.attempt_count = IngestionJobState.RUNNING, job.attempt_count + 1
        job.error_code = None
        self.session.commit()
        try:
            if self.embedder_resolver is not None:
                # Resolve only after claim and retain this adapter through every batch.
                self.embedder = self.embedder_resolver()
            self._run_with_heartbeat(job_id)
        except Exception as error:
            self._fail(job_id, error)
        return job_id

    def _run_with_heartbeat(self, job_id: str) -> None:
        """Keep the job alive using separate DB sessions during slow provider calls."""
        if self.session_factory is None:
            self._ingest(job_id)
            return
        stopped = threading.Event()

        def heartbeat() -> None:
            while not stopped.wait(HEARTBEAT_INTERVAL):
                try:
                    with self.session_factory() as session:
                        result = session.execute(
                            update(IngestionJob)
                            .where(IngestionJob.id == job_id, IngestionJob.state == IngestionJobState.RUNNING)
                            .values(updated_at=datetime.now(timezone.utc))
                        )
                        session.commit()
                        if result.rowcount == 0:
                            return
                except Exception as error:
                    logger.warning("ingestion heartbeat failed (%s)", type(error).__name__)

        thread = threading.Thread(target=heartbeat, name=f"ingestion-heartbeat-{job_id}", daemon=True)
        thread.start()
        try:
            self._ingest(job_id)
        finally:
            stopped.set()
            thread.join()

    def _recover_stale_jobs(self) -> None:
        """Remove partial chunks from interrupted jobs; retry or mark them failed."""
        stale = self.session.scalars(
            select(IngestionJob)
            .where(
                IngestionJob.state == IngestionJobState.RUNNING,
                IngestionJob.updated_at <= datetime.now(timezone.utc) - STALE_AFTER,
            )
            # PostgreSQL skips jobs another worker has already locked.
            .with_for_update(skip_locked=True)
        ).all()
        for job in stale:
            revision = self.session.get(DocumentRevision, job.document_revision_id)
            self.session.execute(delete(DocumentChunk).where(DocumentChunk.document_revision_id == revision.id))
            if job.attempt_count >= MAX_ATTEMPTS:
                job.state, job.error_code = IngestionJobState.FAILED, "worker_interrupted"
                revision.ingestion_state = RevisionIngestionState.FAILED
            else:
                job.state, job.error_code = IngestionJobState.PENDING, "worker_interrupted"
                revision.ingestion_state = RevisionIngestionState.PENDING
        if stale:
            self.session.commit()

    def _ingest(self, job_id: str) -> None:
        """Read a private blob, extract/chunk/embed, then mark ready after all batches succeed."""
        job = self.session.get(IngestionJob, job_id)
        revision = self.session.get(DocumentRevision, job.document_revision_id)
        if (revision.embedding_model_id, revision.embedding_dimension, revision.embedding_distance_metric) != (self.profile.model_id, self.profile.dimension, self.profile.distance_metric):
            raise _IngestionFailure("embedding_profile_mismatch")
        revision_id, document_id, project_id = revision.id, revision.document_id, revision.project_id
        mime_type, blob_uri = revision.mime_type, revision.blob_uri
        software, software_version = revision.software, revision.software_version
        self.session.commit()
        try:
            content = self.blob_store.get(blob_uri)
        except (FileNotFoundError, PermissionError) as error:
            raise _IngestionFailure("blob_unavailable") from error
        except OSError as error:
            raise _IngestionFailure("blob_unavailable", retryable=True) from error
        if not (mime_type.startswith("text/") or mime_type == "application/pdf"):
            raise _IngestionFailure("unsupported_mime_type")
        try:
            text = self.extractor.extract(content, mime_type)
        except Exception as error:
            raise _IngestionFailure("invalid_document") from error
        pieces = self._chunks(text)
        if not pieces:
            raise _IngestionFailure("empty_content")
        self.session.execute(delete(DocumentChunk).where(DocumentChunk.document_revision_id == revision_id))
        self.session.commit()

        # Partial batches remain hidden because retrieval accepts only READY revisions.
        for batch_start in range(0, len(pieces), EMBED_BATCH_SIZE):
            batch = pieces[batch_start : batch_start + EMBED_BATCH_SIZE]
            try:
                vectors = self.embedder.embed([piece[0] for piece in batch])
            except httpx.HTTPStatusError as error:
                status = error.response.status_code
                retryable = status == 429 or status >= 500
                raise _IngestionFailure("provider_unavailable" if retryable else "provider_rejected", retryable=retryable) from error
            except httpx.RequestError as error:
                raise _IngestionFailure("provider_unavailable", retryable=True) from error
            except ValueError as error:
                raise _IngestionFailure("invalid_embedding_response") from error
            except Exception as error:
                raise _IngestionFailure("provider_unavailable", retryable=True) from error
            if len(vectors) != len(batch):
                raise _IngestionFailure("invalid_embedding_response")
            normalized: list[list[float]] = []
            try:
                for vector in vectors:
                    if len(vector) != self.profile.dimension:
                        raise ValueError
                    values = [float(value) for value in vector]
                    if any(not math.isfinite(value) for value in values):
                        raise ValueError
                    normalized.append(values)
            except (TypeError, ValueError) as error:
                raise _IngestionFailure("invalid_embedding_response") from error

            for offset, ((chunk_text, start, end), vector) in enumerate(zip(batch, normalized, strict=True)):
                self.session.add(DocumentChunk(
                    id=str(uuid4()), document_revision_id=revision_id,
                    document_id=document_id, project_id=project_id,
                    ordinal=batch_start + offset, text=chunk_text,
                    content_hash=sha256(chunk_text.encode()).hexdigest(),
                    start_offset=start, end_offset=end, software=software,
                    software_version=software_version, embedding=vector,
                ))
            job = self.session.get(IngestionJob, job_id)
            job.updated_at = datetime.now(timezone.utc)
            self.session.commit()

        job = self.session.get(IngestionJob, job_id)
        revision = self.session.get(DocumentRevision, revision_id)
        revision.ingestion_state, job.state, job.error_code = RevisionIngestionState.READY, IngestionJobState.COMPLETED, None
        job.updated_at = datetime.now(timezone.utc)
        self.session.commit()

    def _fail(self, job_id: str, error: Exception) -> None:
        """Rollback and remove partial chunks; store a safe error code and bounded retry state."""
        self.session.rollback()
        job = self.session.get(IngestionJob, job_id)
        revision = self.session.get(DocumentRevision, job.document_revision_id)
        self.session.execute(delete(DocumentChunk).where(DocumentChunk.document_revision_id == revision.id))  # Remove batches committed before the failure.
        failure = error if isinstance(error, _IngestionFailure) else _IngestionFailure(
            "network_configuration_pending" if isinstance(error, NetworkConfigurationPendingError)
            else "proxy_unavailable" if isinstance(error, ProxyUnavailableError)
            else "database_unavailable" if isinstance(error, OperationalError)
            else "worker_error",
            retryable=isinstance(error, (OperationalError, ProxyUnavailableError)),
        )
        # Retry transient failures only while the total attempt budget remains.
        retry = failure.retryable and job.attempt_count < MAX_ATTEMPTS
        if retry:
            job.state, revision.ingestion_state = IngestionJobState.PENDING, RevisionIngestionState.PENDING
        else:
            job.state, revision.ingestion_state = IngestionJobState.FAILED, RevisionIngestionState.FAILED
        job.error_code = failure.code
        job.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        logger.info("ingestion job %s ended as %s (%s)", job_id, job.state.value, failure.code)

    def _chunks(self, text: str) -> list[tuple[str, int, int]]:
        """Return (text, start, end) chunks with overlap and original character offsets [start, end)."""
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
