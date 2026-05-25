from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ingest, query

app = FastAPI(
    title="DocuGuard RAG API",
    description="Production-style multi-format RAG backend with hybrid retrieval, reranking, citations, and evaluation.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    ingest.router,
    prefix="/documents",
    tags=["Documents"]
)

app.include_router(
    query.router,
    prefix="/query",
    tags=["Query"]
)


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "message": "DocuGuard RAG backend is running"
    }