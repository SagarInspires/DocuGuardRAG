import sys
from pathlib import Path
import csv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.core.hybrid_retriever import hybrid_search
from app.core.reranker import rerank_chunks
from app.core.query_expander import expand_query_with_acronyms


GOLDEN_QA_PATH = PROJECT_ROOT / "data" / "eval" / "golden_qa.csv"

MIN_SOURCE_ACCURACY = 0.90
MIN_LOCATION_RECALL = 0.80


def normalize(value):
    if value is None:
        return ""
    return str(value).strip()


def split_expected_values(value: str) -> list[str]:
    """
    Supports multiple acceptable labels like:
    6|7|8
    Hybrid Retrieval|Evaluation
    """
    value = normalize(value)

    if not value:
        return []

    return [
        item.strip()
        for item in value.split("|")
        if item.strip()
    ]


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


def get_section(item: dict) -> str:
    metadata = item.get("metadata", {})
    section = normalize(metadata.get("section"))

    if section:
        return section

    return infer_section_from_chunk_id(item.get("chunk_id", ""))


def evaluate_retrieval(top_k: int = 3):
    if not GOLDEN_QA_PATH.exists():
        raise FileNotFoundError(f"Golden QA file not found: {GOLDEN_QA_PATH}")

    total_answerable = 0
    source_hits = 0
    location_hits = 0

    rows_report = []

    with open(GOLDEN_QA_PATH, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            question = normalize(row["question"])
            source = normalize(row["source"])
            expected_pages = split_expected_values(row["expected_page"])
            expected_sections = split_expected_values(row["expected_section"])
            answerable = normalize(row["answerable"]).lower()

            if answerable != "yes":
                continue

            total_answerable += 1

            expanded_query = expand_query_with_acronyms(
                query=question,
                source=source
            )

            candidates = hybrid_search(
                query=expanded_query,
                top_k=max(top_k * 3, 10),
                source=source
            )

            results = rerank_chunks(
                query=question,
                chunks=candidates,
                top_n=top_k
            )

            retrieved_sources = [
                normalize(item["metadata"].get("source"))
                for item in results
            ]

            retrieved_pages = [
                normalize(item["metadata"].get("page"))
                for item in results
            ]

            retrieved_sections = [
                get_section(item)
                for item in results
            ]

            source_hit = source in retrieved_sources

            page_hit = False
            section_hit = False

            valid_expected_pages = [
                page for page in expected_pages
                if page != "-1"
            ]

            if valid_expected_pages:
                page_hit = any(
                    page in retrieved_pages
                    for page in valid_expected_pages
                )

            if expected_sections:
                section_hit = any(
                    section in retrieved_sections
                    for section in expected_sections
                )

            location_hit = page_hit or section_hit

            if source_hit:
                source_hits += 1

            if location_hit:
                location_hits += 1

            rows_report.append(
                {
                    "id": row["id"],
                    "question": question,
                    "source_hit": source_hit,
                    "location_hit": location_hit,
                    "expected_pages": expected_pages,
                    "retrieved_pages": retrieved_pages,
                    "expected_sections": expected_sections,
                    "retrieved_sections": retrieved_sections,
                }
            )

    source_accuracy = source_hits / total_answerable if total_answerable else 0
    location_recall = location_hits / total_answerable if total_answerable else 0

    print("\nRetrieval Evaluation Results")
    print("----------------------------")
    print(f"Answerable questions: {total_answerable}")
    print(f"Source Accuracy@{top_k}: {source_accuracy:.2f}")
    print(f"Location Recall@{top_k}: {location_recall:.2f}")

    print("\nPer-question report")
    print("-------------------")

    for item in rows_report:
        print(
            f"Q{item['id']} | "
            f"source_hit={item['source_hit']} | "
            f"location_hit={item['location_hit']} | "
            f"expected_pages={item['expected_pages']} | "
            f"retrieved_pages={item['retrieved_pages']} | "
            f"expected_sections={item['expected_sections']} | "
            f"retrieved_sections={item['retrieved_sections']}"
        )

    print("\nQuality Gate")
    print("------------")

    passed = True

    if source_accuracy < MIN_SOURCE_ACCURACY:
        print(
            f"FAILED: Source Accuracy@{top_k} "
            f"{source_accuracy:.2f} is below threshold {MIN_SOURCE_ACCURACY:.2f}"
        )
        passed = False
    else:
        print(
            f"PASSED: Source Accuracy@{top_k} "
            f"{source_accuracy:.2f} >= {MIN_SOURCE_ACCURACY:.2f}"
        )

    if location_recall < MIN_LOCATION_RECALL:
        print(
            f"FAILED: Location Recall@{top_k} "
            f"{location_recall:.2f} is below threshold {MIN_LOCATION_RECALL:.2f}"
        )
        passed = False
    else:
        print(
            f"PASSED: Location Recall@{top_k} "
            f"{location_recall:.2f} >= {MIN_LOCATION_RECALL:.2f}"
        )

    if not passed:
        raise SystemExit(1)

    print("Overall: PASSED")


if __name__ == "__main__":
    evaluate_retrieval(top_k=3)