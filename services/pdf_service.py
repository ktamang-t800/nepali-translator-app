import json
import shutil
from pathlib import Path
from typing import Dict, List

from pypdf import PdfReader

from app.config import EXTRACTED_DIR, OCR_DPI, OCR_ENABLED, OCR_LANGUAGES, OCR_MIN_TEXT_LENGTH
from models.schemas import ExtractedDocument, ExtractedPage

try:
    import pytesseract
    from pdf2image import convert_from_path

    OCR_IMPORTS_AVAILABLE = True
except Exception:
    OCR_IMPORTS_AVAILABLE = False


def get_ocr_status() -> Dict[str, object]:
    """
    Return a simple OCR readiness summary for the UI.
    """
    tesseract_path = shutil.which("tesseract")
    pdftoppm_path = shutil.which("pdftoppm")

    return {
        "ocr_enabled": OCR_ENABLED,
        "python_packages_ready": OCR_IMPORTS_AVAILABLE,
        "tesseract_found": bool(tesseract_path),
        "tesseract_path": tesseract_path or "",
        "pdftoppm_found": bool(pdftoppm_path),
        "pdftoppm_path": pdftoppm_path or "",
        "ocr_ready": bool(
            OCR_ENABLED and OCR_IMPORTS_AVAILABLE and tesseract_path and pdftoppm_path
        ),
        "ocr_languages": OCR_LANGUAGES,
    }


def extract_pdf_pages(pdf_path: str) -> ExtractedDocument:
    """
    Extract text from a PDF file page by page.
    Uses OCR fallback only for weak/empty pages when OCR tools are available.
    """
    source_path = Path(pdf_path)
    reader = PdfReader(pdf_path)

    pages: List[ExtractedPage] = []

    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text()
        except Exception:
            text = ""

        if text is None:
            text = ""

        clean_text = text.strip()

        if should_use_ocr(clean_text):
            ocr_text = perform_ocr_for_pdf_page(pdf_path=pdf_path, page_number=index)
            if ocr_text.strip():
                clean_text = ocr_text.strip()

        pages.append(
            ExtractedPage(
                page_number=index,
                text=clean_text,
            )
        )

    return ExtractedDocument(
        source_file_name=source_path.name,
        source_file_path=str(source_path),
        file_type=".pdf",
        total_pages=len(pages),
        pages=pages,
    )


def should_use_ocr(text: str) -> bool:
    """
    Decide whether OCR fallback should run.
    """
    if not OCR_ENABLED:
        return False

    if not OCR_IMPORTS_AVAILABLE:
        return False

    status = get_ocr_status()
    if not status.get("ocr_ready"):
        return False

    if not text:
        return True

    if len(text.strip()) < OCR_MIN_TEXT_LENGTH:
        return True

    return False


def perform_ocr_for_pdf_page(pdf_path: str, page_number: int) -> str:
    """
    Render one PDF page to image and OCR it with Tesseract.
    Returns empty text if OCR dependencies are unavailable or OCR fails.
    """
    if not OCR_IMPORTS_AVAILABLE:
        return ""

    status = get_ocr_status()
    if not status.get("ocr_ready"):
        return ""

    try:
        images = convert_from_path(
            pdf_path,
            dpi=OCR_DPI,
            first_page=page_number,
            last_page=page_number,
            fmt="png",
        )

        if not images:
            return ""

        image = images[0]
        return pytesseract.image_to_string(image, lang=OCR_LANGUAGES)
    except Exception:
        return ""


def save_extracted_pdf_result(document: ExtractedDocument) -> Path:
    """
    Save extracted PDF text into a JSON file for later processing.
    """
    safe_stem = Path(document.source_file_name).stem
    output_name = "{0}_extracted.json".format(safe_stem)
    output_path = EXTRACTED_DIR / output_name

    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(document.to_dict(), json_file, ensure_ascii=False, indent=2)

    return output_path


def build_preview_lines(document: ExtractedDocument, max_pages: int = 2, max_chars: int = 500) -> List[str]:
    """
    Build a small preview of extracted text for the UI.
    """
    preview_lines: List[str] = []

    for page in document.pages[:max_pages]:
        text = page.text.strip()

        if not text:
            text = "[No extractable text found on this page]"

        if len(text) > max_chars:
            text = text[:max_chars] + "..."

        preview_lines.append("Page {0}: {1}".format(page.page_number, text))

    return preview_lines


def count_weak_or_empty_pages(document: ExtractedDocument) -> int:
    """
    Count pages that still have very weak text even after OCR fallback.
    """
    weak_count = 0

    for page in document.pages:
        text = (page.text or "").strip()
        if len(text) < OCR_MIN_TEXT_LENGTH:
            weak_count += 1

    return weak_count