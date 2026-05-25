import re
import json
import os
from typing import List, Dict

from app.core.config import settings


ACRONYM_FILE = os.path.join(settings.processed_data_dir, "acronyms.json")


def extract_acronyms_from_text(text: str) -> Dict[str, str]:
    """
    Extracts acronym definitions from text.

    Example:
    Composite Fusion Attention Transformer (CFAT)
    -> {"CFAT": "Composite Fusion Attention Transformer"}
    """

    acronym_map = {}

    pattern = r"([A-Za-z][A-Za-z\-\s]{3,100}?)\s*\(([A-Z][A-Z0-9\-]{1,15})\)"

    matches = re.findall(pattern, text)

    for full_form, acronym in matches:
        full_form = " ".join(full_form.split())
        acronym = acronym.strip()

        words = full_form.split()

        if len(words) < 2:
            continue

        if len(acronym) < 2:
            continue

        acronym_map[acronym] = full_form

    return acronym_map


def extract_acronyms_from_pages(pages: List[Dict]) -> Dict[str, str]:
    combined_text = " ".join(page["text"] for page in pages)
    return extract_acronyms_from_text(combined_text)


def load_all_acronyms() -> Dict:
    if not os.path.exists(ACRONYM_FILE):
        return {}

    with open(ACRONYM_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_document_acronyms(source: str, acronym_map: Dict[str, str]) -> None:
    os.makedirs(settings.processed_data_dir, exist_ok=True)

    all_acronyms = load_all_acronyms()
    all_acronyms[source] = acronym_map

    with open(ACRONYM_FILE, "w", encoding="utf-8") as file:
        json.dump(all_acronyms, file, indent=2, ensure_ascii=False)


def get_document_acronyms(source: str | None) -> Dict[str, str]:
    if source is None:
        return {}

    all_acronyms = load_all_acronyms()
    return all_acronyms.get(source, {})