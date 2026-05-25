from fastapi import FastAPI

from app.api import ingest, query
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description="Production-grade RAG backend",
    version="0.1.0"
)

app.include_router(ingest.router, prefix="/documents", tags=["Documents"])
app.include_router(query.router, prefix="/query", tags=["Query"])


@app.get("/")
def root():
    return {
        "message": "DocuGuard RAG backend is running",
        "status": "ok"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }