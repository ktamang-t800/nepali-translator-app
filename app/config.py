import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APP_TITLE = "Nepali to English Document Translator"
APP_ICON = "📘"
APP_LAYOUT = "wide"

SUPPORTED_EXTENSIONS = [".pdf", ".docx"]
SUPPORTED_UPLOAD_TYPES = ["pdf", "docx"]

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
EXTRACTED_DIR = DATA_DIR / "extracted"
TRANSLATED_DIR = DATA_DIR / "translated"
OUTPUTS_DIR = DATA_DIR / "outputs"

MAX_FILENAME_LENGTH = 200

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "").strip()

OCR_ENABLED = True
OCR_MIN_TEXT_LENGTH = 25
OCR_LANGUAGES = "nep+eng"
OCR_DPI = 300


def ensure_directories() -> None:
    """Create required working folders if they do not already exist."""
    for folder in [DATA_DIR, UPLOADS_DIR, EXTRACTED_DIR, TRANSLATED_DIR, OUTPUTS_DIR]:
        folder.mkdir(parents=True, exist_ok=True)