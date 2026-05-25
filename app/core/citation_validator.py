import re


def has_citation_marker(answer: str) -> bool:
    citation_patterns = [
        r"\[Source\s+\d+\]",
        r"\[.*?page\s+\d+.*?\]",
        r"\[\d+\]"
    ]

    for pattern in citation_patterns:
        if re.search(pattern, answer, flags=re.IGNORECASE):
            return True

    return False


def validate_answer_citations(answer: str, citations: list) -> bool:
    if "LLM generation is currently unavailable" in answer:
        return True

    if not citations:
        return False

    if not has_citation_marker(answer):
        return False

    return True