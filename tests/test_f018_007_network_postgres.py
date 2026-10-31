"""F018 migration and cutover against disposable PostgreSQL; never the app DB."""
import os
import subprocess
import sys
import unittest
from uuid import uuid4
from unittest.mock import patch
import psycopg
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
import test_f005_007_e2e as fixtures

class MigrationSqlTests(unittest.TestCase):
    def test_alembic_sql(self):
        env={**os.environ,'DATABASE_URL':'postgresql+psycopg://offline:offline@localhost/offline'}
        run=subprocess.run([sys.executable,'-B','-m','alembic','-c','backend/alembic.ini',
            'upgrade','0013_org_embedding_settings:head','--sql'],
            capture_output=True,text=True,env=env)
        self.assertEqual(run.returncode,0,run.stderr)
        for value in ('network_mode','ck_org_llm_network','ck_org_embedding_network'):
            self.assertIn(value,run.stdout)
        self.assertNotIn('LLM_PROXY_URL',run.stdout)


class NetworkPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.F005007EndToEndTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.F005007EndToEndTests.tearDownClass()

    def setUp(self):
        self.database = 'f018_' + uuid4().hex[:12]
        self.admin = psycopg.connect(host='127.0.0.1',
            port=fixtures.F005007EndToEndTests.postgres_port,
            dbname=fixtures.POSTGRES_USER, user=fixtures.POSTGRES_USER,
            password=fixtures.POSTGRES_PASSWORD, autocommit=True)
        self.admin.execute(f'CREATE DATABASE "{self.database}"')
        self.addCleanup(self.admin.close)
        self.addCleanup(lambda: self.admin.execute(f'DROP DATABASE "{self.database}" WITH (FORCE)'))
        self.url = (f'postgresql+psycopg://{fixtures.POSTGRES_USER}:{fixtures.POSTGRES_PASSWORD}'
                    f'@127.0.0.1:{fixtures.F005007EndToEndTests.postgres_port}/{self.database}')
        self.engine = create_engine(self.url)
        self.addCleanup(self.engine.dispose)
        with self.engine.begin() as db:
            db.execute(text('CREATE TABLE alembic_version (version_num VARCHAR(128) PRIMARY KEY)'))

    def upgrade(self, target='head'):
        with patch.dict(os.environ, {'DATABASE_URL': self.url}):
            command.upgrade(Config('backend/alembic.ini'), target)

    def networks(self):
        with self.engine.connect() as db:
            return [tuple(db.execute(text(f'SELECT network_mode, proxy_url FROM {table}')).one())
                    for table in ('organization_llm_settings', 'organization_embedding_settings')]

    def test_fresh_upgrade_initializes_direct_without_configuring_providers(self):
        self.upgrade()
        self.assertEqual(self.networks(), [('direct', None), ('direct', None)])
        with self.engine.connect() as db:
            for table in ('organization_llm_settings', 'organization_embedding_settings'):
                self.assertEqual(tuple(db.execute(text(f'SELECT version, base_url FROM {table}')).one()), (0, None))

    def test_existing_version_zero_stays_pending_and_cutover_is_atomic(self):
        self.upgrade('0013_org_embedding_settings')
        self.upgrade()
        self.assertEqual(self.networks(), [(None, None), (None, None)])
        from sqlalchemy.orm import Session
        from ruvie.models import User, AuditEvent
        from ruvie.contracts.network import NetworkConfig
        from ruvie.network_settings_cli import convert
        from sqlalchemy import select, func
        from ruvie.services.admin import AdminRequired
        direct = NetworkConfig(mode='direct', proxy_url=None)
        proxy = NetworkConfig(mode='proxy', proxy_url='socks5://127.0.0.1:1080')
        with Session(self.engine) as db:
            db.add(User(id='admin', email='admin@test', display_name='Admin', system_role='admin'))
            db.add(User(id='employee', email='employee@test', display_name='Employee'))
            db.commit()
            with self.assertRaises(AdminRequired):
                convert(db, 'employee', 0, 0, proxy, direct)
            with self.assertRaises(ValueError):
                convert(db, 'admin', 0, 1, proxy, direct)
            self.assertEqual(self.networks(), [(None, None), (None, None)])
            with patch('ruvie.network_settings_cli.AuditEventWriter.append', side_effect=[None, RuntimeError('audit failed')]):
                with self.assertRaises(RuntimeError):
                    convert(db, 'admin', 0, 0, proxy, direct)
            self.assertEqual(self.networks(), [(None, None), (None, None)])
            self.assertTrue(convert(db, 'admin', 0, 0, proxy, direct))
            self.assertFalse(convert(db, 'admin', 0, 0, direct, direct))
            self.assertEqual(db.scalar(select(func.count()).select_from(AuditEvent)), 2)
        self.assertEqual(self.networks(), [('proxy', 'socks5://127.0.0.1:1080'), ('direct', None)])

    def test_upgrade_preserves_routes_and_postgres_rejects_invalid_pairs(self):
        self.upgrade('0014_ai_network_connections')
        with self.engine.begin() as db:
            db.execute(text("UPDATE organization_llm_settings SET network_mode='proxy', proxy_url='socks5://127.0.0.1:1080'"))
        self.upgrade()
        self.assertEqual(self.networks(), [('proxy', 'socks5://127.0.0.1:1080'), (None, None)])
        for table in ('organization_llm_settings', 'organization_embedding_settings'):
            for mode, endpoint in ((None, 'socks5://127.0.0.1:1080'),
                                   ('direct', 'socks5://127.0.0.1:1080'), ('proxy', None), ('proxy', ' ')):
                with self.subTest(table=table, mode=mode, endpoint=endpoint):
                    with self.assertRaises(IntegrityError), self.engine.begin() as db:
                        db.execute(text(f'UPDATE {table} SET network_mode=:mode, proxy_url=:endpoint'),
                                   {'mode': mode, 'endpoint': endpoint})

    def test_real_proxy_routes_are_independent_and_operation_snapshots_survive_apply(self):
        from http.server import ThreadingHTTPServer
        import threading
        from sqlalchemy.orm import Session
        from ruvie.config import Settings, EmbeddingProfile
        from ruvie.models import User
        from ruvie.services.llm import LlmConnectionService
        from ruvie.services.embedding import EmbeddingConnectionService
        from ruvie.contracts.llm import OrganizationConnectionUpdateRequest
        from ruvie.contracts.embedding import EmbeddingConnectionRequest
        from test_f018_002_network_transport import local_socks_proxy
        self.upgrade()
        fixtures.FakeProviderHandler.state = fixtures.FakeProviderState()
        provider = ThreadingHTTPServer(('127.0.0.1', 0), fixtures.FakeProviderHandler)
        thread = threading.Thread(target=provider.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(provider.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(provider.shutdown)
        base = f'http://127.0.0.1:{provider.server_port}'
        settings = Settings(self.url, EmbeddingProfile('baai/bge-m3', 1024, 'cosine'), None, None,
                            llm_allowed_local_origins=(base,))
        direct = {'mode': 'direct', 'proxy_url': None}
        with Session(self.engine) as db, local_socks_proxy() as proxy:
            db.add(User(id='admin', email='admin@test', display_name='Admin', system_role='admin'))
            db.commit()
            route = {'mode': 'proxy', 'proxy_url': f'socks5://127.0.0.1:{proxy.server_address[1]}'}
            reply = LlmConnectionService(db, settings)
            embedding = EmbeddingConnectionService(db, settings)
            reply.apply_organization('admin', OrganizationConnectionUpdateRequest(
                base_url=base, key_action='clear', expected_version=0, network=direct,
                allowed_model_ids=['a'], default_model_id='a'))
            embedding.apply_organization('admin', EmbeddingConnectionRequest(
                base_url=base, key_action='clear', expected_version=0, network=route, model_id='baai/bge-m3'))
            old = embedding.resolve_embedder()
            before = len(proxy.destinations)
            reply.list_models('admin')
            self.assertEqual(len(proxy.destinations), before)
            old.embed_query('old operation')
            self.assertEqual(len(proxy.destinations), before + 1)
            # Exercise the worker caller with the same DB route and real SOCKS server.
            from pathlib import Path
            from tempfile import TemporaryDirectory
            from ruvie.adapters.blob_storage import LocalBlobStore
            from ruvie.models import Project, Role, RoleCode, Membership, IngestionJob, IngestionJobState
            from ruvie.services.documents.upload import DocumentUploadService, UploadRequest
            from ruvie.services.documents.ingestion import DocumentIngestionWorker
            with TemporaryDirectory() as directory:
                blobs = LocalBlobStore(Path(directory))
                db.add_all([Project(id='project', code='test', name='Test'),
                            Role(id='role', code=RoleCode.BIM_CAD_SPECIALIST)])
                db.commit()
                db.add(Membership(id='member', user_id='admin', project_id='project', role_id='role'))
                db.commit()
                upload = DocumentUploadService(db, blobs, settings.embedding_profile).create_revision(
                    UploadRequest('admin', 'project', 'Guide', 'guide.txt', b'Guide for worker routing',
                                  'text/plain', 'CAD', '1'))
                worker = DocumentIngestionWorker(db, blobs, None, settings.embedding_profile,
                    embedder_resolver=embedding.resolve_embedder)
                self.assertEqual(worker.run_next(), upload.job_id)
                self.assertEqual(db.get(IngestionJob, upload.job_id).state, IngestionJobState.COMPLETED)
                self.assertGreater(len(proxy.destinations), before + 1)
            before = len(proxy.destinations)
            embedding.apply_organization('admin', EmbeddingConnectionRequest(
                base_url=base, key_action='clear', expected_version=1, network=direct, model_id='baai/bge-m3'))
            new = embedding.resolve_embedder()
            new.embed_query('new operation')
            old.embed(['old job batch one', 'old job batch two'])
            self.assertEqual(len(proxy.destinations), before + 1)
            self.assertEqual(reply.get_organization('admin').network.mode, 'direct')
            self.assertTrue(all(destination == ('127.0.0.1', provider.server_port)
                                for destination in proxy.destinations))
