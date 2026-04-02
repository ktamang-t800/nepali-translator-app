import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL, TRANSLATED_DIR


def validate_translation_settings() -> str:
    """
    Validate API configuration before translation starts.
    Returns an error message string if invalid, otherwise an empty string.
    """
    if not OPENAI_API_KEY:
        return "Translation service is not configured yet."

    if not OPENAI_MODEL:
        return "Translation model is not configured yet."

    return ""


def build_translation_prompt(chunk_text: str) -> str:
    """
    Build a careful translation prompt for Nepali to English translation.
    """
    return (
        "You are a professional Nepali to English document translator.\n\n"
        "Translate the following Nepali text into clear, natural, professional English.\n\n"
        "Rules:\n"
        "1. Do not skip any content.\n"
        "2. Do not hallucinate or invent missing content.\n"
        "3. Preserve headings, paragraph flow, numbering, and structure as much as practical.\n"
        "4. If some source text is unclear, unreadable, or incomplete, mark it clearly as [Unclear in source].\n"
        "5. Keep page labels such as [Page X] exactly as they appear.\n"
        "6. Output only the English translation.\n\n"
        "Source text:\n"
        "{0}".format(chunk_text)
    )


def translate_single_chunk(chunk_item: Dict) -> Dict:
    """
    Translate one chunk using the OpenAI Responses API.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = build_translation_prompt(chunk_item.get("text", ""))

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt,
    )

    translated_text = getattr(response, "output_text", "")
    if translated_text is None:
        translated_text = ""

    return {
        "chunk_number": chunk_item.get("chunk_number"),
        "page_numbers": chunk_item.get("page_numbers", []),
        "source_text": chunk_item.get("text", ""),
        "translated_text": translated_text.strip(),
        "character_count": len(translated_text.strip()),
    }


def build_translated_preview(
    translated_chunk_items: List[Dict], max_chunks: int = 3, max_chars: int = 300
) -> List[str]:
    """
    Build a small preview of translated output.
    """
    preview_lines: List[str] = []

    for chunk in translated_chunk_items[:max_chunks]:
        translated_text = chunk.get("translated_text", "").strip()

        if len(translated_text) > max_chars:
            translated_text = translated_text[:max_chars] + "..."

        preview_lines.append(
            "Translated chunk {0} | Pages {1}: {2}".format(
                chunk.get("chunk_number"),
                chunk.get("page_numbers"),
                translated_text,
            )
        )

    return preview_lines


def build_translated_json_path(source_file_name: str) -> Path:
    """
    Build a timestamped output JSON path for translated chunk data.
    """
    safe_stem = Path(source_file_name).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = "{0}_{1}_translated_chunks.json".format(safe_stem, timestamp)
    return TRANSLATED_DIR / output_name


def build_checkpoint_json_path(source_file_name: str) -> Path:
    """
    Build a stable checkpoint JSON path for in-progress translation.
    """
    safe_stem = Path(source_file_name).stem
    output_name = "{0}_translation_checkpoint.json".format(safe_stem)
    return TRANSLATED_DIR / output_name


def save_translated_chunks(
    source_file_name: str,
    start_page: int,
    end_page: int,
    translated_chunk_items: List[Dict],
) -> Path:
    """
    Save translated chunk results to disk as JSON.
    """
    output_path = build_translated_json_path(source_file_name)

    payload = {
        "source_file_name": source_file_name,
        "start_page": start_page,
        "end_page": end_page,
        "translated_chunk_count": len(translated_chunk_items),
        "translated_chunks": translated_chunk_items,
    }

    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, ensure_ascii=False, indent=2)

    return output_path


def save_translation_checkpoint(
    source_file_name: str,
    start_page: int,
    end_page: int,
    total_chunks: int,
    translated_chunk_items: List[Dict],
) -> Path:
    """
    Save in-progress translation checkpoint after each finished chunk.
    """
    checkpoint_path = build_checkpoint_json_path(source_file_name)

    payload = {
        "source_file_name": source_file_name,
        "start_page": start_page,
        "end_page": end_page,
        "total_chunks": total_chunks,
        "completed_chunks": len(translated_chunk_items),
        "translated_chunks": translated_chunk_items,
    }

    with open(checkpoint_path, "w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, ensure_ascii=False, indent=2)

    return checkpoint_path


def load_translation_checkpoint(checkpoint_path: str) -> Dict:
    """
    Load translation checkpoint JSON from disk.
    """
    with open(checkpoint_path, "r", encoding="utf-8") as json_file:
        return json.load(json_file)


def find_remaining_chunks(chunk_items: List[Dict], translated_chunk_items: List[Dict]) -> List[Dict]:
    """
    Return only chunks that are not yet translated.
    """
    completed_numbers = set()

    for item in translated_chunk_items:
        completed_numbers.add(int(item.get("chunk_number", 0)))

    remaining_chunks = []

    for chunk in chunk_items:
        chunk_number = int(chunk.get("chunk_number", 0))
        if chunk_number not in completed_numbers:
            remaining_chunks.append(chunk)

    return remaining_chunks


def merge_translated_chunks(existing_items: List[Dict], new_items: List[Dict]) -> List[Dict]:
    """
    Merge old and new translated chunks, keeping chunk_number unique.
    """
    merged_map = {}

    for item in existing_items:
        merged_map[int(item.get("chunk_number", 0))] = item

    for item in new_items:
        merged_map[int(item.get("chunk_number", 0))] = item

    merged_items = [merged_map[key] for key in sorted(merged_map.keys())]
    return merged_items