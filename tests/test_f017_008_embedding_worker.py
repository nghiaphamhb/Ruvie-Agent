"""A claimed ingestion job retains its resolved adapter across every batch."""
import unittest
from unittest.mock import patch
from sqlalchemy import select
from sqlalchemy.orm import Session
from ruvie.models import DocumentChunk, DocumentRevision, IngestionJob, IngestionJobState, RevisionIngestionState
from ruvie.services.documents.ingestion import DocumentIngestionWorker
from ruvie.services.embedding import EmbeddingUnavailableError
import test_f005_004_ingestion as fixtures


class EmbeddingWorkerSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.F005004IngestionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def test_each_job_resolves_once_and_retains_snapshot_for_all_batches(self):
        first=self.fixture.upload(b'first document has several chunks')
        second=self.fixture.upload(b'second document has several chunks')
        connection={'version':1,'resolutions':0}
        class Snapshot:
            def __init__(self,version):
                self.version=version
            def embed(self,texts):
                connection['version']=2
                return [[float(self.version)]+[0.0]*1023 for _ in texts]
        def resolve():
            connection['resolutions']+=1
            return Snapshot(connection['version'])
        with Session(self.fixture.engine) as db:
            worker=DocumentIngestionWorker(db,self.fixture.blobs,None,self.fixture.profile,
                chunk_size=8,chunk_overlap=2,embedder_resolver=resolve)
            with patch('ruvie.services.documents.ingestion.EMBED_BATCH_SIZE',1):
                self.assertEqual(worker.run_next(),first.job_id)
                self.assertEqual(worker.run_next(),second.job_id)
                self.assertIsNone(worker.run_next())
        self.assertEqual(connection['resolutions'],2)
        with Session(self.fixture.engine) as db:
            for upload,want in ((first,1.0),(second,2.0)):
                vectors=list(db.scalars(select(DocumentChunk.embedding).where(DocumentChunk.document_revision_id==upload.revision_id)))
                self.assertGreater(len(vectors),1)
                self.assertTrue(all(vector[0]==want for vector in vectors))
                self.assertEqual(db.get(DocumentRevision,upload.revision_id).ingestion_state,RevisionIngestionState.READY)

    def test_missing_configuration_fails_claimed_job_without_ready_vectors(self):
        upload=self.fixture.upload()
        def resolve():
            raise EmbeddingUnavailableError('embedding_not_configured')
        with Session(self.fixture.engine) as db:
            worker=DocumentIngestionWorker(db,self.fixture.blobs,None,self.fixture.profile,embedder_resolver=resolve)
            self.assertEqual(worker.run_next(),upload.job_id)
            self.assertIsNone(worker.run_next())
        with Session(self.fixture.engine) as db:
            self.assertEqual(db.get(IngestionJob,upload.job_id).state,IngestionJobState.FAILED)
            self.assertEqual(db.get(DocumentRevision,upload.revision_id).ingestion_state,RevisionIngestionState.FAILED)
            self.assertEqual(list(db.scalars(select(DocumentChunk))),[])
