"""PostgreSQL embedding CAS, migration isolation and fresh process resolution."""
import os
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from ruvie import models
from ruvie.contracts.embedding import EmbeddingConnectionRequest
from ruvie.services.embedding import EmbeddingConnectionService
from ruvie.services.llm import LlmConfigurationConflict
import test_f005_007_e2e as fixtures


class EmbeddingPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.F005007EndToEndTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.F005007EndToEndTests.tearDownClass()

    def setUp(self):
        self.fixture=fixtures.F005007EndToEndTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.factory=self.fixture.client.app.state.session_factory
        with self.factory() as db:
            db.get(models.User,'alpha').system_role='admin'
            db.get(models.User,'beta').system_role='admin'
            db.commit()

    def test_concurrent_apply_has_one_winner_and_atomic_audit(self):
        barrier=Barrier(2)
        def probe(_adapter,_query):
            barrier.wait(timeout=10)
            return [0.1]*1024
        def apply(actor):
            with self.factory() as db:
                try:
                    return EmbeddingConnectionService(db,self.fixture.settings).apply_organization(actor,
                        EmbeddingConnectionRequest(network={'mode':'direct','proxy_url':None}, base_url=self.fixture.settings.embedding_provider.base_url,
                            key_action='clear',expected_version=1,model_id='baai/bge-m3')).version
                except LlmConfigurationConflict:
                    return 'conflict'
        with patch('ruvie.adapters.embedding.OpenAICompatibleQueryEmbedder.embed_query',probe):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(apply,('alpha','beta')))
        self.assertCountEqual(results,[2,'conflict'])
        with self.factory() as db:
            self.assertEqual(db.get(models.OrganizationEmbeddingSettings,1).version,2)
            self.assertEqual(len(list(db.scalars(select(models.AuditEvent).where(
                models.AuditEvent.action=='embedding.organization_settings.update')))),1)

    def test_upgrade_downgrade_preserves_reply_and_documents(self):
        csrf,_=self.fixture._login('alpha@example.test')
        uploaded=self.fixture._upload(csrf,'project-alpha','Existing guide',b'Existing private content')
        self.assertEqual(uploaded.status_code,202,uploaded.text)
        self.fixture._run_worker_once()
        config=Config(str(fixtures.BACKEND/'alembic.ini'))
        with self.factory() as db:
            before=db.get(models.OrganizationLlmSettings,1).allowed_model_ids
            revisions=list(db.execute(text('SELECT id,content_hash,embedding_model_id,embedding_dimension,embedding_distance_metric FROM document_revisions')))
            chunks=list(db.execute(text('SELECT id,content_hash,embedding FROM document_chunks')))
            self.assertTrue(chunks)
        with patch.dict(os.environ,{'DATABASE_URL':self.fixture.database_url}):
            command.downgrade(config,'0012_organization_llm_settings')
            command.upgrade(config,'head')
        with self.factory() as db:
            row=db.get(models.OrganizationEmbeddingSettings,1)
            self.assertEqual((row.version,row.base_url,row.api_key_ciphertext,row.model_id),(0,None,None,None))
            self.assertEqual(db.get(models.OrganizationLlmSettings,1).allowed_model_ids,before)
            self.assertEqual(list(db.execute(text('SELECT id,content_hash,embedding_model_id,embedding_dimension,embedding_distance_metric FROM document_revisions'))),revisions)
            self.assertEqual(list(db.execute(text('SELECT id,content_hash,embedding FROM document_chunks'))),chunks)

    def test_two_processes_read_new_connection_without_restart(self):
        # The child keeps running through an admin commit and reads settings again.
        script='''
import sys
from ruvie.config import Settings,EmbeddingProfile
from ruvie.database import create_database_engine,create_session_factory
from ruvie.services.embedding import EmbeddingConnectionService
settings=Settings(sys.argv[1],EmbeddingProfile('baai/bge-m3',1024,'cosine'),None,None,
                  llm_settings_encryption_key=sys.stdin.readline().strip())
engine=create_database_engine(settings.database_url)
factory=create_session_factory(engine)
with factory() as db:
 old=EmbeddingConnectionService(db,settings).resolve_embedder()
 print(old.provider.api_key=='e2e-embedding-key',flush=True)
sys.stdin.readline()
with factory() as db:
 new=EmbeddingConnectionService(db,settings).resolve_embedder()
 print(str(new.provider.api_key=='')+'|'+str(old.provider.api_key=='e2e-embedding-key'),flush=True)
engine.dispose()
'''
        process=subprocess.Popen([sys.executable,'-B','-c',script,self.fixture.database_url],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            process.stdin.write(self.fixture.settings.llm_settings_encryption_key+'\n');process.stdin.flush()
            self.assertEqual(process.stdout.readline().strip(),'True')
            with self.factory() as db:
                EmbeddingConnectionService(db,self.fixture.settings).apply_organization('alpha',
                    EmbeddingConnectionRequest(network={'mode':'direct','proxy_url':None}, base_url=self.fixture.settings.embedding_provider.base_url,
                        key_action='clear',expected_version=1,model_id='baai/bge-m3'))
            process.stdin.write('continue\n');process.stdin.flush()
            output,error=process.communicate(timeout=15)
            self.assertEqual(process.returncode,0,error)
            self.assertEqual(output.strip(),'True|True')
        finally:
            if process.poll() is None:
                process.kill();process.communicate()
