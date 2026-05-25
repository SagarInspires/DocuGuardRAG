from typing import List, Dict
import tiktoken

from app.core.config import settings


def get_tokenizer():
    return tiktoken.get_encoding("cl100k_base")


def make_safe_location(value: str) -> str:
    """
    Makes section/page text safe for chunk_id.
    """
    return (
        value.replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace("\n", "_")
    )


def chunk_pages(pages: List[Dict]) -> List[Dict]:
    """
    Converts parsed PDF pages, Markdown sections, or LaTeX sections
    into smaller overlapping chunks.

    Supports input items like:

    PDF:
        {
            "source": "paper.pdf",
            "page": 1,
            "section": None,
            "text": "...",
            "extraction_method": "pymupdf"
        }

    Markdown / LaTeX:
        {
            "source": "README.md",
            "page": None,
            "section": "Installation",
            "text": "..."
        }
    """

    tokenizer = get_tokenizer()
    all_chunks = []

    chunk_size = settings.chunk_size
    chunk_overlap = settings.chunk_overlap

    for page in pages:
        source = page["source"]
        page_number = page.get("page")
        section = page.get("section")
        extraction_method = page.get("extraction_method", "")
        text = page["text"]

        tokens = tokenizer.encode(text)

        start = 0
        chunk_index = 0

        while start < len(tokens):
            end = start + chunk_size

            chunk_tokens = tokens[start:end]
            chunk_text = tokenizer.decode(chunk_tokens)

            if page_number is not None:
                location = f"p{page_number}"
            else:
                location = f"s{section or 'document'}"

            safe_location = make_safe_location(location)

            chunk_id = f"{source}_{safe_location}_c{chunk_index}"

            all_chunks.append(
                {
                    "chunk_id": chunk_id,
                    "source": source,
                    "page": page_number,
                    "section": section,
                    "extraction_method": extraction_method,
                    "chunk_index": chunk_index,
                    "text": chunk_text
                }
            )

            start = end - chunk_overlap
            chunk_index += 1

    return all_chunks