"""Organization settings: authority, atomic verification, secrets and shared policy."""
import importlib
import unittest
from dataclasses import replace
from unittest.mock import patch

from cryptography.fernet import Fernet
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ruvie import models
from ruvie.config import Settings, EmbeddingProfile, LlmProviderSettings
from ruvie.services.llm import LlmConnectionService
from ruvie.services.admin import AdminRequired


class OrganizationLlmTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(hasattr(models, 'OrganizationLlmSettings'), 'Organization persistence is missing')
        self.contracts = importlib.import_module('ruvie.contracts.llm')
        self.engine = create_engine('sqlite://')
        self.addCleanup(self.engine.dispose)
        models.Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)
        self.db.add_all([models.User(id='admin', email='admin@test', display_name='Admin', system_role='admin'),
                         models.User(id='user', email='user@test', display_name='User'),
                         models.OrganizationLlmSettings(id=1)])
        self.db.commit()
        self.settings = Settings('sqlite://', EmbeddingProfile('test', 1024, 'cosine'), None,
                                 LlmProviderSettings('https://ignored.test', 'env-model', 'env-key'),
                                 llm_settings_encryption_key=Fernet.generate_key().decode())
        self.service = LlmConnectionService(self.db, self.settings)
        self.catalog = [{'id': 'a', 'name': 'A'}, {'id': 'b', 'name': 'B'}, {'id': 'c', 'name': 'C'}]
        self.probe = patch('ruvie.adapters.llm.OpenAICompatibleLlmAdapter.list_models', return_value=self.catalog)
        self.probe.start()
        self.addCleanup(self.probe.stop)

    def command(self, **changes):
        values = dict(base_url='https://provider.test/v1', key_action='replace', api_key='test-provider-secret',
                      expected_version=0, allowed_model_ids=['a', 'b'], default_model_id='a')
        values.update(changes)
        if values.get('api_key') is None:
            values.pop('api_key', None)
        return self.contracts.OrganizationConnectionUpdateRequest(**values)

    def apply(self, **changes):
        return self.service.apply_organization('admin', self.command(**changes))

    def test_apply_encrypts_key_and_returns_only_safe_metadata(self):
        result = self.apply()
        self.assertEqual(result.version, 1)
        self.assertTrue(result.has_api_key)
        self.assertNotIn('test-provider-secret', result.model_dump_json())
        row = self.db.get(models.OrganizationLlmSettings, 1)
        self.assertNotIn('test-provider-secret', row.api_key_ciphertext)
        self.assertEqual(len(list(self.db.scalars(select(models.AuditEvent)))), 1)
        self.assertEqual(self.service.resolve_chat_adapter('user').provider.api_key, 'test-provider-secret')

    def test_non_admin_cannot_probe_or_apply(self):
        with patch('ruvie.adapters.llm.OpenAICompatibleLlmAdapter.list_models') as probe:
            with self.assertRaises(AdminRequired):
                self.service.apply_organization('user', self.command())
            with self.assertRaises(AdminRequired):
                self.service.verify_organization('user', self.contracts.OrganizationConnectionDraft(
                    base_url='https://provider.test/v1', key_action='clear', expected_version=0))
            probe.assert_not_called()

    def test_verify_does_not_write_and_apply_rechecks_catalog(self):
        draft = self.contracts.OrganizationConnectionDraft(base_url='https://provider.test/v1',
                                                          key_action='clear', expected_version=0)
        self.assertEqual(len(self.service.verify_organization('admin', draft).models), 3)
        self.assertEqual(self.db.get(models.OrganizationLlmSettings, 1).version, 0)
        self.assertEqual(list(self.db.scalars(select(models.AuditEvent))), [])
        with patch('ruvie.adapters.llm.OpenAICompatibleLlmAdapter.list_models', return_value=[{'id':'c','name':'C'}]):
            with self.assertRaises(ValueError):
                self.apply()
        self.assertEqual(self.db.get(models.OrganizationLlmSettings, 1).version, 0)

    def test_stale_version_and_changed_url_keep_do_not_send_credentials(self):
        self.apply()
        with patch('ruvie.adapters.llm.OpenAICompatibleLlmAdapter.list_models') as probe:
            with self.assertRaisesRegex(RuntimeError, 'configuration_conflict'):
                self.apply()
            with self.assertRaises(ValueError):
                self.apply(expected_version=1, key_action='keep', api_key=None, base_url='https://other.test/v1')
            probe.assert_not_called()

    def test_catalog_select_and_chat_share_policy_without_env_fallback(self):
        with self.assertRaises(RuntimeError):
            self.service.list_models('user')
        self.apply()
        self.assertEqual([m.id for m in self.service.list_models('user').models], ['a','b'])
        for operation in (lambda: self.service.select_model('user', 'c'),
                          lambda: self.service.resolve_chat_adapter('user', 'c')):
            with self.assertRaises(ValueError):
                operation()
        self.service.select_model('user', 'b')
        snapshot = self.service.resolve_chat_adapter('user')
        self.apply(expected_version=1, allowed_model_ids=['a'], key_action='clear', api_key=None)
        self.assertEqual(snapshot.provider.model, 'b')
        self.assertEqual(snapshot.provider.api_key, 'test-provider-secret')
        self.assertTrue(self.service.list_models('user').selection_required)
        with self.assertRaises(ValueError):
            self.service.resolve_chat_adapter('user')
        self.assertEqual(self.service.resolve_chat_adapter('user', 'a').provider.model, 'a')
        self.assertEqual(self.db.get(models.UserLlmSettings, 'user').selected_model_id, 'b')

    def test_missing_default_does_not_choose_first_model(self):
        self.apply()
        with patch('ruvie.adapters.llm.OpenAICompatibleLlmAdapter.list_models', return_value=[{'id':'b','name':'B'}]):
            result = self.service.list_models('user')
            self.assertIsNone(result.selected_model_id)
            self.assertTrue(result.selection_required)

    def test_database_failure_preserves_config_and_audit(self):
        self.apply()
        with patch.object(self.db, 'commit', side_effect=SQLAlchemyError('private-db-message')):
            with self.assertRaisesRegex(RuntimeError, 'llm_settings_unavailable'):
                self.apply(expected_version=1, key_action='clear', api_key=None)
        self.assertEqual(self.db.get(models.OrganizationLlmSettings, 1).version, 1)
        self.assertEqual(len(list(self.db.scalars(select(models.AuditEvent)))), 1)

    def test_draft_rejects_key_action_mismatch_duplicates_and_boolean_version(self):
        from pydantic import ValidationError
        for changes in (dict(key_action='clear'), dict(key_action='replace', api_key=' '),
                        dict(expected_version=True), dict(allowed_model_ids=['a','a']),
                        dict(allowed_model_ids=[]), dict(default_model_id='c')):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.command(**changes)
