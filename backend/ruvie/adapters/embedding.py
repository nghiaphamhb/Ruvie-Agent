"""OpenAI-compatible embedding API.

Example HTTP request:

    POST https://embedding.example.com/v1/embeddings
    Authorization: Bearer <EMBEDDING_API_KEY>
    Content-Type: application/json

    {"input": "Cách cài plugin X?", "model": "BAAI/bge-m3"}

Example HTTP response:

    {"data": [{"embedding": [0.12, -0.08, ...]}]}
"""

from typing import Protocol

import httpx

from ruvie.config import EmbeddingProfile, EmbeddingProviderSettings, Settings


class QueryEmbedder(Protocol):
    def embed_query(self, query: str) -> list[float]: ...


class OpenAICompatibleQueryEmbedder:
    def __init__(self, provider: EmbeddingProviderSettings, profile: EmbeddingProfile, client: httpx.Client | None = None) -> None:
        self.provider, self.profile, self.client = provider, profile, client

    def embed_query(self, query: str) -> list[float]:
        if not query.strip():
            raise ValueError("query is required")
        response = self._post("/embeddings", {"input": query, "model": self.profile.model_id})
        response.raise_for_status()
        try:
            vector = response.json()["data"][0]["embedding"]
        except (IndexError, KeyError, TypeError) as error:
            raise ValueError("embedding provider returned an invalid response") from error
        if not isinstance(vector, list) or len(vector) != self.profile.dimension:
            raise ValueError("embedding provider returned a vector with the wrong dimension")
        try:
            return [float(value) for value in vector]
        except (TypeError, ValueError) as error:
            raise ValueError("embedding provider returned a non-numeric vector") from error

    def _post(self, path: str, payload: dict[str, str]) -> httpx.Response:
        request = {"headers": {"Authorization": f"Bearer {self.provider.api_key}"}, "json": payload}
        if self.client:
            return self.client.post(f"{self.provider.base_url}{path}", **request)
        return httpx.post(f"{self.provider.base_url}{path}", **request)


def create_query_embedder(settings: Settings, client: httpx.Client | None = None) -> QueryEmbedder:
    if settings.embedding_provider is None:
        raise RuntimeError("embedding provider is not configured")
    return OpenAICompatibleQueryEmbedder(settings.embedding_provider, settings.embedding_profile, client)
