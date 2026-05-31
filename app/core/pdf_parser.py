import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image
import io

from app.core.ocr import ocr_image


MIN_TEXT_LENGTH_FOR_OCR = 50
MIN_WORDS_FOR_GOOD_TEXT_LAYER = 25


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


def normalize_text(text: str) -> str:
    return " ".join((text or "").split()).strip()


def get_page_image_count(page) -> int:
    try:
        return len(page.get_images(full=True))
    except Exception:
        return 0


def get_text_blocks(page) -> List[Dict]:
    """
    Extracts text blocks with coordinates using PyMuPDF.

    block tuple format:
    (x0, y0, x1, y1, text, block_no, block_type)
    block_type 0 = text
    """

    raw_blocks = page.get_text("blocks")
    blocks = []

    for block in raw_blocks:
        if len(block) < 7:
            continue

        x0, y0, x1, y1, text, block_no, block_type = block[:7]

        if block_type != 0:
            continue

        cleaned_text = normalize_text(text)

        if not cleaned_text:
            continue

        blocks.append(
            {
                "x0": float(x0),
                "y0": float(y0),
                "x1": float(x1),
                "y1": float(y1),
                "text": cleaned_text,
                "block_no": int(block_no),
            }
        )

    return blocks


def detect_text_quality(text: str) -> Dict:
    text = text or ""
    words = text.split()

    word_count = len(words)
    alpha_chars = sum(ch.isalpha() for ch in text)
    total_chars = max(len(text), 1)
    alpha_ratio = alpha_chars / total_chars

    text_quality_score = 0.0

    if word_count >= 80:
        text_quality_score += 0.55
    elif word_count >= 40:
        text_quality_score += 0.35
    elif word_count >= 15:
        text_quality_score += 0.15

    if alpha_ratio >= 0.65:
        text_quality_score += 0.35
    elif alpha_ratio >= 0.45:
        text_quality_score += 0.20

    text_quality_score = min(round(text_quality_score, 3), 1.0)

    return {
        "word_count": word_count,
        "alpha_ratio": round(alpha_ratio, 3),
        "text_quality_score": text_quality_score,
    }


def detect_layout_type(
    blocks: List[Dict],
    page_width: float,
    page_height: float,
    document_type: str = "auto",
    layout_mode: str = "auto",
) -> str:
    """
    Lightweight layout detector.

    It does not hardcode any document content.
    It uses block positions and user-selected parser options.

    Returns:
    default
    multi_column
    slide_layout
    report_layout
    preserve_regions
    """

    if layout_mode != "auto":
        return layout_mode

    if document_type == "slides":
        return "slide_layout"

    if document_type == "report":
        return "report_layout"

    if not blocks:
        return "default"

    block_count = len(blocks)

    # Slide-like heuristic:
    # fewer text blocks, larger visual area, likely title/bullet layout.
    if block_count <= 6 and page_width > page_height:
        return "slide_layout"

    # Multi-column heuristic:
    # text blocks appear on both left and right sides.
    mid_x = page_width / 2

    left_blocks = [
        block for block in blocks
        if (block["x0"] + block["x1"]) / 2 < mid_x
    ]

    right_blocks = [
        block for block in blocks
        if (block["x0"] + block["x1"]) / 2 >= mid_x
    ]

    if len(left_blocks) >= 2 and len(right_blocks) >= 2:
        return "multi_column"

    # Report-like heuristic:
    # many blocks, structured content.
    if block_count >= 8:
        return "report_layout"

    return "default"


def sort_blocks_default(blocks: List[Dict]) -> List[Dict]:
    return sorted(blocks, key=lambda block: (block["y0"], block["x0"]))


def sort_blocks_multi_column(blocks: List[Dict], page_width: float) -> List[Dict]:
    """
    Preserves common left-column then right-column continuation.

    This is important for:
    - two-column notes
    - research papers
    - OneNote exports
    - reports with left/right continuation
    """

    mid_x = page_width / 2

    left_blocks = []
    right_blocks = []

    for block in blocks:
        center_x = (block["x0"] + block["x1"]) / 2

        if center_x < mid_x:
            left_blocks.append(block)
        else:
            right_blocks.append(block)

    left_blocks = sorted(left_blocks, key=lambda block: (block["y0"], block["x0"]))
    right_blocks = sorted(right_blocks, key=lambda block: (block["y0"], block["x0"]))

    return left_blocks + right_blocks


def sort_blocks_slide_layout(blocks: List[Dict]) -> List[Dict]:
    """
    Slide reading order:
    top title first, then body blocks top-to-bottom and left-to-right.
    """

    return sorted(blocks, key=lambda block: (block["y0"], block["x0"]))


def sort_blocks_report_layout(blocks: List[Dict], page_width: float) -> List[Dict]:
    """
    Report layout:
    If columns exist, preserve column continuation.
    Otherwise use top-to-bottom order.
    """

    layout = detect_layout_type(
        blocks=blocks,
        page_width=page_width,
        page_height=0,
        document_type="auto",
        layout_mode="auto",
    )

    if layout == "multi_column":
        return sort_blocks_multi_column(blocks, page_width)

    return sort_blocks_default(blocks)


