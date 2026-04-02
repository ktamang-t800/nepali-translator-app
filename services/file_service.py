import re
from datetime import datetime
from pathlib import Path

from app.config import MAX_FILENAME_LENGTH, UPLOADS_DIR


def sanitize_filename(file_name: str) -> str:
    """
    Clean the file name so it is safer to store on disk.
    Keeps letters, numbers, dots, dashes, and underscores.
    """
    cleaned_name = file_name.strip().replace(" ", "_")
    cleaned_name = re.sub(r"[^A-Za-z0-9._-]", "", cleaned_name)

    if not cleaned_name:
        cleaned_name = "uploaded_file"

    if len(cleaned_name) > MAX_FILENAME_LENGTH:
        suffix = Path(cleaned_name).suffix
        stem = Path(cleaned_name).stem[: MAX_FILENAME_LENGTH - len(suffix)]
        cleaned_name = "{0}{1}".format(stem, suffix)

    return cleaned_name


def build_unique_file_path(original_file_name: str) -> Path:
    """
    Create a unique file path using a timestamp so files do not overwrite each other.
    """
    safe_name = sanitize_filename(original_file_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = Path(safe_name).stem
    suffix = Path(safe_name).suffix

    unique_name = "{0}_{1}{2}".format(stem, timestamp, suffix)
    return UPLOADS_DIR / unique_name


def save_uploaded_file(uploaded_file) -> Path:
    """
    Save the uploaded Streamlit file to disk and return the saved path.
    """
    destination_path = build_unique_file_path(uploaded_file.name)

    with open(destination_path, "wb") as output_file:
        output_file.write(uploaded_file.getbuffer())

    return destination_path