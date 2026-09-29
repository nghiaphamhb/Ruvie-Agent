import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


@dataclass(frozen=True)
class EmbeddingProfile:
    """Server-side vector-space configuration stored with indexed revisions."""

    model_id: str
    dimension: int
    distance_metric: str

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise RuntimeError("EMBEDDING_MODEL_ID is required")
        if self.dimension != 1024:
            raise RuntimeError("EMBEDDING_DIMENSION must be 1024")
        if self.distance_metric != "cosine":
            raise RuntimeError("EMBEDDING_DISTANCE_METRIC must be cosine")


@dataclass(frozen=True)
class LlmProviderSettings:
    base_url: str
    model: str
    api_key: str

    def __post_init__(self) -> None:
        if not self.base_url or not self.model or not self.api_key:
            raise RuntimeError("LLM_BASE_URL, LLM_MODEL, and LLM_API_KEY are required together")


@dataclass(frozen=True)
class EmbeddingProviderSettings:
    """Runtime connection settings for the embedding provider."""

    base_url: str
    api_key: str

    def __post_init__(self) -> None:
        if not self.base_url or not self.api_key:
            raise RuntimeError("EMBEDDING_BASE_URL and EMBEDDING_API_KEY are required together")


@dataclass(frozen=True)
class Settings:
    database_url: str
    embedding_profile: EmbeddingProfile
    embedding_provider: EmbeddingProviderSettings | None
    llm: LlmProviderSettings | None


def load_settings() -> Settings:
    load_dotenv(ENV_FILE, override=False)
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    embedding_values = tuple(os.getenv(name, "").strip() for name in ("EMBEDDING_BASE_URL", "EMBEDDING_API_KEY"))
    embedding_provider = EmbeddingProviderSettings(embedding_values[0].rstrip("/"), embedding_values[1]) if any(embedding_values) else None
    llm_values = tuple(os.getenv(name, "").strip() for name in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"))
    llm = LlmProviderSettings(llm_values[0].rstrip("/"), llm_values[1], llm_values[2]) if any(llm_values) else None
    return Settings(database_url, EmbeddingProfile(os.getenv("EMBEDDING_MODEL_ID", "").strip(), int(os.getenv("EMBEDDING_DIMENSION", "0")), os.getenv("EMBEDDING_DISTANCE_METRIC", "").strip()), embedding_provider, llm)
