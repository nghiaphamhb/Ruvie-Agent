"""Reply smoke test must generate text independently of catalog verification."""
import unittest
from unittest.mock import patch
import test_f016_003_admin_llm as fixtures


class ReplyProbeTests(unittest.TestCase):
    def setUp(self):
        fixtures.OrganizationLlmTests.setUp(self)
    def test_catalog_success_does_not_imply_reply_probe_success(self):
        self.assertTrue(callable(getattr(self.service,'probe_organization',None)), 'reply probe missing')
        command = self.contracts.OrganizationModelProbeRequest(network={'mode':'direct','proxy_url':None}, base_url='https://provider.test/v1',
            key_action='clear',expected_version=0,model_id='a')
        with patch('ruvie.adapters.llm.OpenAICompatibleLlmAdapter.stream',return_value=iter([])):
            with self.assertRaises(RuntimeError):
                self.service.probe_organization('admin',command)
        with patch('ruvie.adapters.llm.OpenAICompatibleLlmAdapter.stream',return_value=iter(['OK'])):
            self.assertTrue(self.service.probe_organization('admin',command)['success'])
        self.assertEqual(self.service.get_organization('admin').version,0)
