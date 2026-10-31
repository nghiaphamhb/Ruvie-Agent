"""Endpoint guard and DNS-rebinding tests."""
import socket
import select
import socketserver
import threading
from contextlib import contextmanager
import unittest
import httpcore
import httpx
from ruvie.adapters.llm import OpenAICompatibleLlmAdapter, LlmProviderError
from ruvie.adapters.embedding import OpenAICompatibleQueryEmbedder
from ruvie.config import LlmProviderSettings, EmbeddingProviderSettings, EmbeddingProfile
from unittest.mock import patch
from ruvie.adapters.network import normalize_proxy_url,pinned_proxy_url,effective_proxy,InvalidNetworkConfiguration,ProxyUnavailableError

def answer(ip):
    return [(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,1080))]


class _SocksHandler(socketserver.StreamRequestHandler):
    def handle(self):
        greeting = self.rfile.read(2)
        if len(greeting) != 2:
            return
        self.rfile.read(greeting[1])
        self.request.sendall(b'\x05\x00')
        header = self.rfile.read(4)
        family, size = (socket.AF_INET, 4) if header[3] == 1 else (socket.AF_INET6, 16)
        host = socket.inet_ntop(family, self.rfile.read(size))
        port = int.from_bytes(self.rfile.read(2), 'big')
        self.server.destinations.append((host, port))
        with socket.create_connection((host, port), timeout=5) as upstream:
            self.request.sendall(b'\x05\x00\x00\x01' + b'\x00' * 6)
            while True:
                readable, _, _ = select.select([self.request, upstream], [], [], 5)
                if not readable:
                    return
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    (upstream if source is self.request else self.request).sendall(data)


@contextmanager
def local_socks_proxy():
    """A real loopback SOCKS server recording the guarded numeric destinations."""
    class Server(socketserver.ThreadingTCPServer):
        daemon_threads = True
    with Server(('127.0.0.1', 0), _SocksHandler) as server:
        server.destinations = []
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join()

class NetworkTransportTests(unittest.TestCase):
    def test_proxy_tcp_failure_is_distinct_from_provider_failure(self):
        reply = OpenAICompatibleLlmAdapter(LlmProviderSettings('https://provider.test', 'm'),
                                           proxy_url='socks5://127.0.0.1:1080')
        embedding = OpenAICompatibleQueryEmbedder(EmbeddingProviderSettings('https://provider.test'),
            EmbeddingProfile('baai/bge-m3', 1024, 'cosine'), proxy_url='socks5://127.0.0.1:1080')
        operations = (reply.list_models, lambda: list(reply.stream([{'role':'user','content':'OK'}])),
                      lambda: embedding.embed_query('guide'))
        for failure in (httpcore.ConnectError, httpcore.ConnectTimeout):
            for operation in operations:
                with self.subTest(failure=failure.__name__, operation=operation), patch(
                    'socket.getaddrinfo', return_value=answer('93.184.216.34')
                ), patch.object(httpcore.SyncBackend, 'connect_tcp', side_effect=failure('internal endpoint')) as dial:
                    with self.assertRaises(ProxyUnavailableError) as caught:
                        operation()
                    self.assertEqual(str(caught.exception), 'proxy_unavailable')
                    self.assertEqual(dial.call_count, 1)
                    self.assertEqual(dial.call_args.kwargs['host'], '127.0.0.1')

    def test_provider_tls_failure_is_not_attributed_to_proxy(self):
        stream = httpcore.MockStream([b'\x05\x00', b'\x05\x00\x00\x01' + b'\x00' * 6])
        adapter = OpenAICompatibleLlmAdapter(LlmProviderSettings('https://provider.test'),
                                             proxy_url='socks5://127.0.0.1:1080')
        with patch('socket.getaddrinfo', return_value=answer('93.184.216.34')), patch.object(
            httpcore.SyncBackend, 'connect_tcp', return_value=stream
        ), patch.object(stream, 'start_tls', side_effect=httpcore.ConnectError('certificate verify failed')):
            with self.assertRaises(LlmProviderError):
                adapter.list_models()

    def test_socks_handshake_failure_has_safe_proxy_code(self):
        adapter = OpenAICompatibleLlmAdapter(LlmProviderSettings('https://provider.test'),
                                             proxy_url='socks5://127.0.0.1:1080')
        with patch('socket.getaddrinfo', return_value=answer('93.184.216.34')), patch.object(
            httpcore.SyncBackend, 'connect_tcp', return_value=httpcore.MockStream([b'\x05\xff'])
        ):
            with self.assertRaisesRegex(ProxyUnavailableError, '^proxy_unavailable$'):
                adapter.list_models()

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
