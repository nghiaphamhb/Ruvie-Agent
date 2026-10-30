"""OpenAI-compatible embedding API.

Example HTTP request:

    POST https://embedding.example.com/v1/embeddings
    Authorization: Bearer <EMBEDDING_API_KEY>
    Content-Type: application/json

    {"input": "Cách cài plugin X?", "model": "BAAI/bge-m3"}

Example HTTP response:

    {"data": [{"embedding": [0.12, -0.08, ...]}]}
"""

import math
from typing import Protocol

import httpx

from ruvie.config import EmbeddingProfile, EmbeddingProviderSettings, LlmProviderSettings, Settings
from ruvie.adapters.llm import OpenAICompatibleLlmAdapter, normalize_llm_url


class QueryEmbedder(Protocol):
    """Contract for converting one query string into a numeric search vector."""

    def embed_query(self, query: str) -> list[float]: ...


class OpenAICompatibleQueryEmbedder:
    """Use server-owned endpoint/key and the pinned embedding profile."""

    def __init__(
        self,
        provider: EmbeddingProviderSettings,
        profile: EmbeddingProfile,
        client: httpx.Client | None = None,
        *, allowed_local_origins: tuple[str, ...] = (), proxy_url: str | None = None,
    ) -> None:
        self.provider, self.profile, self.client = provider, profile, client
        self.transport = OpenAICompatibleLlmAdapter(
            LlmProviderSettings(provider.base_url, api_key=provider.api_key), client,
            allowed_local_origins=allowed_local_origins, proxy_url=proxy_url)

    def embed_query(self, query: str) -> list[float]:
        """POST /embeddings: {input: query, model} -> vector of the pinned dimension."""
        if not query.strip():
            raise ValueError("query is required")
        response = self._post('/embeddings', {'input':query, 'model':self.profile.model_id})
        try:
            vector = response.json()['data'][0]['embedding']
            if not isinstance(vector,list) or len(vector) != self.profile.dimension:
                raise ValueError
            if any(isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) for value in vector):
                raise ValueError
            return [float(value) for value in vector]
        except (IndexError, KeyError, TypeError, ValueError):
            raise ValueError('invalid_embedding_response') from None

    def embed(self, texts: list[str]) -> list[list[float]]:
        """POST /embeddings: {input: texts, model} -> finite vectors in input order."""
        if not texts:
            return []
        if any(not text.strip() for text in texts):
            raise ValueError("embedding inputs must not be empty")
        response = self._post("/embeddings", {"input": texts, "model": self.profile.model_id})
        response.raise_for_status()
        try:
            data = response.json()["data"]
            if not isinstance(data, list) or len(data) != len(texts):
                raise ValueError
            if any("index" in item for item in data):
                if any(not isinstance(item, dict) or not isinstance(item.get("index"), int) for item in data):
                    raise ValueError
                # Providers may return vectors out of order; index maps them back to input texts.
                indexed = {item["index"]: item for item in data}
                if len(indexed) != len(texts) or set(indexed) != set(range(len(texts))):
                    raise ValueError
                data = [indexed[index] for index in range(len(texts))]
            vectors = [item["embedding"] for item in data]
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("embedding provider returned an invalid batch response") from error

        result: list[list[float]] = []
        try:
            for vector in vectors:
                if not isinstance(vector, list) or len(vector) != self.profile.dimension:
                    raise ValueError
                if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in vector):
                    raise ValueError
                values = [float(value) for value in vector]
                if any(not math.isfinite(value) for value in values):
                    raise ValueError
                result.append(values)
        except (TypeError, ValueError) as error:
            raise ValueError("embedding provider returned an invalid vector") from error
        return result

    def list_models(self) -> list[dict[str, object]]:
        """GET /embeddings/models; preserve unknown dimensions and unsupported choices."""
        response = self._send('GET', '/embeddings/models')
        payload = response.json()
        data = payload.get('data') if isinstance(payload,dict) else None
        if not isinstance(data, list):
            raise ValueError('invalid_embedding_response')
        models, seen = [], set()
        for item in data:
            if not isinstance(item, dict) or not isinstance(item.get('id'), str):
                continue
            model_id = item['id'].strip()
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            dimension = item.get('dimensions', item.get('dimension'))
            if type(dimension) is not int or dimension <= 0:
                dimension = None
            reason = ('embedding_model_unsupported' if model_id != 'baai/bge-m3'
                      else 'embedding_dimension_unsupported' if dimension not in (None, 1024) else None)
            name = item.get('name')
            models.append(dict(id=model_id, name=name if isinstance(name, str) and name else model_id,
                               dimension=dimension, supported=reason is None, reason_code=reason))
        return models

    def _send(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Reuse DNS/IP pinning, TLS, explicit proxy and cookie stripping from F016."""
        normalize_llm_url(self.provider.base_url, self.transport.allowed_local_origins)
        with self.transport._request_client() as client:
            response = client.send(self.transport._request(client, method, path, **kwargs), follow_redirects=False)
            response.raise_for_status()
            return response

    def _post(self, path: str, payload: dict[str, object]) -> httpx.Response:
        """POST a JSON batch without ambient proxies or redirect credential forwarding."""
        return self._send('POST', path, json=payload)


def create_query_embedder(
    settings: Settings,
    client: httpx.Client | None = None,
) -> OpenAICompatibleQueryEmbedder:
    """Build the adapter from server settings; reject a missing embedding provider."""
    if settings.embedding_provider is None:
        raise RuntimeError("embedding provider is not configured")
    return OpenAICompatibleQueryEmbedder(settings.embedding_provider, settings.embedding_profile, client)
