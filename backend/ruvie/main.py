from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI

from ruvie.adapters.embedding import create_query_embedder
from ruvie.adapters.llm import create_llm_adapter
from ruvie.api.chat import router as chat_router
from ruvie.api.documents import router as document_router
from ruvie.config import load_settings
from ruvie.database import create_database_engine, create_session_factory
from ruvie.document_upload import LocalBlobStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    engine = create_database_engine(settings.database_url)
    http_client: httpx.Client | None = None
    try:
        http_client = httpx.Client()
        app.state.settings = settings
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.http_client = http_client
        app.state.blob_store = LocalBlobStore(Path("data/uploads"))
        app.state.query_embedder = create_query_embedder(settings, http_client) if settings.embedding_provider else None
        app.state.llm_adapter = create_llm_adapter(settings, http_client) if settings.llm else None
        yield
    finally:
        try:
            if http_client is not None:
                http_client.close()
        finally:
            engine.dispose()


app = FastAPI(title="Ruvie Assistant", lifespan=lifespan)
app.include_router(chat_router)
app.include_router(document_router)


@app.get("/health")
@app.get("/ready")
def service_status() -> dict[str, str]:
    return {"status": "ok"}
