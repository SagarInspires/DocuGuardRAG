from PIL import Image, ImageOps, ImageFilter
import pytesseract
import os


TESSERACT_EXE_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if os.path.exists(TESSERACT_EXE_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE_PATH


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    image = image.convert("L")
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.MedianFilter(size=3))

    image = image.point(
        lambda pixel: 255 if pixel > 165 else 0
    )

    return image


def clean_ocr_text(text: str) -> str:
    return " ".join(text.split())


def ocr_image(image: Image.Image) -> str:
    processed_image = preprocess_image_for_ocr(image)

    configs = [
        "--oem 3 --psm 6",
        "--oem 3 --psm 11",
        "--oem 3 --psm 12"
    ]

    best_text = ""

    for config in configs:
        try:
            text = pytesseract.image_to_string(
                processed_image,
                config=config
            )

            text = clean_ocr_text(text)

            if len(text) > len(best_text):
                best_text = text

        except Exception:
            continue

    return best_text