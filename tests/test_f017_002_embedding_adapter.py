"""Embedding catalog separation and real vector validation with fake HTTP providers."""
import unittest
import httpx
from ruvie.adapters import embedding
from ruvie.config import EmbeddingProfile, EmbeddingProviderSettings


class EmbeddingAdapterTests(unittest.TestCase):
    def adapter(self, handler):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        return embedding.OpenAICompatibleQueryEmbedder(
            EmbeddingProviderSettings('https://provider.test/v1', 'private-key'),
            EmbeddingProfile('baai/bge-m3', 1024, 'cosine'), client)

    def test_catalog_uses_embedding_endpoint_and_does_not_guess_dimensions(self):
        def provider(request):
            self.assertEqual(request.url.path, '/v1/embeddings/models')
            return httpx.Response(200, json={'data': [
                {'id': 'baai/bge-m3', 'name': 'BGE'},
                {'id': 'other', 'name': 'Other', 'dimensions': 1024}]})
        adapter = self.adapter(provider)
        self.assertTrue(callable(getattr(adapter, 'list_models', None)), 'embedding catalog missing')
        self.assertEqual(adapter.list_models(), [
            {'id': 'baai/bge-m3', 'name': 'BGE', 'dimension': None, 'supported': True, 'reason_code': None},
            {'id': 'other', 'name': 'Other', 'dimension': 1024, 'supported': False, 'reason_code': 'embedding_model_unsupported'}])

    def test_query_rejects_nonfinite_and_boolean_vectors(self):
        for value in (float('nan'), float('inf'), True):
            with self.subTest(value=value):
                adapter = self.adapter(lambda request: httpx.Response(200,
                    text='{"data":[{"embedding":[' + ','.join(['NaN' if value != value else 'Infinity' if value == float('inf') else 'true'] * 1024) + ']}]}',
                    headers={'Content-Type': 'application/json'}))
                with self.assertRaises(ValueError):
                    adapter.embed_query('test')

    def test_redirect_is_rejected_without_forwarding_credentials(self):
        adapter = self.adapter(lambda request: httpx.Response(302, headers={'Location': 'https://other.test'}))
        with self.assertRaises(Exception):
            adapter.embed_query('test')

    def test_provider_without_key_omits_authorization_and_cookies(self):
        def provider(request):
            self.assertNotIn('authorization',request.headers)
            self.assertNotIn('cookie',request.headers)
            return httpx.Response(200,json={'data':[{'embedding':[0.1]*1024}]})
        client=httpx.Client(transport=httpx.MockTransport(provider),cookies={'session':'private'})
        self.addCleanup(client.close)
        adapter=embedding.OpenAICompatibleQueryEmbedder(EmbeddingProviderSettings('https://provider.test/v1',''),
            EmbeddingProfile('baai/bge-m3',1024,'cosine'),client)
        self.assertEqual(adapter.embed_query('test'),[0.1]*1024)
