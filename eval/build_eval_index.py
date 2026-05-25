import sys
from pathlib import Path
import csv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.core.pdf_parser import parse_pdf
from app.core.markdown_parser import parse_markdown
from app.core.latex_parser import parse_latex
from app.core.chunking import chunk_pages
from app.core.vector_store import add_chunks_to_vector_store
from app.core.bm25_store import build_bm25_index
from app.core.acronym_extractor import (
    extract_acronyms_from_pages,
    save_document_acronyms
)


ALLOWED_EXTENSIONS = (".pdf", ".md", ".markdown", ".tex")

GOLDEN_QA_PATH = PROJECT_ROOT / "data" / "eval" / "golden_qa.csv"
EVAL_DOCS_DIR = PROJECT_ROOT / "data" / "eval_docs"


def normalize(value):
    if value is None:
        return ""
    return str(value).strip()


def load_required_sources() -> set[str]:
    """
    Reads golden_qa.csv and collects unique source filenames.
    This keeps eval indexing deterministic and CI-friendly.
    """

    if not GOLDEN_QA_PATH.exists():
        raise FileNotFoundError(f"Golden QA file not found: {GOLDEN_QA_PATH}")

    sources = set()

    with open(GOLDEN_QA_PATH, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            source = normalize(row.get("source"))

            if source:
                sources.add(source)

    return sources


def parse_document(file_path: Path):
    filename = file_path.name
    lower_filename = filename.lower()

    if lower_filename.endswith(".pdf"):
        return parse_pdf(str(file_path))

    if lower_filename.endswith((".md", ".markdown")):
        return parse_markdown(str(file_path))

    if lower_filename.endswith(".tex"):
        return parse_latex(str(file_path))

    return []


def build_eval_index():
    if not EVAL_DOCS_DIR.exists():
        raise FileNotFoundError(f"Eval docs directory not found: {EVAL_DOCS_DIR}")

    required_sources = load_required_sources()

    if not required_sources:
        raise ValueError("No source files found in golden_qa.csv")

    print("Required eval sources")
    print("---------------------")
    for source in sorted(required_sources):
        print(source)

    print("\nBuilding eval index from data/eval_docs")
    print("---------------------------------------")

    all_chunks = []
    indexed_files = 0
    missing_files = []

    for source in sorted(required_sources):
        file_path = EVAL_DOCS_DIR / source

        if not file_path.exists():
            missing_files.append(source)
            print(f"Missing: {source}")
            continue

        if not file_path.name.lower().endswith(ALLOWED_EXTENSIONS):
            print(f"Skipped unsupported file: {file_path.name}")
            continue

        print(f"Indexing: {file_path.name}")

        parsed_units = parse_document(file_path)

        if not parsed_units:
            print(f"Skipped: no text extracted from {file_path.name}")
            continue

        acronyms = extract_acronyms_from_pages(parsed_units)
        save_document_acronyms(file_path.name, acronyms)

        chunks = chunk_pages(parsed_units)

        if not chunks:
            print(f"Skipped: no chunks created for {file_path.name}")
            continue

        added_count = add_chunks_to_vector_store(chunks)

        all_chunks.extend(chunks)
        indexed_files += 1

        print(
            f"Done: {file_path.name} | "
            f"units={len(parsed_units)} | "
            f"chunks={len(chunks)} | "
            f"indexed={added_count} | "
            f"acronyms={len(acronyms)}"
        )

    if missing_files:
        print("\nMissing required files")
        print("----------------------")
        for filename in missing_files:
            print(filename)

        raise SystemExit(1)

    if all_chunks:
        bm25_count = build_bm25_index(all_chunks)
    else:
        bm25_count = 0

    print("\nEval index build complete")
    print("-------------------------")
    print(f"Required files: {len(required_sources)}")
    print(f"Indexed files: {indexed_files}")
    print(f"Total chunks: {len(all_chunks)}")
    print(f"BM25 chunks indexed: {bm25_count}")


if __name__ == "__main__":
    build_eval_index()