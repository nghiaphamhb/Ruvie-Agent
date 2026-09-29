"""OpenAI-compatible streaming chat completion API.

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

import json
from collections.abc import Iterator
from typing import Protocol

import httpx

from ruvie.config import LlmProviderSettings, Settings


class LlmAdapter(Protocol):
    def stream(self, messages: list[dict[str, str]]) -> Iterator[str]: ...


class OpenAICompatibleLlmAdapter:
    def __init__(self, provider: LlmProviderSettings, client: httpx.Client | None = None) -> None:
        self.provider, self.client = provider, client

    def stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        if self.client:
            yield from self._stream(self.client, messages)
            return
        with httpx.Client() as client:
            yield from self._stream(client, messages)

    def _stream(self, client: httpx.Client, messages: list[dict[str, str]]) -> Iterator[str]:
        with client.stream("POST", f"{self.provider.base_url}/chat/completions", headers={"Authorization": f"Bearer {self.provider.api_key}"}, json={"model": self.provider.model, "messages": messages, "stream": True}) as response:
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
    if settings.llm is None:
        raise RuntimeError("LLM provider is not configured")
    return OpenAICompatibleLlmAdapter(settings.llm, client)
