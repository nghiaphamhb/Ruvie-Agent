"""Secret storage must fail closed without exposing credentials."""
import importlib
import importlib.util
import os
import unittest
from unittest.mock import patch


class LlmSecretTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('ruvie.services.llm_secrets'),
                             'F016 needs encrypted organization credentials')
        self.module = importlib.import_module('ruvie.services.llm_secrets')
        from cryptography.fernet import Fernet
        self.key = Fernet.generate_key().decode('ascii')

    def test_encrypted_key_roundtrips_without_plaintext_at_rest(self):
        store = self.module.LlmSecretStore(self.key)
        first = store.encrypt('private-provider-key')
        second = store.encrypt('private-provider-key')
        self.assertTrue(first.startswith('v1:'))
        self.assertNotIn('private-provider-key', first)
        self.assertNotEqual(first, second)
        self.assertEqual(store.decrypt(first), 'private-provider-key')

    def test_keyless_connection_does_not_require_encryption_key(self):
        store = self.module.LlmSecretStore(None)
        self.assertIsNone(store.encrypt(None))
        self.assertIsNone(store.encrypt(''))
        self.assertEqual(store.decrypt(None), '')

    def test_missing_wrong_or_corrupt_credentials_fail_closed(self):
        token = self.module.LlmSecretStore(self.key).encrypt('private-provider-key')
        for key, value in ((None, token), (self.key, 'v1:broken'),
                           (self.key, 'v2:unknown'), (self.key, ''),
                           (self.key, 'private-provider-key')):
            with self.subTest(value=value[:3]):
                with self.assertRaises(self.module.LlmSecretError) as caught:
                    self.module.LlmSecretStore(key).decrypt(value)
                self.assertEqual(str(caught.exception), 'llm_settings_unavailable')
        from cryptography.fernet import Fernet
        with self.assertRaises(self.module.LlmSecretError):
            self.module.LlmSecretStore(Fernet.generate_key().decode()).decrypt(token)
        with self.assertRaises(self.module.LlmSecretError):
            self.module.LlmSecretStore(None).encrypt('private-provider-key')

    def test_invalid_server_key_and_repr_do_not_expose_secrets(self):
        with self.assertRaises(self.module.LlmSecretError) as caught:
            self.module.LlmSecretStore('invalid-server-secret')
        self.assertNotIn('invalid-server-secret', str(caught.exception))
        store = self.module.LlmSecretStore(self.key)
        self.assertNotIn(self.key, repr(store))

    def test_settings_load_server_key_without_exposing_it_in_repr(self):
        from ruvie.config import load_settings
        environment = {
            'DATABASE_URL': 'postgresql+psycopg://offline:offline@localhost/offline',
            'EMBEDDING_MODEL_ID': 'baai/bge-m3', 'EMBEDDING_DIMENSION': '1024',
            'EMBEDDING_DISTANCE_METRIC': 'cosine',
            'LLM_SETTINGS_ENCRYPTION_KEY': self.key,
        }
        with patch.dict(os.environ, environment, clear=True), patch('ruvie.config.load_dotenv'):
            settings = load_settings()
        self.assertEqual(getattr(settings, 'llm_settings_encryption_key', None), self.key)
        self.assertNotIn(self.key, repr(settings))
        environment['LLM_SETTINGS_ENCRYPTION_KEY'] = 'invalid-secret'
        with patch.dict(os.environ, environment, clear=True), patch('ruvie.config.load_dotenv'):
            with self.assertRaises(RuntimeError) as caught:
                load_settings()
        self.assertNotIn('invalid-secret', str(caught.exception))

    def test_obsolete_environment_credentials_do_not_create_a_fallback(self):
        from ruvie.config import load_settings
        for values in ({'LLM_API_KEY':'obsolete-key'},
                       {'LLM_BASE_URL':'https://obsolete.test','LLM_MODEL':'old','LLM_API_KEY':'obsolete-key'}):
            environment = {'DATABASE_URL':'postgresql://offline/offline',
                           'EMBEDDING_MODEL_ID':'test','EMBEDDING_DIMENSION':'1024',
                           'EMBEDDING_DISTANCE_METRIC':'cosine', **values}
            with patch.dict(os.environ, environment, clear=True), patch('ruvie.config.load_dotenv'):
                self.assertIsNone(load_settings().llm)
