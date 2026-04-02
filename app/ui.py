from pathlib import Path
from typing import Optional, Tuple

import streamlit as st

from app.config import SUPPORTED_EXTENSIONS, SUPPORTED_UPLOAD_TYPES


def render_header() -> None:
    st.title("📘 Nepali to English Document Translator")
    st.write(
        "Upload a Nepali PDF or DOCX file, choose the page range, "
        "translate it into English, and download the result as a Word document."
    )


def render_architecture_note() -> None:
    with st.expander("What this app can do"):
        st.write(
            "- Upload PDF and DOCX documents\n"
            "- Extract text from the document\n"
            "- Translate only the page range you choose\n"
            "- Handle scanned PDFs with OCR when needed\n"
            "- Download the translated result as a Word file"
        )


def render_status_panel() -> None:
    st.subheader("Current status")

    if st.session_state.get("error_message"):
        st.error(st.session_state["error_message"])
        return

    if st.session_state.get("export_completed"):
        st.success("Your translated Word document is ready to download.")
    elif st.session_state.get("translation_completed"):
        st.success("Translation completed successfully.")
    elif st.session_state.get("translation_partial_count", 0) > 0:
        st.info("Partial translation progress is available. You can resume it.")
    elif st.session_state.get("chunks_created"):
        st.info("Your document is ready for translation.")
    elif st.session_state.get("selected_pages_loaded"):
        st.info("Selected pages are loaded and ready.")
    elif st.session_state.get("page_range_confirmed"):
        st.info("Page range confirmed.")
    elif st.session_state.get("extraction_completed"):
        st.info("Document extraction completed.")
    elif st.session_state.get("file_saved"):
        st.info("File saved successfully.")
    elif st.session_state.get("upload_ready"):
        st.info("File is valid and ready to save.")
    else:
        st.warning("Please upload a PDF or DOCX file to continue.")


def render_upload_section():
    st.subheader("Step 1 — Upload document")

    uploaded_file = st.file_uploader(
        "Choose a Nepali document",
        type=SUPPORTED_UPLOAD_TYPES,
        help="Supported file types: PDF and DOCX",
    )
    return uploaded_file


def validate_uploaded_file(uploaded_file) -> Tuple[bool, Optional[str]]:
    if uploaded_file is None:
        return False, "No file uploaded yet."

    file_name = uploaded_file.name.strip()
    if not file_name:
        return False, "Uploaded file name is empty."

    extension = Path(file_name).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        return False, "Unsupported file type: {0}".format(extension)

    return True, None


def render_file_summary(uploaded_file) -> None:
    extension = Path(uploaded_file.name).suffix.lower()

    st.write("**File name:** {0}".format(uploaded_file.name))
    st.write("**File type:** {0}".format(extension))
    st.write("**File size:** {0:,} bytes".format(uploaded_file.size))


def render_saved_file_summary() -> None:
    st.success("File uploaded and saved successfully.")


def render_save_button() -> bool:
    return st.button("Save uploaded file")


def render_extract_button(file_type: str) -> bool:
    if file_type == ".docx":
        return st.button("Extract DOCX text")
    return st.button("Extract PDF text")


def render_load_selected_pages_button() -> bool:
    return st.button("Load selected pages")


def render_create_chunks_button() -> bool:
    return st.button("Prepare translation")


def render_translate_chunks_button() -> bool:
    return st.button("Translate now")


def render_resume_translation_button() -> bool:
    return st.button("Resume translation")


def render_export_docx_button() -> bool:
    return st.button("Prepare Word download")


def render_docx_virtual_page_note() -> None:
    st.info(
        "For DOCX files, page range is based on extracted content sections, "
        "not exact Microsoft Word print pages."
    )


def render_pdf_ocr_note(weak_page_count: int) -> None:
    if weak_page_count > 0:
        st.warning(
            "Some pages may still contain unclear text because scanned documents "
            "can be harder to read accurately."
        )


