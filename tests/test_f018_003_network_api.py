"""Employee network isolation and administrator response contracts."""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from ruvie.api.documents import router
from ruvie.dependencies import get_authenticated_user_id, get_session
from ruvie.adapters.network import (NetworkConfigurationPendingError, ProxyUnavailableError,
                                    InvalidNetworkConfiguration)
from ruvie.contracts.llm import OrganizationConnectionResponse, ConnectionResponse, ModelsResponse
from ruvie.contracts.embedding import EmbeddingConnectionResponse
from ruvie.contracts.network import NetworkConfig

class ApiContractTests(unittest.TestCase):
    def test_retrieval_network_resolution_errors_are_safe_503(self):
        app = FastAPI()
        app.include_router(router)
        app.state.session_factory = MagicMock()
        app.state.settings = SimpleNamespace()
        app.dependency_overrides[get_authenticated_user_id] = lambda: 'employee'
        app.dependency_overrides[get_session] = lambda: None
        with TestClient(app, raise_server_exceptions=False) as client:
            for error in (NetworkConfigurationPendingError(), ProxyUnavailableError(),
                          InvalidNetworkConfiguration()):
                with self.subTest(error=type(error).__name__), patch(
                    'ruvie.services.embedding.EmbeddingConnectionService.resolve_embedder',
                    side_effect=error,
                ):
                    response = client.post('/documents/retrieve', json={'query': 'guide', 'limit': 3})
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(response.json(), {'detail': {'code': 'embedding_unavailable'}})

    def test_admin_only_metadata_contains_proxy(self):
        n=NetworkConfig(mode='proxy',proxy_url='socks5://127.0.0.1:1080')
        llm=OrganizationConnectionResponse(configured=True,base_url='https://p.test',
            has_api_key=True,network=n,allowed_model_ids=['m'],default_model_id='m',
            version=2,updated_at=None)
        embed=EmbeddingConnectionResponse(configured=True,base_url='https://p.test',
            has_api_key=True,network=n,model_id='baai/bge-m3',dimension=1024,
            distance_metric='cosine',version=2,updated_at=None)
        self.assertEqual(llm.network.proxy_url,embed.network.proxy_url)
        employee=ConnectionResponse(configured=True,selected_model_id='m',configuration_version=2)
        models=ModelsResponse(models=[],selected_model_id=None,selection_required=True,configuration_version=2)
        for response in (employee,models):
            self.assertNotIn('proxy',response.model_dump_json())
            self.assertNotIn('base_url',response.model_dump_json())
