import fitz
import os
from functools import lru_cache

from fastapi import HTTPException
from PIL import Image
import pytesseract
from pytesseract import TesseractNotFoundError
from pathlib import Path

MIN_TEXT_LENGTH = 30
OCR_SCALE = float(os.getenv("OCR_SCALE", "0.9"))
OCR_TIMEOUT_SECONDS = int(os.getenv("OCR_TIMEOUT_SECONDS", "5"))
OCR_REQUIRED_MESSAGE = (
    "This PDF appears to be scanned. OCR is required but Tesseract is not installed."
)
WINDOWS_TESSERACT_PATHS = [
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
]


def configure_tesseract_path() -> None:
    if pytesseract.pytesseract.tesseract_cmd != "tesseract":
        return

    for tesseract_path in WINDOWS_TESSERACT_PATHS:
        if tesseract_path.exists():
            pytesseract.pytesseract.tesseract_cmd = str(tesseract_path)
            return


@lru_cache
def get_rapid_ocr():
    from rapidocr import RapidOCR

    return RapidOCR()


def image_to_text_with_rapid_ocr(image: Image.Image) -> str:
    try:
        import numpy as np

        result = get_rapid_ocr()(np.array(image))
        return "\n".join(text for text in (result.txts or ()) if text).strip()
    except Exception as exc:
        raise RuntimeError(f"RapidOCR failed for this page: {exc}") from exc


def extract_text_with_ocr(page) -> str:
    try:
        configure_tesseract_path()
        pix = page.get_pixmap(matrix=fitz.Matrix(OCR_SCALE, OCR_SCALE), alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return pytesseract.image_to_string(image, timeout=OCR_TIMEOUT_SECONDS).strip()
    except TesseractNotFoundError:
        return image_to_text_with_rapid_ocr(image)
    except Exception as exc:
        raise RuntimeError(f"OCR failed for this page: {exc}") from exc


def extract_text_from_page(page, page_number: int) -> dict:
    text = page.get_text("text").strip()

    if text and len(text) > MIN_TEXT_LENGTH:
        return {
            "page_number": page_number,
            "text": text,
            "method": "text",
        }

    ocr_text = extract_text_with_ocr(page)

    return {
        "page_number": page_number,
        "text": ocr_text,
        "method": "ocr",
    }


def extract_text_from_pdf(file_path: str) -> dict:
    extracted_pages = []

    try:
        with fitz.open(file_path) as document:
            total_pages = document.page_count

            for page_index in range(total_pages):
                page = document.load_page(page_index)
                extracted_page = extract_text_from_page(page, page_index + 1)

                if extracted_page["text"]:
                    extracted_pages.append(extracted_page)

        return {
            "total_pages": total_pages,
            "extracted_pages": extracted_pages,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read PDF file. It may be corrupted or unreadable. Error: {exc}",
        ) from exc
