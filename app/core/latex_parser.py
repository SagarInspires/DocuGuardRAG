import re
from pathlib import Path
from typing import List, Dict


def clean_latex_text(text: str) -> str:
    """
    Removes common LaTeX commands while keeping useful readable content.
    This is a simple parser for v1, not a full LaTeX compiler.
    """

    # Remove comments
    text = re.sub(r"%.*", " ", text)

    # Keep content inside common commands: \textbf{hello} -> hello
    text = re.sub(r"\\[a-zA-Z]+\*?\{([^{}]*)\}", r"\1", text)

    # Remove remaining LaTeX commands without arguments
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text)

    # Remove equation delimiters but keep equation text roughly
    text = text.replace("$", " ")
    text = text.replace("\\[", " ")
    text = text.replace("\\]", " ")
    text = text.replace("\\(", " ")
    text = text.replace("\\)", " ")

    # Remove braces
    text = text.replace("{", " ").replace("}", " ")

    # Normalize whitespace
    text = " ".join(text.split())

    return text


def parse_latex(file_path: str) -> List[Dict]:
    """
    Reads a LaTeX .tex file and extracts section-wise text.
    """

    tex_path = Path(file_path)

    if not tex_path.exists():
        raise FileNotFoundError(f"LaTeX file not found: {file_path}")

    with open(tex_path, "r", encoding="utf-8") as file:
        content = file.read()

    section_pattern = r"\\(section|subsection|subsubsection)\*?\{([^{}]+)\}"

    matches = list(re.finditer(section_pattern, content))

    sections = []

    if not matches:
        cleaned = clean_latex_text(content)

        if cleaned.strip():
            sections.append(
                {
                    "source": tex_path.name,
                    "page": None,
                    "section": "Document",
                    "text": cleaned
                }
            )

        return sections

    for index, match in enumerate(matches):
        section_title = match.group(2).strip()

        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)

        section_text = content[start:end]
        cleaned_text = clean_latex_text(section_text)

        if cleaned_text.strip():
            sections.append(
                {
                    "source": tex_path.name,
                    "page": None,
                    "section": section_title,
                    "text": cleaned_text
                }
            )

    return sections