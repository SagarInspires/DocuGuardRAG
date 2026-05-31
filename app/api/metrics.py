import json
import os
from statistics import mean
from typing import Any, Dict, List

from fastapi import APIRouter

from app.core.observability import QUERY_LOG_PATH

router = APIRouter()


def load_query_logs() -> List[Dict[str, Any]]:
    if not os.path.exists(QUERY_LOG_PATH):
        return []

    logs = []

    with open(QUERY_LOG_PATH, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return logs


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0

    sorted_values = sorted(values)

    if len(sorted_values) == 1:
        return round(sorted_values[0], 3)

    index = (len(sorted_values) - 1) * (p / 100)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)

    weight = index - lower
    result = sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight

    return round(result, 3)


def avg(values: List[float]) -> float:
    if not values:
        return 0.0

    return round(mean(values), 3)


def get_latency(log: Dict[str, Any], stage: str) -> float:
    latency = log.get("latency_ms", {})
    value = latency.get(stage, 0.0)

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def get_int_value(log: Dict[str, Any], key: str) -> int:
    try:
        return int(log.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


@router.get("/summary")
def get_metrics_summary():
    logs = load_query_logs()

    if not logs:
        return {
            "message": "No query logs found yet.",
            "query_count": 0,
            "log_path": QUERY_LOG_PATH,
        }

    total_latencies = [get_latency(log, "total") for log in logs]
    retrieval_latencies = [get_latency(log, "retrieval") for log in logs]
    rerank_latencies = [get_latency(log, "rerank") for log in logs]
    llm_latencies = [get_latency(log, "llm_generation") for log in logs]

    answer_modes = {}

    for log in logs:
        mode = log.get("answer_mode", "unknown")
        answer_modes[mode] = answer_modes.get(mode, 0) + 1

    failed_logs = [
        log for log in logs
        if log.get("failure_reason") is not None
        or log.get("answer_mode") == "error"
    ]

    citation_validation_values = [
        bool(log.get("citation_validation_passed"))
        for log in logs
        if "citation_validation_passed" in log
    ]

    citation_pass_count = sum(
        1 for value in citation_validation_values
        if value
    )

    citation_validation_pass_rate = 0.0

    if citation_validation_values:
        citation_validation_pass_rate = round(
            citation_pass_count / len(citation_validation_values),
            4
        )

    citation_covered_logs = [
        log for log in logs
        if log.get("answer_mode") in {"llm", "extractive_fallback"}
        and get_int_value(log, "citation_count") > 0
    ]

    citation_coverage_rate = round(
        len(citation_covered_logs) / len(logs),
        4
    )

    source_counts = {}

    for log in logs:
        source = log.get("selected_source") or "all_documents"
        source_counts[source] = source_counts.get(source, 0) + 1

    latest_query = logs[-1]

    return {
        "query_count": len(logs),
        "latency_ms": {
            "total": {
                "avg": avg(total_latencies),
                "p50": percentile(total_latencies, 50),
                "p95": percentile(total_latencies, 95),
                "max": round(max(total_latencies), 3),
            },
            "retrieval": {
                "avg": avg(retrieval_latencies),
                "p50": percentile(retrieval_latencies, 50),
                "p95": percentile(retrieval_latencies, 95),
                "max": round(max(retrieval_latencies), 3),
            },
            "rerank": {
                "avg": avg(rerank_latencies),
                "p50": percentile(rerank_latencies, 50),
                "p95": percentile(rerank_latencies, 95),
                "max": round(max(rerank_latencies), 3),
            },
            "llm_generation": {
                "avg": avg(llm_latencies),
                "p50": percentile(llm_latencies, 50),
                "p95": percentile(llm_latencies, 95),
                "max": round(max(llm_latencies), 3),
            },
        },
        "answer_modes": answer_modes,
        "failure_rate": round(len(failed_logs) / len(logs), 4),
        "failed_query_count": len(failed_logs),
        "citation_validation_pass_rate": citation_validation_pass_rate,
        "citation_coverage_rate": citation_coverage_rate,
        "source_counts": source_counts,
        "latest_query": {
            "query_id": latest_query.get("query_id"),
            "question": latest_query.get("question"),
            "answer_mode": latest_query.get("answer_mode"),
            "total_latency_ms": get_latency(latest_query, "total"),
            "selected_source": latest_query.get("selected_source"),
            "citation_count": latest_query.get("citation_count"),
        },
        "log_path": QUERY_LOG_PATH,
    }


@router.get("/recent")
def get_recent_queries(limit: int = 10):
    logs = load_query_logs()

    if limit < 1:
        limit = 1

    if limit > 100:
        limit = 100

    recent_logs = logs[-limit:]

    return {
        "count": len(recent_logs),
        "queries": recent_logs,
    }