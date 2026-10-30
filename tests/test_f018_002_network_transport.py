"""Endpoint guard and DNS-rebinding tests."""
import socket
import unittest
from unittest.mock import patch
from ruvie.adapters.network import normalize_proxy_url,pinned_proxy_url,effective_proxy,InvalidNetworkConfiguration,ProxyUnavailableError

def answer(ip):
    return [(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,1080))]

class NetworkTransportTests(unittest.TestCase):
    def test_reject_unsafe_endpoints(self):
        for url in ('socks5h://localhost:1080','socks5://user:secret@localhost:1080',
                    'socks5://localhost:1080/path','socks5://0.0.0.0:1080',
                    'socks5://169.254.169.254:1080','socks5://localhost:65536'):
            with self.subTest(url=url),self.assertRaises(InvalidNetworkConfiguration) as result:
                normalize_proxy_url(url)
            self.assertNotIn(url,str(result.exception))

    def test_pin_all_dns_answers_and_reject_rebinding(self):
        with patch('ruvie.adapters.network.socket.getaddrinfo',return_value=answer('10.0.0.2')):
            self.assertEqual(pinned_proxy_url('socks5://proxy.local:1080'),'socks5://10.0.0.2:1080')
        with patch('ruvie.adapters.network.socket.getaddrinfo',return_value=answer('10.0.0.2')+answer('169.254.169.254')):
            with self.assertRaises(InvalidNetworkConfiguration):
                pinned_proxy_url('socks5://proxy.local:1080')
        with patch('ruvie.adapters.network.socket.getaddrinfo',side_effect=OSError('private detail')):
            with self.assertRaises(ProxyUnavailableError):
                pinned_proxy_url('socks5://proxy.local:1080')

    def test_direct_never_reads_ambient_proxy(self):
        with patch('ruvie.adapters.network.socket.getaddrinfo') as dns:
            self.assertIsNone(effective_proxy('direct',None))
            dns.assert_not_called()