def render_extraction_summary() -> None:
    extracted_page_count = st.session_state.get("extracted_page_count", 0)
    extracted_preview = st.session_state.get("extracted_preview", [])
    uploaded_file_type = st.session_state.get("uploaded_file_type")
    weak_page_count = st.session_state.get("weak_page_count_after_extraction", 0)

    st.subheader("Step 2 — Extraction result")

    if uploaded_file_type == ".docx":
        render_docx_virtual_page_note()

    if uploaded_file_type == ".pdf":
        render_pdf_ocr_note(weak_page_count)

    st.write("**Total pages available:** {0}".format(extracted_page_count))

    if extracted_preview:
        st.write("**Preview:**")
        for line in extracted_preview:
            st.write(line)


def render_page_range_selector(total_pages: int) -> Tuple[int, int, bool]:
    st.subheader("Step 3 — Select page range")

    with st.form("page_range_form"):
        col1, col2 = st.columns(2)

        with col1:
            start_page = st.number_input(
                "Start page",
                min_value=1,
                max_value=total_pages,
                value=int(st.session_state.get("selected_start_page", 1)),
                step=1,
            )

        with col2:
            end_page = st.number_input(
                "End page",
                min_value=1,
                max_value=total_pages,
                value=int(st.session_state.get("selected_end_page", total_pages)),
                step=1,
            )

        confirm_clicked = st.form_submit_button("Confirm page range")

    return int(start_page), int(end_page), confirm_clicked


def validate_page_range(start_page: int, end_page: int, total_pages: int) -> Tuple[bool, Optional[str]]:
    if start_page < 1 or end_page < 1:
        return False, "Page numbers must start from 1."

    if start_page > total_pages or end_page > total_pages:
        return False, "Selected page is outside the available page count."

    if start_page > end_page:
        return False, "Start page cannot be greater than end page."

    return True, None


def render_page_range_summary() -> None:
    start_page = st.session_state.get("selected_start_page")
    end_page = st.session_state.get("selected_end_page")

    if st.session_state.get("page_range_confirmed"):
        st.write("**Selected range:** Page {0} to Page {1}".format(start_page, end_page))


def render_selected_pages_summary() -> None:
    selected_page_items = st.session_state.get("selected_page_items", [])
    selected_text_preview = st.session_state.get("selected_text_preview", [])
    selected_total_characters = st.session_state.get("selected_total_characters", 0)

    st.subheader("Step 4 — Selected content")

    if st.session_state.get("selected_pages_loaded"):
        st.write("**Pages loaded:** {0}".format(len(selected_page_items)))
        st.write("**Text size:** {0:,} characters".format(selected_total_characters))

    if selected_text_preview:
        st.write("**Preview:**")
        for line in selected_text_preview:
            st.write(line)


def render_chunk_summary() -> None:
    chunk_count = st.session_state.get("chunk_count", 0)
    translation_partial_count = st.session_state.get("translation_partial_count", 0)

    st.subheader("Step 5 — Translation preparation")

    if st.session_state.get("chunks_created"):
        st.write("**Translation parts prepared:** {0}".format(chunk_count))

    if translation_partial_count > 0:
        st.write("**Already translated parts:** {0}".format(translation_partial_count))


def render_translated_summary() -> None:
    translated_chunk_count = st.session_state.get("translated_chunk_count", 0)
    translated_preview = st.session_state.get("translated_preview", [])

    st.subheader("Step 6 — Translated output")

    if st.session_state.get("translation_completed"):
        st.write("**Translated parts:** {0}".format(translated_chunk_count))

    if translated_preview:
        st.write("**Preview:**")
        for line in translated_preview:
            st.write(line)


def render_export_summary() -> None:
    output_docx_name = st.session_state.get("output_docx_name")

    st.subheader("Step 7 — Word export")

    if output_docx_name:
        st.write("Your Word file is ready.")


def render_download_button(file_bytes: bytes, output_file_name: str) -> None:
    st.download_button(
        label="Download Word file",
        data=file_bytes,
        file_name=output_file_name,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def render_placeholder_next_steps() -> None:
    st.subheader("What we can improve next")
    st.write(
        "Next, we can prepare the app for Streamlit deployment and connect "
        "deployment secrets safely."
    )