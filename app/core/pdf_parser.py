import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict
from PIL import Image
import io

from app.core.ocr import ocr_image


MIN_TEXT_LENGTH_FOR_OCR = 50


def render_page_to_image(page, zoom: float = 3.0) -> Image.Image:
    """
    Renders a PDF page into a PIL image for OCR.
    Higher zoom improves OCR quality but is slower.
    """

    matrix = fitz.Matrix(zoom, zoom)
    pixmap = page.get_pixmap(matrix=matrix)

    image_bytes = pixmap.tobytes("png")
    image = Image.open(io.BytesIO(image_bytes))

    return image


def parse_pdf(file_path: str) -> List[Dict]:
    """
    Reads a PDF file page by page and returns extracted text with metadata.

    First tries normal PyMuPDF text extraction.
    If text is too short, tries OCR fallback.
    If OCR fails, keeps PyMuPDF result and continues safely.
    """

    pdf_path = Path(file_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    document = fitz.open(file_path)
    pages = []

    for page_index, page in enumerate(document):
        text = page.get_text("text")
        text = " ".join(text.split())

        extraction_method = "pymupdf"

        if len(text) < MIN_TEXT_LENGTH_FOR_OCR:
            try:
                image = render_page_to_image(page)
                ocr_text = ocr_image(image)

                if len(ocr_text) > len(text):
                    text = ocr_text
                    extraction_method = "ocr"

            except Exception:
                extraction_method = "pymupdf_ocr_failed"

        if not text.strip():
            continue

        pages.append(
            {
                "source": pdf_path.name,
                "page": page_index + 1,
                "section": None,
                "text": text,
                "extraction_method": extraction_method
            }
        )

    document.close()

    return pages