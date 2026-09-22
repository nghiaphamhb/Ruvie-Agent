import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


@dataclass(frozen=True)
class EmbeddingProfile:
    model_id: str
    model_version: str
    dimension: int
    distance_metric: str

    def __post_init__(self) -> None:
        if not self.model_id.strip() or len(self.model_version) != 40 or not all(c in "0123456789abcdef" for c in self.model_version.lower()):
            raise RuntimeError("EMBEDDING_MODEL_ID and a 40-character EMBEDDING_MODEL_VERSION are required")
        if self.dimension != 1024:
            raise RuntimeError("EMBEDDING_DIMENSION must be 1024")
        if self.distance_metric != "cosine":
            raise RuntimeError("EMBEDDING_DISTANCE_METRIC must be cosine")


@dataclass(frozen=True)
class Settings:
    database_url: str
    embedding_profile: EmbeddingProfile


def load_settings() -> Settings:
    load_dotenv(ENV_FILE, override=False)
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    return Settings(database_url, EmbeddingProfile(os.getenv("EMBEDDING_MODEL_ID", "").strip(), os.getenv("EMBEDDING_MODEL_VERSION", "").strip(), int(os.getenv("EMBEDDING_DIMENSION", "0")), os.getenv("EMBEDDING_DISTANCE_METRIC", "").strip()))
