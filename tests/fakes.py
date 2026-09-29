from collections.abc import Iterator


class FakeQueryEmbedder:
    def __init__(self, vector: list[float]) -> None:
        self.vector = vector

    def embed_query(self, query: str) -> list[float]:
        return self.vector


class FakeLlmAdapter:
    def __init__(self, deltas: list[str]) -> None:
        self.deltas = deltas

    def stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        yield from self.deltas
