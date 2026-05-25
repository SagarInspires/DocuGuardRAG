from pathlib import Path
from typing import List, Dict


def parse_markdown(file_path: str) -> List[Dict]:
    """
    Reads a Markdown file and extracts text section-wise.
    Each section keeps source and section metadata.
    """

    md_path = Path(file_path)

    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {file_path}")

    with open(md_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    sections = []
    current_heading = "Document"
    current_text = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("#"):
            if current_text:
                sections.append(
                    {
                        "source": md_path.name,
                        "page": None,
                        "section": current_heading,
                        "text": " ".join(" ".join(current_text).split())
                    }
                )
                current_text = []

            current_heading = stripped.lstrip("#").strip() or "Untitled Section"
        else:
            if stripped:
                current_text.append(stripped)

    if current_text:
        sections.append(
            {
                "source": md_path.name,
                "page": None,
                "section": current_heading,
                "text": " ".join(" ".join(current_text).split())
            }
        )

    return sections