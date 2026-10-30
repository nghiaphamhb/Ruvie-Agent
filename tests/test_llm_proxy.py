"""Server-owned SOCKS routing preserves the destination guard and TLS identity."""
import os
import socket
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpcore
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from ruvie.adapters.llm import InvalidLlmUrl, LlmProviderError, OpenAICompatibleLlmAdapter, PinnedLlmTransport, create_llm_adapter
from ruvie.config import LlmProviderSettings, load_settings
from ruvie.services.llm import LlmConnectionService
from ruvie.contracts.network import NetworkConfig
from ruvie.adapters.network import normalize_proxy_url, InvalidNetworkConfiguration

PROXY = "socks5://127.0.0.1:12334"
PUBLIC_IP = "93.184.216.34"
ENVIRONMENT = {"DATABASE_URL": "postgresql://offline/offline", "EMBEDDING_MODEL_ID": "BAAI/bge-m3", "EMBEDDING_DIMENSION": "1024", "EMBEDDING_DISTANCE_METRIC": "cosine"}


def resolved(address):
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, 443))]


class RecordingStream(httpcore.MockStream):
    def __init__(self, body):
        super().__init__([b"\x05\x00", b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00", b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body])
        self.writes = []
        self.tls_hostname = None

    def write(self, buffer, timeout=None):
        self.writes.append(buffer)

    def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        self.tls_hostname = server_hostname
        return super().start_tls(ssl_context, server_hostname, timeout)


class LlmProxyTests(unittest.TestCase):
    def test_proxy_is_explicit_server_configuration_with_direct_default(self):
        with patch.dict(os.environ, ENVIRONMENT, clear=True), patch("ruvie.config.load_dotenv"):
            self.assertIsNone(getattr(load_settings(), "llm_proxy_url", "missing"))
            os.environ["LLM_PROXY_URL"] = " " + PROXY + " "
            self.assertIsNone(load_settings().llm_proxy_url)  # DB-only runtime

    def test_invalid_proxy_configuration_fails_without_echoing_credentials(self):
        for value in ("http://user:secret@proxy:8080", "socks5://", "socks5://proxy:bad", "socks5://proxy:0", "socks5://proxy:1080/path", "socks5://proxy:1080?q=secret"):
            with self.subTest(value=value):
                with self.assertRaises(InvalidNetworkConfiguration) as raised:
                    normalize_proxy_url(value)
                self.assertNotIn("secret", str(raised.exception))

    def test_service_routes_discovery_and_chat_through_proxy_with_pinned_tls_identity(self):
        settings = SimpleNamespace(llm_allowed_local_origins=(), llm_proxy_url=PROXY)
        adapter = LlmConnectionService(None, settings)._adapter(LlmProviderSettings("https://llm.test/v1", "a", "test-key"), NetworkConfig(mode="proxy", proxy_url=PROXY))
        for operation, body in ((lambda: adapter.list_models(), b'{"data":[{"id":"a"}]}'), (lambda: list(adapter.stream([{"role": "user", "content": "hello"}])), b'data: {"choices":[{"delta":{"content":"answer"}}]}\n\ndata: [DONE]\n\n')):
            stream = RecordingStream(body)
            destinations = []
            def connect(backend, host, port, **kwargs):
                destinations.append((host, port))
                return stream
            with patch("socket.getaddrinfo", return_value=resolved(PUBLIC_IP)), patch.object(httpcore.SyncBackend, "connect_tcp", connect):
                result = operation()
            self.assertEqual(result, [{"id": "a", "name": "a"}] if body.startswith(b'{') else ["answer"])
            self.assertEqual(destinations, [("127.0.0.1", 12334)])
            # SOCKS CONNECT must contain the checked address, never a hostname to re-resolve.
            self.assertEqual(stream.writes[1], b'\x05\x01\x00\x01\x5d\xb8\xd8\x22\x01\xbb')
            self.assertNotIn(b"llm.test", stream.writes[1])
            self.assertEqual(stream.tls_hostname, "llm.test")
            self.assertIn(b"Host: llm.test\r\n", stream.writes[2])

    def test_forbidden_destinations_never_reach_proxy(self):
        for address in ("127.0.0.1", "169.254.169.254", "100.100.100.200", "168.63.129.16", "::ffff:169.254.169.254"):
            with self.subTest(address=address), patch("socket.getaddrinfo", return_value=resolved(address)), patch.object(httpcore.SyncBackend, "connect_tcp") as connect:
                with httpx.Client(transport=PinnedLlmTransport(proxy_url=PROXY), trust_env=False) as client:
                    with self.assertRaises(InvalidLlmUrl):
                        client.get("https://llm.test/models")
                connect.assert_not_called()

    def test_proxy_checks_mixed_and_rebound_dns_before_each_request(self):
        stream = RecordingStream(b'{"data":[{"id":"a"}]}')
        with patch("socket.getaddrinfo", side_effect=[resolved(PUBLIC_IP), resolved("127.0.0.1")]), patch.object(httpcore.SyncBackend, "connect_tcp", return_value=stream):
            with httpx.Client(transport=PinnedLlmTransport(proxy_url=PROXY), trust_env=False) as client:
                self.assertEqual(client.get("https://llm.test/models").status_code, 200)
                with self.assertRaises(InvalidLlmUrl):
                    client.get("https://llm.test/models")
        with patch("socket.getaddrinfo", return_value=resolved(PUBLIC_IP) + resolved("127.0.0.1")), patch.object(httpcore.SyncBackend, "connect_tcp") as connect:
            with httpx.Client(transport=PinnedLlmTransport(proxy_url=PROXY), trust_env=False) as client:
                with self.assertRaises(InvalidLlmUrl):
                    client.get("https://llm.test/models")
            connect.assert_not_called()

    def test_redirect_through_proxy_is_rejected_without_following_location(self):
        stream = RecordingStream(b"")
        stream._buffer[-1] = b"HTTP/1.1 302 Found\r\nLocation: https://other.test/models\r\nContent-Length: 0\r\n\r\n"
        adapter = OpenAICompatibleLlmAdapter(LlmProviderSettings("https://llm.test/v1"), proxy_url=PROXY)
        with patch("socket.getaddrinfo", return_value=resolved(PUBLIC_IP)), patch.object(httpcore.SyncBackend, "connect_tcp", return_value=stream) as connect:
            with self.assertRaises(LlmProviderError):
                adapter.list_models()
        self.assertEqual(connect.call_count, 1)
        self.assertEqual(sum(data.startswith(b"GET ") for data in stream.writes), 1)

    def test_failed_proxy_does_not_fall_back_to_direct_or_leak_details(self):
        adapter = OpenAICompatibleLlmAdapter(LlmProviderSettings("https://llm.test/v1"), proxy_url=PROXY)
        with patch("socket.getaddrinfo", return_value=resolved(PUBLIC_IP)), patch.object(httpcore.SyncBackend, "connect_tcp", side_effect=httpcore.ConnectError("proxy-secret")) as connect:
            with self.assertRaises(LlmProviderError) as raised:
                adapter.list_models()
        self.assertNotIn("proxy-secret", str(raised.exception))
        self.assertEqual(connect.call_count, 1)
        self.assertEqual(connect.call_args.kwargs["host"], "127.0.0.1")

    def test_factory_propagates_proxy_and_local_permissions(self):
        settings = SimpleNamespace(llm=LlmProviderSettings("https://llm.test/v1"), llm_allowed_local_origins=("http://localhost:11434",), llm_proxy_url=PROXY)
        adapter = create_llm_adapter(settings)
        self.assertEqual(getattr(adapter, "proxy_url", None), PROXY)
        self.assertEqual(adapter.allowed_local_origins, settings.llm_allowed_local_origins)


if __name__ == "__main__":
    unittest.main()
