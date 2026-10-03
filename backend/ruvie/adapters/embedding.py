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

    def embed(self, texts: list[str]) -> list[list[float]]:
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
                values = [float(value) for value in vector]
                if any(not math.isfinite(value) for value in values):
                    raise ValueError
                result.append(values)
        except (TypeError, ValueError) as error:
            raise ValueError("embedding provider returned an invalid vector") from error
        return result

    def _post(self, path: str, payload: dict[str, object]) -> httpx.Response:
        request = {"headers": {"Authorization": f"Bearer {self.provider.api_key}"}, "json": payload, "timeout": 60.0}
        if self.client:
            return self.client.post(f"{self.provider.base_url}{path}", **request)
        return httpx.post(f"{self.provider.base_url}{path}", **request)


def create_query_embedder(settings: Settings, client: httpx.Client | None = None) -> OpenAICompatibleQueryEmbedder:
    if settings.embedding_provider is None:
        raise RuntimeError("embedding provider is not configured")
    return OpenAICompatibleQueryEmbedder(settings.embedding_provider, settings.embedding_profile, client)
