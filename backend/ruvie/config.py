import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


# Read the repository-root .env, independent of the current working directory.
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
    """LLM endpoint with optional model/key; settings stay on the server."""
    base_url: str
    model: str = ""
    api_key: str = ""

    def __post_init__(self) -> None:
        if not self.base_url.strip():
            raise RuntimeError("LLM_BASE_URL is required when LLM settings are provided")


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
    """Validated database, provider and browser/network permissions."""
    database_url: str
    embedding_profile: EmbeddingProfile
    embedding_provider: EmbeddingProviderSettings | None
    llm: LlmProviderSettings | None
    auth_allowed_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    llm_allowed_local_origins: tuple[str, ...] = ()


def load_settings() -> Settings:
    """Read .env without overriding shell values; return validated server settings."""
    load_dotenv(ENV_FILE, override=False)
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    embedding_values = tuple(
        os.getenv(name, "").strip()
        for name in ("EMBEDDING_BASE_URL", "EMBEDDING_API_KEY")
    )
    embedding_provider = (
        EmbeddingProviderSettings(embedding_values[0].rstrip("/"), embedding_values[1])
        if any(embedding_values) else None
    )
    llm_values = tuple(
        os.getenv(name, "").strip()
        for name in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY")
    )
    llm = (
        LlmProviderSettings(llm_values[0].rstrip("/"), llm_values[1], llm_values[2])
        if any(llm_values) else None
    )
    origins = tuple(
        value.strip().rstrip("/")
        for value in os.getenv(
            "AUTH_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if value.strip()
    )
    # Exact scheme/host/port origins; an empty list denies HTTP and private destinations.
    local_origins = tuple(
        value.strip().rstrip("/")
        for value in os.getenv("LLM_ALLOWED_LOCAL_ORIGINS", "").split(",")
        if value.strip()
    )
    return Settings(
        database_url,
        EmbeddingProfile(
            os.getenv("EMBEDDING_MODEL_ID", "").strip(),
            int(os.getenv("EMBEDDING_DIMENSION", "0")),
            os.getenv("EMBEDDING_DISTANCE_METRIC", "").strip(),
        ),
        embedding_provider,
        llm,
        origins,
        local_origins,
    )
