from sentence_transformers import CrossEncoder


_reranker_model = None


def get_reranker_model():
    global _reranker_model

    if _reranker_model is None:
        _reranker_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    return _reranker_model


def rerank_chunks(query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
    if not chunks:
        return []

    model = get_reranker_model()

    pairs = [
        (query, chunk["text"])
        for chunk in chunks
    ]

    scores = model.predict(pairs)

    reranked = []

    for chunk, score in zip(chunks, scores):
        updated_chunk = chunk.copy()
        updated_chunk["rerank_score"] = float(score)
        reranked.append(updated_chunk)

    reranked.sort(
        key=lambda item: item["rerank_score"],
        reverse=True
    )

    return reranked[:top_n]