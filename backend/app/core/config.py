import os
from pathlib import Path 
from dotenv import load_dotenv

load_dotenv()


def _csv_env(name: str, default: str) -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_MODEL = os.getenv("LLM_MODEL")

    MARKDOWN_DIR = Path(os.getenv("MARKDOWN_DIR", "data/markdown"))
    CHROMA_DIR = Path(os.getenv("CHROMA_DIR", "chroma_db"))
    CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION")

    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL")

    APP_NAME: str = os.getenv("APP_NAME")
    APP_URL: str = os.getenv("APP_URL", "http://localhost:8000")

    FRONT_END_URL: str = os.getenv("FRONT_END_URL", "http://localhost:5173")
    FRONT_END_URLS: list[str] = _csv_env(
        "FRONT_END_URLS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    
    RAW_DOCUMENT_DIR = Path(os.getenv("RAW_DOCUMENT_DIR", "data/uploads"))
    CONVERTED_MARKDOWN_DIR = Path(os.getenv("CONVERTED_MARKDOWN_DIR", "data/markdown/converted_md"))

settings = Settings()
