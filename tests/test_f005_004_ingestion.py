import json
import sys
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ruvie.adapters.embedding import OpenAICompatibleQueryEmbedder
from ruvie.config import EmbeddingProfile, EmbeddingProviderSettings
from ruvie.services.documents.ingestion import DocumentIngestionWorker
from ruvie.services.documents.upload import DocumentUploadService, UploadRequest
from ruvie.adapters.blob_storage import LocalBlobStore
from ruvie.models import (
    Base, DocumentChunk, DocumentRevision, IngestionJob, IngestionJobState,
    Membership, Project, RevisionIngestionState, Role, RoleCode, User,
)
from ruvie.worker_cli import run_worker_loop


class SequenceEmbedder:
    def __init__(self, failures=0):
        self.failures = failures
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        if self.calls <= self.failures:
            raise httpx.ConnectError("provider secret")
        return [[float(len(text))] + [0.0] * 1023 for text in texts]


class F005004IngestionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        event.listen(self.engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
        Base.metadata.create_all(self.engine)
        self.profile = EmbeddingProfile("BAAI/bge-m3", 1024, "cosine")
        with Session(self.engine) as db:
            db.add_all((
                User(id="user-1", email="member@example.test", display_name="Member"),
                Role(id="role-1", code=RoleCode.BIM_CAD_SPECIALIST),
                Project(id="project-1", code="alpha", name="Alpha"),
            ))
            db.commit()
            db.add(Membership(id="membership-1", user_id="user-1", project_id="project-1", role_id="role-1"))
            db.commit()
        self.directory = TemporaryDirectory()
        self.blobs = LocalBlobStore(Path(self.directory.name))

    def tearDown(self):
        self.directory.cleanup()
        self.engine.dispose()

    def upload(self, content=b"abcdefghijk", *, filename="alpha.txt", mime_type="text/plain"):
        with Session(self.engine) as db:
            return DocumentUploadService(db, self.blobs, self.profile).create_revision(
                UploadRequest("user-1", "project-1", "Alpha doc", filename, content,
                              mime_type, "Revit", "2026")
            )

    def worker(self, embedder):
        return DocumentIngestionWorker(Session(self.engine), self.blobs, embedder, self.profile, chunk_size=8, chunk_overlap=2)

    def age_job(self, job_id, seconds):
        with Session(self.engine) as db:
            job = db.get(IngestionJob, job_id)
            job.updated_at = datetime.now(timezone.utc) - timedelta(seconds=seconds)
            db.commit()

    def test_temporary_provider_failure_retries_after_backoff_and_creates_no_duplicate_ordinals(self):
        uploaded = self.upload()
        embedder = SequenceEmbedder(failures=1)
        worker = self.worker(embedder)
        self.assertEqual(worker.run_next(), uploaded.job_id)
        with Session(self.engine) as db:
            job = db.get(IngestionJob, uploaded.job_id)
            self.assertEqual((job.state, job.attempt_count), (IngestionJobState.PENDING, 1))
            self.assertEqual(job.error_code, "provider_unavailable")
        self.assertIsNone(worker.run_next(), "first retry must wait for its backoff")

        self.age_job(uploaded.job_id, 6)
        self.assertEqual(worker.run_next(), uploaded.job_id)
        with Session(self.engine) as db:
            job = db.get(IngestionJob, uploaded.job_id)
            revision = db.get(DocumentRevision, uploaded.revision_id)
            chunks = db.scalars(select(DocumentChunk).where(DocumentChunk.document_revision_id == uploaded.revision_id)).all()
            self.assertEqual((job.state, job.attempt_count), (IngestionJobState.COMPLETED, 2))
            self.assertEqual(revision.ingestion_state, RevisionIngestionState.READY)
            self.assertEqual([chunk.ordinal for chunk in chunks], [0, 1])

    def test_provider_failure_stops_after_three_total_attempts(self):
        uploaded = self.upload()
        worker = self.worker(SequenceEmbedder(failures=99))
        for attempt, wait_seconds in ((1, 6), (2, 31)):
            self.assertEqual(worker.run_next(), uploaded.job_id)
            with Session(self.engine) as db:
                self.assertEqual(db.get(IngestionJob, uploaded.job_id).state, IngestionJobState.PENDING)
            self.age_job(uploaded.job_id, wait_seconds)
        self.assertEqual(worker.run_next(), uploaded.job_id)
        self.assertIsNone(worker.run_next())
        with Session(self.engine) as db:
            job = db.get(IngestionJob, uploaded.job_id)
            revision = db.get(DocumentRevision, uploaded.revision_id)
            self.assertEqual((job.state, job.attempt_count), (IngestionJobState.FAILED, 3))
            self.assertEqual(revision.ingestion_state, RevisionIngestionState.FAILED)

    def test_stale_running_job_is_recovered_and_retry_backoff_is_applied(self):
        uploaded = self.upload()
        with Session(self.engine) as db:
            job = db.get(IngestionJob, uploaded.job_id)
            revision = db.get(DocumentRevision, uploaded.revision_id)
            job.state = IngestionJobState.RUNNING
            job.attempt_count = 1
            job.updated_at = datetime.now(timezone.utc) - timedelta(minutes=6)
            db.commit()
        worker = self.worker(SequenceEmbedder())
        self.assertIsNone(worker.run_next())
        with Session(self.engine) as db:
            job = db.get(IngestionJob, uploaded.job_id)
            self.assertEqual((job.state, job.attempt_count), (IngestionJobState.PENDING, 1))
            self.assertEqual(job.error_code, "worker_interrupted")
        self.age_job(uploaded.job_id, 6)
        self.assertEqual(worker.run_next(), uploaded.job_id)

    def test_stale_job_at_attempt_limit_is_failed_and_partial_chunks_are_removed(self):
        uploaded = self.upload()
        with Session(self.engine) as db:
            job = db.get(IngestionJob, uploaded.job_id)
            revision = db.get(DocumentRevision, uploaded.revision_id)
            job.state = IngestionJobState.RUNNING
            job.attempt_count = 3
            job.updated_at = datetime.now(timezone.utc) - timedelta(minutes=6)
            db.add(DocumentChunk(
                id="partial", document_revision_id=uploaded.revision_id,
                document_id=revision.document_id, project_id="project-1", ordinal=0,
                text="partial", content_hash="a" * 64, start_offset=0, end_offset=7,
                software="Revit", software_version="2026", embedding=[0.0] * 1024,
            ))
            db.commit()
        self.assertIsNone(self.worker(SequenceEmbedder()).run_next())
        with Session(self.engine) as db:
            self.assertEqual(db.get(IngestionJob, uploaded.job_id).state, IngestionJobState.FAILED)
            self.assertEqual(db.get(DocumentRevision, uploaded.revision_id).ingestion_state, RevisionIngestionState.FAILED)
            self.assertEqual(db.scalars(select(DocumentChunk).where(DocumentChunk.document_revision_id == uploaded.revision_id)).all(), [])

    def test_retry_removes_committed_partial_batch_before_reembedding(self):
        uploaded = self.upload(b"x" * 65)

        class FailsSecondBatch:
            calls = 0

            def embed(self, texts):
                self.calls += 1
                if self.calls == 2:
                    raise httpx.ConnectError("provider secret")
                return [[1.0] * 1024 for _ in texts]

        embedder = FailsSecondBatch()
        worker = DocumentIngestionWorker(Session(self.engine), self.blobs, embedder, self.profile, chunk_size=1, chunk_overlap=0)
        worker.run_next()
        with Session(self.engine) as db:
            self.assertEqual(db.scalars(select(DocumentChunk).where(DocumentChunk.document_revision_id == uploaded.revision_id)).all(), [])
        self.age_job(uploaded.job_id, 6)
        worker.run_next()
        with Session(self.engine) as db:
            chunks = db.scalars(select(DocumentChunk).where(DocumentChunk.document_revision_id == uploaded.revision_id).order_by(DocumentChunk.ordinal)).all()
            self.assertEqual([chunk.ordinal for chunk in chunks], list(range(65)))

    def test_empty_extracted_text_fails_without_calling_provider(self):
        uploaded = self.upload(b"   \n  ")
        embedder = SequenceEmbedder()
        self.worker(embedder).run_next()
        with Session(self.engine) as db:
            job = db.get(IngestionJob, uploaded.job_id)
            revision = db.get(DocumentRevision, uploaded.revision_id)
            self.assertEqual(job.state, IngestionJobState.FAILED)
            self.assertEqual(job.error_code, "empty_content")
            self.assertEqual(revision.ingestion_state, RevisionIngestionState.FAILED)
        self.assertEqual(embedder.calls, 0)

    def test_non_finite_vector_is_rejected_before_chunk_commit(self):
        uploaded = self.upload()

        class NonFiniteEmbedder:
            def embed(self, texts):
                return [[float("nan")] + [0.0] * 1023 for _ in texts]

        self.worker(NonFiniteEmbedder()).run_next()
        with Session(self.engine) as db:
            self.assertEqual(db.get(IngestionJob, uploaded.job_id).error_code, "invalid_embedding_response")
            self.assertEqual(db.get(DocumentRevision, uploaded.revision_id).ingestion_state, RevisionIngestionState.FAILED)
            self.assertEqual(db.scalars(select(DocumentChunk).where(DocumentChunk.document_revision_id == uploaded.revision_id)).all(), [])

    def test_non_utf8_text_is_terminal_and_does_not_call_provider(self):
        uploaded = self.upload(b"\xff\xfe")
        embedder = SequenceEmbedder()
        self.worker(embedder).run_next()
        with Session(self.engine) as db:
            self.assertEqual(db.get(IngestionJob, uploaded.job_id).error_code, "invalid_document")
            self.assertEqual(db.get(DocumentRevision, uploaded.revision_id).ingestion_state, RevisionIngestionState.FAILED)
        self.assertEqual(embedder.calls, 0)

    def test_unreadable_pdf_fails_without_calling_provider(self):
        uploaded = self.upload(b"%PDF-1.4\n", filename="broken.pdf", mime_type="application/pdf")
        embedder = SequenceEmbedder()
        with self.assertLogs("pypdf", level="WARNING"):
            self.worker(embedder).run_next()
        with Session(self.engine) as db:
            self.assertEqual(db.get(IngestionJob, uploaded.job_id).error_code, "invalid_document")
            self.assertEqual(db.get(DocumentRevision, uploaded.revision_id).ingestion_state, RevisionIngestionState.FAILED)
        self.assertEqual(embedder.calls, 0)

    def test_provider_auth_rejection_is_terminal(self):
        uploaded = self.upload()

        class UnauthorizedEmbedder:
            def embed(self, texts):
                request = httpx.Request("POST", "https://embedding.example.test/v1/embeddings")
                response = httpx.Response(401, request=request)
                raise httpx.HTTPStatusError("provider secret", request=request, response=response)

        self.worker(UnauthorizedEmbedder()).run_next()
        with Session(self.engine) as db:
            job = db.get(IngestionJob, uploaded.job_id)
            self.assertEqual((job.state, job.attempt_count), (IngestionJobState.FAILED, 1))
            self.assertEqual(job.error_code, "provider_rejected")

    def test_embedding_adapter_restores_provider_index_order_for_multiple_inputs(self):
        expected = [[0.0] * 1024, [1.0] * 1024]

        def handler(request):
            self.assertEqual(json.loads(request.content), {"input": ["first", "second"], "model": "BAAI/bge-m3"})
            return httpx.Response(200, json={"data": [
                {"index": 1, "embedding": expected[1]},
                {"index": 0, "embedding": expected[0]},
            ]})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        adapter = OpenAICompatibleQueryEmbedder(
            EmbeddingProviderSettings("https://embedding.example.test/v1", "server-key"), self.profile, client
        )
        self.assertEqual(adapter.embed(["first", "second"]), expected)
        client.close()

    def test_embedding_adapter_returns_empty_result_without_provider_request(self):
        adapter = OpenAICompatibleQueryEmbedder(
            EmbeddingProviderSettings("https://embedding.example.test/v1", "server-key"), self.profile,
            httpx.Client(transport=httpx.MockTransport(lambda _: self.fail("unexpected provider request"))),
        )
        self.assertEqual(adapter.embed([]), [])

    def test_local_blob_store_refuses_uri_outside_private_root(self):
        outside = Path(self.directory.name).parent / "outside-private-blob.txt"
        outside.write_text("private", encoding="utf-8")
        try:
            with self.assertRaises(PermissionError):
                self.blobs.get(outside.as_uri())
        finally:
            outside.unlink(missing_ok=True)

    def test_worker_loop_polls_again_after_a_job_and_stops_on_signal(self):
        stop = threading.Event()
        calls = []

        def run_once():
            calls.append(True)
            if len(calls) == 2:
                stop.set()
                return "job-1"
            return "job-0"

        run_worker_loop(run_once, stop, poll_interval=0)
        self.assertEqual(len(calls), 2)

    def test_worker_heartbeats_running_job_during_long_provider_call(self):
        uploaded = self.upload()

        class SlowEmbedder:
            def embed(inner_self, texts):
                with Session(self.engine) as db:
                    claimed_at = db.get(IngestionJob, uploaded.job_id).updated_at
                time.sleep(0.06)
                with Session(self.engine) as db:
                    heartbeat_at = db.get(IngestionJob, uploaded.job_id).updated_at
                self.assertGreater(heartbeat_at, claimed_at)
                return [[1.0] * 1024 for _ in texts]

        factory = lambda: Session(self.engine)
        with patch("ruvie.services.documents.ingestion.HEARTBEAT_INTERVAL", 0.01):
            worker = DocumentIngestionWorker(
                Session(self.engine), self.blobs, SlowEmbedder(), self.profile,
                session_factory=factory,
            )
            worker.run_next()


if __name__ == "__main__":
    unittest.main()
