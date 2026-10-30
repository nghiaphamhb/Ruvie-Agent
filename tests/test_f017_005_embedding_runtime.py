"""Runtime must resolve embedding after reply policy, and isolate safe failures."""
import unittest
from contextlib import nullcontext
from unittest.mock import Mock, patch
from ruvie.services.chat import ChatService


class EmbeddingRuntimeTests(unittest.TestCase):
    def test_unconfigured_embedding_has_distinct_error_after_reply_policy(self):
        from ruvie.services.embedding import EmbeddingUnavailableError
        with patch('ruvie.services.chat.LlmConnectionService') as llm, patch('ruvie.services.embedding.EmbeddingConnectionService.resolve_embedder',side_effect=EmbeddingUnavailableError('embedding_not_configured')):
            llm.return_value.resolve_chat_adapter.return_value = Mock()
            service = ChatService(None, Mock(), lambda:nullcontext(Mock()))
            with self.assertRaisesRegex(EmbeddingUnavailableError,'embedding_not_configured'):
                service.prepare('user','question')
            llm.return_value.resolve_chat_adapter.assert_called_once_with('user',None)

    def test_reply_policy_failure_prevents_embedding_resolution(self):
        with patch('ruvie.services.chat.LlmConnectionService') as llm, patch('ruvie.services.embedding.EmbeddingConnectionService.resolve_embedder') as embedding:
            llm.return_value.resolve_chat_adapter.side_effect = ValueError('model_not_allowed')
            with self.assertRaisesRegex(ValueError,'model_not_allowed'):
                ChatService(None,Mock(),lambda:nullcontext(Mock())).prepare('user','question')
            embedding.assert_not_called()
