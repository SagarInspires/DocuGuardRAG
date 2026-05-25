from fastapi import APIRouter

from app.schemas.models import (
    QueryRequest,
    QueryResponse,
    Citation,
    RetrievedChunk
)
from app.core.vector_store import search_vector_store
from app.core.context_builder import build_context_from_chunks
from app.core.generator import (
    generate_answer,
    is_extractive_fallback_answer
)
from app.core.hybrid_retriever import hybrid_search
from app.core.reranker import rerank_chunks
from app.core.citation_validator import validate_answer_citations
from app.core.query_expander import expand_query_with_acronyms

router = APIRouter()


def infer_section_from_chunk_id(chunk_id: str) -> str:
    """
    Recovers section from chunk_id like:
    test_notes.md_sHybrid_Retrieval_c0
    -> Hybrid Retrieval
    """

    if "_s" not in chunk_id:
        return ""

    try:
        section_part = chunk_id.split("_s", 1)[1]
        section_part = section_part.rsplit("_c", 1)[0]
        return section_part.replace("_", " ").strip()
    except Exception:
        return ""


@router.post("/", response_model=QueryResponse)
def ask_question(request: QueryRequest):
    candidate_k = max(request.top_k * 3, 10)

    expanded_query = expand_query_with_acronyms(
        query=request.question,
        source=request.source
    )

    if request.retrieval_mode == "hybrid":
        results = hybrid_search(
            query=expanded_query,
            top_k=candidate_k,
            source=request.source
        )
    else:
        results = search_vector_store(
            query=expanded_query,
            top_k=candidate_k,
            source=request.source
        )

    if not results:
        return QueryResponse(
            answer="I could not find this in the uploaded documents.",
            citations=[],
            retrieved_chunks=[]
        )

    results = rerank_chunks(
        query=request.question,
        chunks=results,
        top_n=request.top_k
    )

    if not results:
        return QueryResponse(
            answer="I could not find this in the uploaded documents.",
            citations=[],
            retrieved_chunks=[]
        )

    retrieved_chunks = []
    citations = []

    for item in results:
        metadata = item["metadata"]

        section = metadata.get("section")
        if not section:
            section = infer_section_from_chunk_id(item["chunk_id"])

        extraction_method = metadata.get("extraction_method")
        if extraction_method is None:
            extraction_method = ""

        retrieved_chunks.append(
            RetrievedChunk(
                chunk_id=item["chunk_id"],
                text=item["text"],
                source=metadata["source"],
                page=metadata.get("page"),
                section=section,
                extraction_method=extraction_method,
                chunk_index=metadata["chunk_index"],
                distance=item.get("distance", 999.0),
                hybrid_score=item.get("hybrid_score"),
                rerank_score=item.get("rerank_score")
            )
        )

        citations.append(
            Citation(
                source=metadata["source"],
                page=metadata.get("page"),
                chunk_id=item["chunk_id"]
            )
        )

    context = build_context_from_chunks(results)

    answer = generate_answer(
        question=request.question,
        context=context
    )

    citation_dicts = [citation.model_dump() for citation in citations]

    is_valid = validate_answer_citations(
        answer=answer,
        citations=citation_dicts
    )

    # Important:
    # If Gemini/API failed, generator.py returns an extractive fallback answer.
    # That answer is already built directly from retrieved context, so do not
    # overwrite it with the generic citation-validation error.
    if not is_valid and not is_extractive_fallback_answer(answer):
        answer = (
            "I could not generate a citation-supported answer from the retrieved evidence. "
            "Please check the retrieved_chunks field for the most relevant source passages."
        )

    return QueryResponse(
        answer=answer,
        citations=citations,
        retrieved_chunks=retrieved_chunks
    )