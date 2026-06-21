from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.logging_config import setup_logging
from app.core.config import settings

setup_logging()

app = FastAPI(
    title="Ruvie API",
    description="Minimal RAG backend for Markdown files",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONT_END_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "project": "Ruvie"
    }

app.include_router(router)

@app.get("/")
def serve_ui():
    return FileResponse("app/static/index.html")
