import json
import re
from typing import Dict, List


def load_extracted_json(json_path: str) -> Dict:
    """
    Load the extracted JSON file from disk.
    """
    with open(json_path, "r", encoding="utf-8") as json_file:
        return json.load(json_file)


def select_page_range(extracted_data: Dict, start_page: int, end_page: int) -> List[Dict]:
    """
    Return only the pages that fall within the selected page range.
    """
    selected_pages: List[Dict] = []

    for page in extracted_data.get("pages", []):
        page_number = int(page.get("page_number", 0))
        if start_page <= page_number <= end_page:
            selected_pages.append(
                {
                    "page_number": page_number,
                    "text": page.get("text", "") or "",
                }
            )

    return selected_pages


def count_total_characters(selected_pages: List[Dict]) -> int:
    """
    Count total characters across all selected pages.
    """
    total_characters = 0

    for page in selected_pages:
        total_characters += len(page.get("text", ""))

    return total_characters


def build_selected_text_preview(selected_pages: List[Dict], max_pages: int = 3, max_chars: int = 400) -> List[str]:
    """
    Build a small preview of the selected page range.
    """
    preview_lines: List[str] = []

    for page in selected_pages[:max_pages]:
        text = page.get("text", "").strip()

        if not text:
            text = "[No extractable text found on this page]"

        if len(text) > max_chars:
            text = text[:max_chars] + "..."

        preview_lines.append("Page {0}: {1}".format(page.get("page_number"), text))

    return preview_lines


def split_text_into_paragraphs(text: str) -> List[str]:
    """
    Split text into paragraph-like blocks.
    """
    if not text or not text.strip():
        return []

    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = re.split(r"\n\s*\n+", normalized_text)

    cleaned_paragraphs: List[str] = []
    for paragraph in paragraphs:
        clean_paragraph = paragraph.strip()
        if clean_paragraph:
            cleaned_paragraphs.append(clean_paragraph)

    return cleaned_paragraphs


def create_chunks_from_selected_pages(
    selected_pages: List[Dict], max_chars_per_chunk: int = 3000
) -> List[Dict]:
    """
    Create safe translation chunks from selected page text.
    """
    chunks: List[Dict] = []
    chunk_index = 1

    current_chunk_parts: List[str] = []
    current_chunk_pages: List[int] = []
    current_chunk_chars = 0

    for page in selected_pages:
        page_number = int(page.get("page_number", 0))
        page_text = page.get("text", "") or ""

        paragraphs = split_text_into_paragraphs(page_text)

        if not paragraphs:
            paragraphs = ["[No extractable text found on this page]"]

        for paragraph in paragraphs:
            paragraph_text = paragraph.strip()

            if not paragraph_text:
                continue

            paragraph_with_label = "[Page {0}]\n{1}".format(page_number, paragraph_text)
            paragraph_length = len(paragraph_with_label)

            if paragraph_length > max_chars_per_chunk:
                if current_chunk_parts:
                    chunks.append(
                        {
                            "chunk_number": chunk_index,
                            "page_numbers": sorted(list(set(current_chunk_pages))),
                            "text": "\n\n".join(current_chunk_parts),
                            "character_count": current_chunk_chars,
                        }
                    )
                    chunk_index += 1
                    current_chunk_parts = []
                    current_chunk_pages = []
                    current_chunk_chars = 0

                oversized_parts = break_large_paragraph(paragraph_with_label, max_chars_per_chunk)

                for oversized_part in oversized_parts:
                    chunks.append(
                        {
                            "chunk_number": chunk_index,
                            "page_numbers": [page_number],
                            "text": oversized_part,
                            "character_count": len(oversized_part),
                        }
                    )
                    chunk_index += 1

                continue

            projected_size = current_chunk_chars + paragraph_length
            if current_chunk_parts:
                projected_size += 2

            if projected_size > max_chars_per_chunk and current_chunk_parts:
                chunks.append(
                    {
                        "chunk_number": chunk_index,
                        "page_numbers": sorted(list(set(current_chunk_pages))),
                        "text": "\n\n".join(current_chunk_parts),
                        "character_count": current_chunk_chars,
                    }
                )
                chunk_index += 1
                current_chunk_parts = []
                current_chunk_pages = []
                current_chunk_chars = 0

            current_chunk_parts.append(paragraph_with_label)
            current_chunk_pages.append(page_number)

            if current_chunk_chars == 0:
                current_chunk_chars = len(paragraph_with_label)
            else:
                current_chunk_chars += 2 + len(paragraph_with_label)

    if current_chunk_parts:
        chunks.append(
            {
                "chunk_number": chunk_index,
                "page_numbers": sorted(list(set(current_chunk_pages))),
                "text": "\n\n".join(current_chunk_parts),
                "character_count": current_chunk_chars,
            }
        )

    return chunks


def break_large_paragraph(text: str, max_chars_per_chunk: int) -> List[str]:
    """
    Break a very large paragraph into smaller pieces by sentence-like boundaries,
    then by hard character limit if needed.
    """
    sentence_parts = re.split(r"(?<=[।.!?])\s+", text.strip())
    sentence_parts = [part.strip() for part in sentence_parts if part.strip()]

    if not sentence_parts:
        return force_break_text(text, max_chars_per_chunk)

    broken_chunks: List[str] = []
    current_parts: List[str] = []
    current_chars = 0

    for sentence in sentence_parts:
        sentence_length = len(sentence)

        if sentence_length > max_chars_per_chunk:
            if current_parts:
                broken_chunks.append(" ".join(current_parts))
                current_parts = []
                current_chars = 0

            hard_parts = force_break_text(sentence, max_chars_per_chunk)
            broken_chunks.extend(hard_parts)
            continue

        projected_size = current_chars + sentence_length
        if current_parts:
            projected_size += 1

        if projected_size > max_chars_per_chunk and current_parts:
            broken_chunks.append(" ".join(current_parts))
            current_parts = [sentence]
            current_chars = sentence_length
        else:
            current_parts.append(sentence)
            if current_chars == 0:
                current_chars = sentence_length
            else:
                current_chars += 1 + sentence_length

    if current_parts:
        broken_chunks.append(" ".join(current_parts))

    return broken_chunks


def force_break_text(text: str, max_chars_per_chunk: int) -> List[str]:
    """
    Hard-break text when normal sentence splitting is not enough.
    """
    forced_parts: List[str] = []
    start_index = 0
    clean_text = text.strip()

    while start_index < len(clean_text):
        end_index = start_index + max_chars_per_chunk
        forced_parts.append(clean_text[start_index:end_index].strip())
        start_index = end_index

    return [part for part in forced_parts if part]


def build_chunk_preview(chunk_items: List[Dict], max_chunks: int = 3, max_chars: int = 300) -> List[str]:
    """
    Build a small preview of the first few chunks.
    """
    preview_lines: List[str] = []

    for chunk in chunk_items[:max_chunks]:
        chunk_text = chunk.get("text", "").strip()
        if len(chunk_text) > max_chars:
            chunk_text = chunk_text[:max_chars] + "..."

        preview_lines.append(
            "Chunk {0} | Pages {1} | {2} chars: {3}".format(
                chunk.get("chunk_number"),
                chunk.get("page_numbers"),
                chunk.get("character_count"),
                chunk_text,
            )
        )

    return preview_lines


def count_chunk_total_characters(chunk_items: List[Dict]) -> int:
    """
    Count total characters across all chunks.
    """
    total_characters = 0

    for chunk in chunk_items:
        total_characters += int(chunk.get("character_count", 0))

    return total_characters