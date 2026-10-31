"""F016 persistence cutover and constraints, including offline migration SQL."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ruvie import models

ROOT = Path(__file__).resolve().parents[1]


class OrganizationSchemaTests(unittest.TestCase):
    def test_personal_settings_cannot_store_connection_or_credentials(self):
        self.assertNotIn('api_key', models.UserLlmSettings.__table__.c)
        self.assertNotIn('base_url', models.UserLlmSettings.__table__.c)
        self.assertNotIn('models', models.UserLlmSettings.__table__.c)

    def test_singleton_rejects_second_identity_or_inconsistent_state(self):
        self.assertTrue(hasattr(models, 'OrganizationLlmSettings'))
        engine = create_engine('sqlite://')
        self.addCleanup(engine.dispose)
        models.Base.metadata.create_all(engine)
        for values in (dict(id=2), dict(id=1, version=-1),
                       dict(id=1, version=1), dict(id=1, api_key_ciphertext='not-configured')):
            with self.subTest(values=values), Session(engine) as db:
                db.add(models.OrganizationLlmSettings(**values))
                with self.assertRaises(IntegrityError):
                    db.commit()

    def test_migration_sql_seeds_empty_org_and_removes_personal_secrets(self):
        environment = {**os.environ, 'DATABASE_URL':'postgresql+psycopg://offline:offline@localhost/offline',
                       'EMBEDDING_MODEL_ID':'test','EMBEDDING_DIMENSION':'1024',
                       'EMBEDDING_DISTANCE_METRIC':'cosine'}
        for action, revision, expected in (
            ('upgrade','head', ('CREATE TABLE organization_llm_settings', 'DROP COLUMN api_key',
                               'DROP COLUMN base_url', 'DROP COLUMN models', 'INSERT INTO organization_llm_settings')),
            ('downgrade','0012_organization_llm_settings:0011_user_presence',
             ('DROP TABLE organization_llm_settings','ADD COLUMN api_key'))):
            result = subprocess.run([sys.executable,'-B','-m','alembic','-c','backend/alembic.ini',
                                     action, revision,'--sql'], cwd=ROOT, env=environment,
                                    capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            for fragment in expected:
                self.assertIn(fragment,result.stdout)


class OrganizationPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_f005_007_e2e as fixtures
        cls.fixtures = fixtures
        fixtures.F005007EndToEndTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.F005007EndToEndTests.tearDownClass()

    def setUp(self):
        self.fixture = self.fixtures.F005007EndToEndTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.factory = self.fixture.client.app.state.session_factory

    def test_cutover_keeps_preferences_and_cannot_restore_old_credentials(self):
        from unittest.mock import patch
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import text, inspect
        config = Config(str(ROOT / 'backend/alembic.ini'))
        engine = self.fixture.client.app.state.engine
        with patch.dict(os.environ, {'DATABASE_URL':self.fixture.database_url}):
            command.downgrade(config,'0011_user_presence')
            with engine.begin() as db:
                db.execute(text("INSERT INTO user_llm_settings (user_id,base_url,api_key,selected_model_id) VALUES ('alpha','https://old.test','old-private-key','old-id')"))
            command.upgrade(config,'head')
            with self.factory() as db:
                self.assertEqual(db.get(models.UserLlmSettings,'alpha').selected_model_id,'old-id')
                row=db.get(models.OrganizationLlmSettings,1)
                self.assertEqual((row.version,row.base_url,row.api_key_ciphertext,row.allowed_model_ids),(0,None,None,[]))
            self.assertNotIn('api_key',{c['name'] for c in inspect(engine).get_columns('user_llm_settings')})
            command.downgrade(config,'0011_user_presence')
            with engine.connect() as db:
                self.assertEqual(tuple(db.execute(text("SELECT base_url,api_key,models,selected_model_id FROM user_llm_settings WHERE user_id='alpha'")).one()),(None,None,[],'old-id'))
            command.upgrade(config,'head')

    def test_parallel_admin_apply_has_one_winner_and_one_audit(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from unittest.mock import patch
        from sqlalchemy import select
        from ruvie.contracts.llm import OrganizationConnectionUpdateRequest
        from ruvie.services.llm import LlmConnectionService, LlmConfigurationConflict
        with self.factory() as db:
            for actor in ('alpha','beta'):
                db.get(models.User,actor).system_role='admin'
            row=db.get(models.OrganizationLlmSettings,1)
            version=row.version
            db.commit()
        barrier=Barrier(2)
        def probe(_adapter):
            barrier.wait(timeout=10)
            return [{'id':'a','name':'A'}]
        def apply(actor):
            with self.factory() as db:
                try:
                    return LlmConnectionService(db,self.fixture.settings).apply_organization(actor,
                        OrganizationConnectionUpdateRequest(network={'mode':'direct','proxy_url':None}, base_url='https://provider.test/v1',
                            key_action='clear',expected_version=version,allowed_model_ids=['a'],default_model_id='a')).version
                except LlmConfigurationConflict:
                    return 'conflict'
        with patch('ruvie.adapters.llm.OpenAICompatibleLlmAdapter.list_models',probe):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(apply,('alpha','beta')))
        self.assertCountEqual(results,[version+1,'conflict'])
        with self.factory() as db:
            self.assertEqual(db.get(models.OrganizationLlmSettings,1).version,version+1)
            self.assertEqual(len(list(db.scalars(select(models.AuditEvent).where(
                models.AuditEvent.action=='llm.organization_settings.update')))),1)

    def test_admin_revoked_during_probe_cannot_commit(self):
        from unittest.mock import patch
        from ruvie.contracts.llm import OrganizationConnectionUpdateRequest
        from ruvie.services.admin import AdminRequired
        from ruvie.services.llm import LlmConnectionService
        with self.factory() as db:
            db.get(models.User,'alpha').system_role='admin'
            version=db.get(models.OrganizationLlmSettings,1).version
            db.commit()
        def revoke(_adapter):
            with self.factory() as db:
                db.get(models.User,'alpha').system_role='user'
                db.commit()
            return [{'id':'a','name':'A'}]
        with self.factory() as db, patch('ruvie.adapters.llm.OpenAICompatibleLlmAdapter.list_models',revoke):
            with self.assertRaises(AdminRequired):
                LlmConnectionService(db,self.fixture.settings).apply_organization('alpha',
                    OrganizationConnectionUpdateRequest(network={'mode':'direct','proxy_url':None}, base_url='https://provider.test/v1',key_action='clear',
                        expected_version=version,allowed_model_ids=['a'],default_model_id='a'))
        with self.factory() as db:
            self.assertEqual(db.get(models.OrganizationLlmSettings,1).version,version)

    def test_parallel_initial_configuration_has_one_winner(self):
        with self.factory() as db:
            row=db.get(models.OrganizationLlmSettings,1)
            row.version=0
            row.base_url=None
            row.api_key_ciphertext=None
            row.allowed_model_ids=[]
            row.default_model_id=None
            db.commit()
        self.test_parallel_admin_apply_has_one_winner_and_one_audit()
