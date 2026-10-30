"""LLM and embedding routes are explicit, independent and per-operation."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from ruvie.config import LlmProviderSettings, EmbeddingProviderSettings
from ruvie.contracts.network import NetworkConfig
from ruvie.services.llm import LlmConnectionService
from ruvie.services.embedding import EmbeddingConnectionService

class NetworkRuntimeTests(unittest.TestCase):
    def test_runtime_ignores_legacy_proxy_settings(self):
        settings=SimpleNamespace(llm_allowed_local_origins=(),
            llm_proxy_url='socks5://legacy:9',embedding_proxy_url='socks5://legacy:9')
        llm=LlmConnectionService(None,settings)
        embedding=EmbeddingConnectionService(None,settings)
        proxy=NetworkConfig(mode='proxy',proxy_url='socks5://127.0.0.1:12334')
        direct=NetworkConfig(mode='direct',proxy_url=None)
        with patch('ruvie.services.llm.effective_proxy',return_value=proxy.proxy_url) as llm_route:
            a=llm._adapter(LlmProviderSettings('https://provider.test/v1'),proxy)
            self.assertEqual(a.proxy_url,proxy.proxy_url)
            llm_route.assert_called_once_with('proxy',proxy.proxy_url)
        with patch('ruvie.services.embedding.effective_proxy',return_value=None) as embed_route:
            b=embedding._adapter(EmbeddingProviderSettings('https://provider.test/v1'),direct)
            self.assertIsNone(b.transport.proxy_url)
            embed_route.assert_called_once_with('direct',None)
