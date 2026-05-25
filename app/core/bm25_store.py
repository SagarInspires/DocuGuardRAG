import re
from rank_bm25 import BM25Okapi

_bm25_index = None
_bm25_chunks = []


def tokenize(text: str) -> list[str]:
    text = text.lower()
    return re.findall(r"\b\w+\b", text)


def build_bm25_index(chunks: list[dict]) -> int:
    global _bm25_index, _bm25_chunks

    _bm25_chunks = chunks

    tokenized_corpus = [
        tokenize(chunk["text"])
        for chunk in chunks
    ]

    _bm25_index = BM25Okapi(tokenized_corpus)

    return len(chunks)


def search_bm25(query: str, top_k: int = 5) -> list[dict]:
    if _bm25_index is None:
        return []

    tokenized_query = tokenize(query)

    scores = _bm25_index.get_scores(tokenized_query)

    ranked_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )

    results = []

    for index in ranked_indices[:top_k]:
        chunk = _bm25_chunks[index].copy()
        chunk["bm25_score"] = float(scores[index])
        results.append(chunk)

    return results