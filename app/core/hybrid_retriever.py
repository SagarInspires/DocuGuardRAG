from app.core.vector_store import (
    search_vector_store,
    get_all_chunks_from_vector_store
)
from app.core.bm25_store import build_bm25_index, search_bm25


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


def hybrid_search(
    query: str,
    top_k: int = 5,
    source: str | None = None
) -> list[dict]:
    source_chunks = get_all_chunks_from_vector_store(source=source)

    if source_chunks:
        build_bm25_index(source_chunks)

    vector_results = search_vector_store(
        query=query,
        top_k=top_k,
        source=source
    )

    bm25_results = search_bm25(
        query=query,
        top_k=top_k
    )

    combined = {}

    for rank, item in enumerate(vector_results):
        chunk_id = item["chunk_id"]

        if chunk_id not in combined:
            combined[chunk_id] = item
            combined[chunk_id]["hybrid_score"] = 0.0

        combined[chunk_id]["hybrid_score"] += 1.0 / (rank + 1)

    for rank, item in enumerate(bm25_results):
        chunk_id = item["chunk_id"]

        section = item.get("section")
        if not section:
            section = infer_section_from_chunk_id(chunk_id)

        if chunk_id not in combined:
            combined[chunk_id] = {
                "chunk_id": item["chunk_id"],
                "text": item["text"],
                "metadata": {
                    "source": item["source"],
                    "page": item.get("page") if item.get("page") is not None else -1,
                    "section": section,
                    "extraction_method": item.get("extraction_method") if item.get("extraction_method") is not None else "",
                    "chunk_index": item["chunk_index"]
                },
                "distance": 999.0
            }
            combined[chunk_id]["hybrid_score"] = 0.0

        combined[chunk_id]["hybrid_score"] += 1.0 / (rank + 1)

    ranked_results = sorted(
        combined.values(),
        key=lambda x: x["hybrid_score"],
        reverse=True
    )

    return ranked_results[:top_k]