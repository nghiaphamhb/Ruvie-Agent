from fastapi import FastAPI

from ruvie.config import load_settings

settings = load_settings()
app = FastAPI(title="Ruvie Assistant")


@app.get("/health")
@app.get("/ready")
def service_status() -> dict[str, str]:
    return {"status": "ok"}
