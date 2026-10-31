"""Embedding administration keeps secrets, authority, versions and runtime snapshots isolated."""
import importlib
import unittest
from pathlib import Path
from unittest.mock import patch
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from ruvie import models
from ruvie.config import Settings, EmbeddingProfile
from ruvie.services.admin import AdminRequired


class EmbeddingServiceTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(Path('backend/ruvie/services/embedding.py').exists(), 'embedding service missing')
        self.contracts = importlib.import_module('ruvie.contracts.embedding')
        module = importlib.import_module('ruvie.services.embedding')
        self.engine = create_engine('sqlite://')
        self.addCleanup(self.engine.dispose)
        models.Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)
        self.db.add_all([models.User(id='admin', email='admin@test', display_name='Admin', system_role='admin'),
                         models.User(id='user', email='user@test', display_name='User'),
                         models.OrganizationEmbeddingSettings(id=1)])
        self.db.commit()
        self.settings = Settings('sqlite://', EmbeddingProfile('baai/bge-m3',1024,'cosine'),None,None,
                                 llm_settings_encryption_key=Fernet.generate_key().decode())
        self.service = module.EmbeddingConnectionService(self.db, self.settings)
        probe = patch('ruvie.adapters.embedding.OpenAICompatibleQueryEmbedder.embed_query', return_value=[0.1]*1024)
        probe.start()
        self.addCleanup(probe.stop)

    def command(self, **changes):
        values = dict(network={'mode':'direct','proxy_url':None}, base_url='https://provider.test/v1', key_action='replace', api_key='private-embedding-key',
                      expected_version=0, model_id='baai/bge-m3') | changes
        if values.get('api_key') is None:
            values.pop('api_key')
        return self.contracts.EmbeddingConnectionRequest(**values)

    def test_apply_encrypted_metadata_and_operation_snapshot(self):
        result = self.service.apply_organization('admin',self.command())
        self.assertEqual(result.version,1)
        self.assertNotIn('private-embedding-key', result.model_dump_json())
        self.assertNotIn('private-embedding-key', self.db.get(models.OrganizationEmbeddingSettings,1).api_key_ciphertext)
        old = self.service.resolve_embedder()
        self.service.apply_organization('admin',self.command(expected_version=1,key_action='clear',api_key=None))
        self.assertEqual(old.provider.api_key,'private-embedding-key')
        self.assertEqual(self.service.resolve_embedder().provider.api_key,'')
        self.assertEqual(len(list(self.db.scalars(select(models.AuditEvent)))),2)

    def test_unsupported_model_never_probes_or_commits(self):
        with patch('ruvie.adapters.embedding.OpenAICompatibleQueryEmbedder.embed_query') as probe:
            with self.assertRaisesRegex(ValueError,'embedding_model_unsupported'):
                self.service.apply_organization('admin',self.command(model_id='other'))
            probe.assert_not_called()
        self.assertEqual(self.service.get_organization('admin').version,0)

    def test_nonadmin_and_changed_url_keep_never_probe(self):
        with self.assertRaises(AdminRequired):
            self.service.apply_organization('user', self.command())
        self.service.apply_organization('admin',self.command())
        with patch('ruvie.adapters.embedding.OpenAICompatibleQueryEmbedder.embed_query') as probe:
            with self.assertRaises(ValueError):
                self.service.apply_organization('admin',self.command(expected_version=1,key_action='keep',api_key=None,base_url='https://other.test'))
            probe.assert_not_called()

    def test_verify_does_not_save_and_revoked_admin_cannot_apply(self):
        result = self.service.verify_organization('admin',self.command())
        self.assertTrue(result.compatible)
        self.assertEqual(self.service.get_organization('admin').version,0)
        def revoke(query):
            self.db.get(models.User,'admin').system_role='user'
            self.db.commit()
            return [0.1]*1024
        with patch('ruvie.adapters.embedding.OpenAICompatibleQueryEmbedder.embed_query',side_effect=revoke):
            with self.assertRaises(AdminRequired):
                self.service.apply_organization('admin',self.command())
        self.assertEqual(self.db.get(models.OrganizationEmbeddingSettings,1).version,0)

    def test_failed_commit_rolls_back_configuration_and_audit(self):
        from sqlalchemy.exc import SQLAlchemyError
        with patch.object(self.db,'commit',side_effect=SQLAlchemyError('private parameters')):
            with self.assertRaisesRegex(RuntimeError,'embedding_settings_unavailable'):
                self.service.apply_organization('admin',self.command())
        self.assertEqual(self.service.get_organization('admin').version,0)
        self.assertEqual(list(self.db.scalars(select(models.AuditEvent))),[])

    def test_corrupt_ciphertext_never_becomes_anonymous_request(self):
        self.service.apply_organization('admin',self.command())
        self.db.get(models.OrganizationEmbeddingSettings,1).api_key_ciphertext='broken'
        self.db.commit()
        with patch('ruvie.adapters.embedding.OpenAICompatibleQueryEmbedder.embed_query') as probe:
            with self.assertRaises(RuntimeError):
                self.service.resolve_embedder()
            probe.assert_not_called()