def build_layout_aware_text(
    blocks: List[Dict],
    page_width: float,
    page_height: float,
    document_type: str,
    layout_mode: str,
) -> Tuple[str, str]:
    """
    Converts coordinate-aware text blocks into a layout-aware text string.
    """

    detected_layout = detect_layout_type(
        blocks=blocks,
        page_width=page_width,
        page_height=page_height,
        document_type=document_type,
        layout_mode=layout_mode,
    )

    if detected_layout == "multi_column":
        ordered_blocks = sort_blocks_multi_column(blocks, page_width)
    elif detected_layout == "slide_layout":
        ordered_blocks = sort_blocks_slide_layout(blocks)
    elif detected_layout == "report_layout":
        ordered_blocks = sort_blocks_report_layout(blocks, page_width)
    elif detected_layout == "preserve_regions":
        ordered_blocks = sort_blocks_default(blocks)
    else:
        ordered_blocks = sort_blocks_default(blocks)

    text_parts = []

    for index, block in enumerate(ordered_blocks):
        if detected_layout == "preserve_regions":
            region_header = (
                f"[region {index + 1} "
                f"x0={round(block['x0'], 1)} "
                f"y0={round(block['y0'], 1)} "
                f"x1={round(block['x1'], 1)} "
                f"y1={round(block['y1'], 1)}]"
            )
            text_parts.append(f"{region_header}\n{block['text']}")
        else:
            text_parts.append(block["text"])

    return "\n\n".join(text_parts).strip(), detected_layout


def should_use_ocr(
    text: str,
    image_count: int,
    extraction_mode: str,
    document_type: str,
) -> bool:
    """
    Page-level OCR decision.

    Manual user choice comes first.
    Then auto detection decides using text quality and images.
    """

    if extraction_mode == "text_only":
        return False

    if extraction_mode == "ocr_only":
        return True

    if document_type == "scanned_pdf":
        return True

    quality = detect_text_quality(text)
    word_count = quality["word_count"]
    alpha_ratio = quality["alpha_ratio"]

    weak_text_layer = (
        len(text) < MIN_TEXT_LENGTH_FOR_OCR
        or word_count < MIN_WORDS_FOR_GOOD_TEXT_LAYER
        or alpha_ratio < 0.45
    )

    image_heavy = image_count >= 1 and word_count < 40

    if extraction_mode == "hybrid":
        return weak_text_layer or image_heavy

    # extraction_mode == auto
    return weak_text_layer or image_heavy


def should_merge_text_and_ocr(
    extraction_mode: str,
    text: str,
    ocr_text: str,
) -> bool:
    """
    In hybrid mode, keep useful text layer and OCR together if both exist.
    """

    if extraction_mode != "hybrid":
        return False

    text = normalize_text(text)
    ocr_text = normalize_text(ocr_text)

    if not text:
        return False

    if not ocr_text:
        return False

    # Merge if OCR adds substantial extra content.
    return len(ocr_text) > len(text) * 1.20


def parse_pdf(
    file_path: str,
    document_type: str = "auto",
    extraction_mode: str = "auto",
    layout_mode: str = "auto",
) -> List[Dict]:
    """
    Reads a PDF page by page and returns extracted text with metadata.

    Supports user-selected parser choices:

    document_type:
        auto | pdf | scanned_pdf | slides | report

    extraction_mode:
        auto | text_only | ocr_only | hybrid

    layout_mode:
        auto | default | multi_column | slide_layout | report_layout | preserve_regions

    Design:
    - Text-layer PDFs use coordinate-aware block ordering.
    - Scanned PDFs can force OCR.
    - Hybrid mode can combine text layer + OCR.
    - Layout metadata is stored per page.
    """

    pdf_path = Path(file_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    document = fitz.open(file_path)
    pages = []

    for page_index, page in enumerate(document):
        page_rect = page.rect
        page_width = float(page_rect.width)
        page_height = float(page_rect.height)

        image_count = get_page_image_count(page)
        blocks = get_text_blocks(page)

        layout_text, detected_layout = build_layout_aware_text(
            blocks=blocks,
            page_width=page_width,
            page_height=page_height,
            document_type=document_type,
            layout_mode=layout_mode,
        )

        plain_text = normalize_text(page.get_text("text"))
        text = layout_text if layout_text else plain_text

        extraction_method = "pymupdf_layout"

        ocr_used = False
        ocr_failed = False

        if should_use_ocr(
            text=text,
            image_count=image_count,
            extraction_mode=extraction_mode,
            document_type=document_type,
        ):
            try:
                image = render_page_to_image(page)
                ocr_text = normalize_text(ocr_image(image))

                if extraction_mode == "ocr_only" or document_type == "scanned_pdf":
                    if ocr_text:
                        text = ocr_text
                        extraction_method = "ocr_layout"
                        ocr_used = True

                elif should_merge_text_and_ocr(
                    extraction_mode=extraction_mode,
                    text=text,
                    ocr_text=ocr_text,
                ):
                    text = f"{text}\n\n[OCR extra text]\n{ocr_text}"
                    extraction_method = "hybrid_text_ocr"
                    ocr_used = True

                elif len(ocr_text) > len(text):
                    text = ocr_text
                    extraction_method = "ocr_layout"
                    ocr_used = True

            except Exception:
                ocr_failed = True

                if extraction_method == "pymupdf_layout":
                    extraction_method = "pymupdf_layout_ocr_failed"

        text = text.strip()

        if not text:
            continue

        quality = detect_text_quality(text)

        pages.append(
            {
                "source": pdf_path.name,
                "page": page_index + 1,
                "section": detected_layout,
                "text": text,
                "extraction_method": extraction_method,
                "document_type": document_type,
                "extraction_mode": extraction_mode,
                "layout_mode": layout_mode,
                "detected_layout": detected_layout,
                "ocr_used": ocr_used,
                "ocr_failed": ocr_failed,
                "image_count": image_count,
                "text_block_count": len(blocks),
                "text_quality_score": quality["text_quality_score"],
                "word_count": quality["word_count"],
                "alpha_ratio": quality["alpha_ratio"],
            }
        )

    document.close()

    return pages