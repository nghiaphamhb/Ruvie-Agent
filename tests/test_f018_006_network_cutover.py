"""One-shot conversion does not overwrite already converted routes."""
import unittest
from unittest.mock import Mock,patch
from ruvie.contracts.network import NetworkConfig
from ruvie.network_settings_cli import legacy_network,convert

class NetworkCutoverTests(unittest.TestCase):
    def test_legacy_parser_dry_run_inputs(self):
        with patch.dict('os.environ',{'LLM_PROXY_URL':'socks5://127.0.0.1:12334'}):
            self.assertEqual(legacy_network('LLM_PROXY_URL').mode,'proxy')
        with patch.dict('os.environ',{'LLM_PROXY_URL':''}):
            self.assertEqual(legacy_network('LLM_PROXY_URL').mode,'direct')
        with patch.dict('os.environ',{'LLM_PROXY_URL':'socks5h://localhost:12334'}):
            with self.assertRaises(ValueError):
                legacy_network('LLM_PROXY_URL')

    def test_idempotent_confirm(self):
        session=Mock()
        session.scalar.side_effect=[Mock(network_mode='proxy'),Mock(network_mode='direct')]
        network=NetworkConfig(mode='direct',proxy_url=None)
        with patch('ruvie.network_settings_cli.AdminAccountService') as admins:
            self.assertFalse(convert(session,'admin',2,3,network,network))
            admins.return_value.require_admin.assert_called_once_with('admin',lock=True)
        session.execute.assert_not_called()
        session.commit.assert_not_called()
        session.rollback.assert_called_once()
