import time

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
from app.core.observability import (
    build_base_trace,
    safe_chunk_ids,
    safe_sources,
    timed_stage,
    write_query_trace
)

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
    total_start = time.perf_counter()

    trace = build_base_trace(
        question=request.question,
        source=request.source,
        retrieval_mode=request.retrieval_mode,
        top_k=request.top_k,
    )

    try:
        candidate_k = max(request.top_k * 3, 10)

        with timed_stage(trace, "query_expansion"):
            expanded_query = expand_query_with_acronyms(
                query=request.question,
                source=request.source
            )

        trace["expanded_query"] = expanded_query

        with timed_stage(trace, "retrieval"):
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

        trace["retrieved_chunk_ids"] = safe_chunk_ids(results)
        trace["retrieved_sources"] = safe_sources(results)

        if not results:
            trace["answer_mode"] = "no_results"
            trace["failure_reason"] = "no_retrieval_results"
            trace["latency_ms"]["total"] = round(
                (time.perf_counter() - total_start) * 1000,
                3
            )
            write_query_trace(trace)

            return QueryResponse(
                answer="I could not find this in the uploaded documents.",
                citations=[],
                retrieved_chunks=[],
                answer_mode="no_results"
            )

        with timed_stage(trace, "rerank"):
            results = rerank_chunks(
                query=request.question,
                chunks=results,
                top_n=request.top_k
            )

        trace["reranked_chunk_ids"] = safe_chunk_ids(results)

        if not results:
            trace["answer_mode"] = "no_results"
            trace["failure_reason"] = "no_rerank_results"
            trace["latency_ms"]["total"] = round(
                (time.perf_counter() - total_start) * 1000,
                3
            )
            write_query_trace(trace)

            return QueryResponse(
                answer="I could not find this in the uploaded documents.",
                citations=[],
                retrieved_chunks=[],
                answer_mode="no_results"
            )

        retrieved_chunks = []
        citations = []

        with timed_stage(trace, "response_building"):
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

        with timed_stage(trace, "llm_generation"):
            answer = generate_answer(
                question=request.question,
                context=context
            )

        if is_extractive_fallback_answer(answer):
            answer_mode = "extractive_fallback"
        else:
            answer_mode = "llm"

        citation_dicts = [citation.model_dump() for citation in citations]

        with timed_stage(trace, "citation_validation"):
            is_valid = validate_answer_citations(
                answer=answer,
                citations=citation_dicts
            )

        # Do not overwrite clean Ollama answer if citation markers are not inside answer.
        # Citations are already returned separately in the UI.
        if not is_valid and not is_extractive_fallback_answer(answer):
            print(
                "[Citation validation warning] "
                "Answer did not include explicit citation markers, "
                "but answer is preserved because citations are returned separately."
            )
            answer_mode = "llm"

        trace["citation_count"] = len(citations)
        trace["answer_mode"] = answer_mode
        trace["answer_length_chars"] = len(answer or "")
        trace["citation_validation_passed"] = bool(is_valid)
        trace["failure_reason"] = None
        trace["latency_ms"]["total"] = round(
            (time.perf_counter() - total_start) * 1000,
            3
        )

        write_query_trace(trace)

        return QueryResponse(
            answer=answer,
            citations=citations,
            retrieved_chunks=retrieved_chunks,
            answer_mode=answer_mode
        )

    except Exception as error:
        trace["answer_mode"] = "error"
        trace["failure_reason"] = f"{type(error).__name__}: {error}"
        trace["latency_ms"]["total"] = round(
            (time.perf_counter() - total_start) * 1000,
            3
        )
        write_query_trace(trace)
        raise