from fastapi import FastAPI

from ruvie.config import load_settings
from ruvie.document_api import router as document_router

settings = load_settings()
app = FastAPI(title="Ruvie Assistant")
app.include_router(document_router)


@app.get("/health")
@app.get("/ready")
def service_status() -> dict[str, str]:
    return {"status": "ok"}
