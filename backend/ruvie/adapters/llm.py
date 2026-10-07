"""OpenAI-compatible model listing and streaming chat API.

Model request/response (Authorization is sent only when a key exists):

    GET https://llm.example.com/v1/models
    {"data": [{"id": "chat-model", "name": "Chat Model"}]}


Example HTTP request:

    POST https://llm.example.com/v1/chat/completions
    Authorization: Bearer <LLM_API_KEY>
    Content-Type: application/json

    {
      "model": "chat-model",
      "messages": [{"role": "user", "content": "Cách cài plugin X?"}],
      "stream": true
    }

Example HTTP stream response:

    data: {"choices": [{"delta": {"content": "Bước 1..."}}]}
    data: [DONE]
"""

import ipaddress
import json
import socket
from collections.abc import Iterator
from contextlib import closing, contextmanager
from typing import Protocol
from urllib.parse import urlsplit

import httpx

from ruvie.config import LlmProviderSettings, Settings


class InvalidLlmUrl(ValueError):
    pass


class LlmProviderError(RuntimeError):
    pass


def normalize_llm_url(value: str, allowed_local_origins: tuple[str, ...] = ()) -> str:
    """Validate URL syntax and the server-owned HTTP origin permission."""
    try:
        value = value.strip()
        parts = urlsplit(value)
        url = httpx.URL(value)
        if (
            url.scheme not in ("http", "https") or not url.host
            or "@" in parts.netloc or "\\" in value
            or "?" in value or "#" in value or "%" in url.host
        ):
            raise ValueError
        # Origin means scheme + host + port, without the API path.
        origin = f"{url.scheme}://{url.netloc.decode('ascii')}"
        if url.scheme == "http" and origin not in allowed_local_origins:
            raise ValueError
        return str(url).rstrip("/")
    except (ValueError, httpx.InvalidURL):
        raise InvalidLlmUrl("LLM URL is invalid or not allowed") from None


