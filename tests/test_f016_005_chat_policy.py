"""Failures resolving organization credentials must stop before embedding/context."""
import unittest
from unittest.mock import Mock, patch
from sqlalchemy.exc import SQLAlchemyError
from ruvie.services.chat import ChatService, ProviderUnavailableError
from ruvie.services.llm import LlmStorageError, LlmNotConfiguredError
from ruvie.services.llm_secrets import LlmSecretError


class ChatSettingsFailureTests(unittest.TestCase):
    def test_storage_secret_and_unconfigured_errors_stop_before_embedding(self):
        from contextlib import nullcontext
        for error in (LlmSecretError(), LlmStorageError(), LlmNotConfiguredError(),
                      SQLAlchemyError('private-bound-parameters')):
            with self.subTest(error=type(error).__name__):
                embedder=Mock()
                service=ChatService(embedder,None,lambda:nullcontext(None))
                with patch('ruvie.services.llm.LlmConnectionService.resolve_chat_adapter',side_effect=error):
                    with self.assertRaises(ProviderUnavailableError):
                        service.prepare('user','question')
                embedder.embed_query.assert_not_called()
