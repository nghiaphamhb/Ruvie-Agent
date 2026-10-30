"""Employee network isolation and administrator response contracts."""
import unittest
from ruvie.contracts.llm import OrganizationConnectionResponse, ConnectionResponse, ModelsResponse
from ruvie.contracts.embedding import EmbeddingConnectionResponse
from ruvie.contracts.network import NetworkConfig

class ApiContractTests(unittest.TestCase):
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