class PinnedLlmTransport(httpx.HTTPTransport):
    """Prevent user LLM URLs from reaching forbidden network destinations.

    Resolve DNS -> check every IP -> dial one checked IP.
    Keep the original HTTP Host and TLS hostname while changing the dial address.
    """

    def __init__(self, allowed_local_origins: tuple[str, ...] = ()) -> None:
        # Disable environment-derived TLS settings; the owning client also disables proxies.
        super().__init__(trust_env=False)
        self.allowed_local_origins = allowed_local_origins

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Resolve/check destination IPs, send to a checked IP, and return the HTTP response."""
        normalize_llm_url(str(request.url), self.allowed_local_origins)
        # Origin means scheme + host + port, without the API path.
        origin = f"{request.url.scheme}://{request.url.netloc.decode('ascii')}"
        # Only the server allowlist can permit private/loopback destinations.
        allow_private = origin in self.allowed_local_origins
        hostname = request.url.raw_host.decode("ascii")
        port = request.url.port or (443 if request.url.scheme == "https" else 80)
        try:
            # SOCK_STREAM requests TCP addresses; each result ends with a socket address.
            answers = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        except OSError:
            raise httpx.ConnectError(
                "LLM hostname could not be resolved", request=request
            ) from None
        addresses = []
        for answer in answers:
            # getaddrinfo result: (family, socket type, protocol, name, socket address).
            address = ipaddress.ip_address(answer[4][0])
            # Treat IPv4-mapped IPv6 as IPv4 so it cannot bypass the same address rules.
            address = getattr(address, "ipv4_mapped", None) or address
            # Metadata and unsafe address ranges stay blocked even for allowed origins.
            forbidden = (
                address.is_link_local or address.is_multicast or address.is_unspecified
                or (address.is_reserved and not address.is_loopback)
                or str(address) in {"100.100.100.200", "168.63.129.16", "fd00:ec2::254"}
            )
            permitted = address.is_global or (
                allow_private and (address.is_private or address.is_loopback)
            )
            if forbidden or not permitted:
                raise InvalidLlmUrl("LLM destination is not allowed")
            addresses.append(str(address))
        if not addresses:
            raise httpx.ConnectError("LLM hostname has no addresses", request=request)
        # The URL uses a numeric IP, so a second DNS answer cannot change the destination.
        headers = request.headers.copy()
        # HTTP still addresses the original virtual host even though TCP dials a numeric IP.
        headers["Host"] = request.url.netloc.decode("ascii")
        # TLS uses the original hostname for SNI and certificate verification.
        pinned = httpx.Request(
            request.method,
            request.url.copy_with(host=addresses[0]),
            headers=headers,
            stream=request.stream,
            extensions={**request.extensions, "sni_hostname": hostname},
        )
        return super().handle_request(pinned)


class LlmAdapter(Protocol):
    """Contract for yielding answer text from role/content message dictionaries."""

    def stream(self, messages: list[dict[str, str]]) -> Iterator[str]: ...


class OpenAICompatibleLlmAdapter:
    """Use one endpoint/model/key configuration per adapter; do not mutate a shared provider."""

    def __init__(
        self,
        provider: LlmProviderSettings,
        client: httpx.Client | None = None,
        *,
        allowed_local_origins: tuple[str, ...] = (),
    ) -> None:
        self.provider, self.client = provider, client
        self.allowed_local_origins = allowed_local_origins

    @contextmanager
    def _request_client(self):
        """Borrow an injected client or own a guarded client that closes after the call."""
        if self.client is not None:
            yield self.client
        else:
            with httpx.Client(
                transport=PinnedLlmTransport(self.allowed_local_origins),
                trust_env=False,
                follow_redirects=False,
            ) as client:
                yield client

    def _request(self, client: httpx.Client, method: str, path: str, **kwargs) -> httpx.Request:
        """Build a timed request; remove cookies and add Bearer only when a key exists."""
        headers = {"Accept": "application/json"}
        if self.provider.api_key:
            headers["Authorization"] = f"Bearer {self.provider.api_key}"
        request = client.build_request(
            method,
            f"{self.provider.base_url.rstrip('/')}{path}",
            headers=headers,
            timeout=10,
            **kwargs,
        )
        # Borrowed clients may carry Ruvie/provider cookies; none may leave this adapter.
        request.headers.pop("cookie", None)
        if not self.provider.api_key:
            request.headers.pop("authorization", None)
        return request

    def list_models(self) -> list[dict[str, str]]:
        """GET /models: {data: [{id, name?}]} -> unique {id, name} items; reject unusable results."""
        normalize_llm_url(self.provider.base_url, self.allowed_local_origins)
        try:
            with self._request_client() as client:
                response = client.send(
                    self._request(client, "GET", "/models"), follow_redirects=False
                )
                if response.status_code != 200:
                    raise LlmProviderError("LLM provider could not return models")
                payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, list):
                raise LlmProviderError("LLM provider returned an invalid model list")
            # seen deduplicates IDs; the public catalog contains only id/name fields.
            models, seen = [], set()
            for item in data:
                model_id = item.get("id") if isinstance(item, dict) else None
                if not isinstance(model_id, str) or not model_id.strip() or model_id.strip() in seen:
                    continue
                model_id = model_id.strip()
                name = item.get("name")
                models.append({
                    "id": model_id,
                    "name": name.strip() if isinstance(name, str) and name.strip() else model_id,
                })
                seen.add(model_id)
            if not models:
                raise LlmProviderError("LLM provider returned no usable models")
            return models
        except InvalidLlmUrl:
            raise
        except (httpx.HTTPError, ValueError):
            raise LlmProviderError("LLM provider could not return models") from None

    def stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        """POST /chat/completions: {model, messages, stream: true} -> delta text until [DONE]."""
        with self._request_client() as client:
            request = self._request(
                client,
                "POST",
                "/chat/completions",
                json={"model": self.provider.model, "messages": messages, "stream": True},
            )
            with closing(client.send(request, stream=True, follow_redirects=False)) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ")
                    if data == "[DONE]":
                        return
                    try:
                        content = json.loads(data)["choices"][0]["delta"].get("content")
                    except (IndexError, KeyError, TypeError, json.JSONDecodeError) as error:
                        raise ValueError("LLM provider returned an invalid stream") from error
                    if isinstance(content, str):
                        yield content


def create_llm_adapter(settings: Settings, client: httpx.Client | None = None) -> LlmAdapter:
    """Build the current server chat adapter; reject missing LLM settings."""
    if settings.llm is None:
        raise RuntimeError("LLM provider is not configured")
    return OpenAICompatibleLlmAdapter(settings.llm, client)
