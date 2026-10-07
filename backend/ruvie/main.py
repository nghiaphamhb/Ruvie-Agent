from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI

from ruvie.adapters.blob_storage import DEFAULT_BLOB_ROOT, LocalBlobStore
from ruvie.adapters.embedding import create_query_embedder
from ruvie.api.chat import router as chat_router
from ruvie.api.auth import router as auth_router
from ruvie.api.documents import router as document_router
from ruvie.api.projects import router as projects_router
from ruvie.api.llm import router as llm_router
from ruvie.config import load_settings
from ruvie.database import create_database_engine, create_session_factory


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create shared DB/HTTP resources at startup and release them on shutdown."""
    settings = load_settings()
    engine = create_database_engine(settings.database_url)
    http_client: httpx.Client | None = None
    try:
        http_client = httpx.Client()
        app.state.settings = settings
        app.state.engine = engine
        # Share the embedding client/factory; chat creates its own guarded provider adapter.
        app.state.session_factory = create_session_factory(engine)
        app.state.http_client = http_client
        app.state.blob_store = LocalBlobStore(DEFAULT_BLOB_ROOT)
        app.state.query_embedder = create_query_embedder(settings, http_client) if settings.embedding_provider else None
        yield
    finally:
        try:
            if http_client is not None:
                http_client.close()
        finally:
            engine.dispose()


app = FastAPI(title="Ruvie Agent", lifespan=lifespan)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(document_router)
app.include_router(projects_router)
app.include_router(llm_router)


@app.get("/health")
@app.get("/ready")
def service_status() -> dict[str, str]:
    """GET /health or /ready returns {"status": "ok"}; this is not a DB probe."""
    return {"status": "ok"}
