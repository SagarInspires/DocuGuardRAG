from pydantic import BaseModel
from typing import List, Optional

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    source: Optional[str] = None
    retrieval_mode: str = "vector"

class Citation(BaseModel):
    source: str
    page: Optional[int] = None
    chunk_id: str


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    source: str
    page: Optional[int] = None
    section: Optional[str] = None
    extraction_method: Optional[str] = None
    chunk_index: int
    distance: float
    hybrid_score: Optional[float] = None
    rerank_score: Optional[float] = None


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    retrieved_chunks: List[RetrievedChunk]