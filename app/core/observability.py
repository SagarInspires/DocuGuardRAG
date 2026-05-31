import json
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings


OBSERVABILITY_DIR = os.path.join(settings.processed_data_dir, "observability")
QUERY_LOG_PATH = os.path.join(OBSERVABILITY_DIR, "query_logs.jsonl")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_ms() -> float:
    return time.perf_counter() * 1000


def create_query_id() -> str:
    return f"q_{uuid.uuid4().hex[:12]}"


@contextmanager
def timed_stage(trace: Dict[str, Any], stage_name: str):
    """
    Usage:
        with timed_stage(trace, "retrieval"):
            ...
    Automatically stores latency as:
        trace["latency_ms"]["retrieval"] = 12.34
    """

    start = now_ms()

    try:
        yield
    finally:
        end = now_ms()
        latency = round(end - start, 3)

        if "latency_ms" not in trace:
            trace["latency_ms"] = {}

        trace["latency_ms"][stage_name] = latency


def safe_chunk_ids(results: Optional[List[Dict[str, Any]]]) -> List[str]:
    if not results:
        return []

    chunk_ids = []

    for item in results:
        chunk_id = item.get("chunk_id")

        if chunk_id:
            chunk_ids.append(str(chunk_id))

    return chunk_ids


def safe_sources(results: Optional[List[Dict[str, Any]]]) -> List[str]:
    if not results:
        return []

    sources = []

    for item in results:
        metadata = item.get("metadata", {})
        source = metadata.get("source")

        if source:
            sources.append(str(source))

    return sorted(set(sources))


def write_query_trace(trace: Dict[str, Any]) -> None:
    """
    Appends one query trace as JSONL.

    JSONL is production-friendly:
    - one query = one line
    - easy to parse later
    - safe for logs/dashboard/CI metrics
    """

    os.makedirs(OBSERVABILITY_DIR, exist_ok=True)

    trace = dict(trace)
    trace.setdefault("logged_at", utc_now_iso())

    with open(QUERY_LOG_PATH, "a", encoding="utf-8") as file:
        file.write(json.dumps(trace, ensure_ascii=False) + "\n")


def build_base_trace(
    question: str,
    source: Optional[str],
    retrieval_mode: str,
    top_k: int,
) -> Dict[str, Any]:
    return {
        "query_id": create_query_id(),
        "timestamp": utc_now_iso(),
        "question": question,
        "selected_source": source,
        "retrieval_mode": retrieval_mode,
        "top_k": top_k,
        "expanded_query": None,
        "retrieved_chunk_ids": [],
        "retrieved_sources": [],
        "reranked_chunk_ids": [],
        "citation_count": 0,
        "answer_mode": "unknown",
        "answer_length_chars": 0,
        "failure_reason": None,
        "latency_ms": {},
    }