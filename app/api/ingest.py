from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import shutil

from app.core.config import settings
from app.core.pdf_parser import parse_pdf
from app.core.markdown_parser import parse_markdown
from app.core.latex_parser import parse_latex
from app.core.chunking import chunk_pages
from app.core.vector_store import (
    add_chunks_to_vector_store,
    delete_document_from_vector_store,
    get_indexed_sources_from_vector_store
)
from app.core.bm25_store import build_bm25_index
from app.core.acronym_extractor import (
    extract_acronyms_from_pages,
    save_document_acronyms
)

router = APIRouter()

ALLOWED_EXTENSIONS = (".pdf", ".md", ".markdown", ".tex")


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    filename = file.filename

    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="Only PDF, Markdown, and LaTeX files are supported right now."
        )

    os.makedirs(settings.raw_data_dir, exist_ok=True)

    file_path = os.path.join(settings.raw_data_dir, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    lower_filename = filename.lower()

    if lower_filename.endswith(".pdf"):
        parsed_units = parse_pdf(file_path)
    elif lower_filename.endswith((".md", ".markdown")):
        parsed_units = parse_markdown(file_path)
    elif lower_filename.endswith(".tex"):
        parsed_units = parse_latex(file_path)
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type."
        )

    acronyms = extract_acronyms_from_pages(parsed_units)
    save_document_acronyms(filename, acronyms)

    chunks = chunk_pages(parsed_units)

    added_count = add_chunks_to_vector_store(chunks)
    bm25_count = build_bm25_index(chunks)

    return {
        "message": "File uploaded and indexed successfully",
        "filename": filename,
        "path": file_path,
        "document_units_extracted": len(parsed_units),
        "chunks_created": len(chunks),
        "chunks_indexed": added_count,
        "bm25_chunks_indexed": bm25_count,
        "acronyms_extracted": len(acronyms)
    }


@router.get("/")
def list_documents():
    indexed_sources = get_indexed_sources_from_vector_store()

    files = []

    for source in indexed_sources:
        raw_path = os.path.join(settings.raw_data_dir, source)

        files.append(
            {
                "filename": source,
                "path": raw_path if os.path.exists(raw_path) else "",
                "indexed": True
            }
        )

    return {
        "documents": files,
        "count": len(files)
    }

@router.delete("/{filename}")
def delete_document(filename: str):
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="Only PDF, Markdown, and LaTeX files are supported right now."
        )

    file_path = os.path.join(settings.raw_data_dir, filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    deleted_chunks = delete_document_from_vector_store(filename)
    os.remove(file_path)

    return {
        "message": "Document and indexed chunks deleted successfully",
        "filename": filename,
        "chunks_deleted": deleted_chunks
    }