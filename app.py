from pathlib import Path

import streamlit as st

from app.config import APP_ICON, APP_LAYOUT, APP_TITLE, ensure_directories
from app.state import initialize_state, reset_file_state
from app.ui import (
    render_architecture_note,
    render_chunk_summary,
    render_create_chunks_button,
    render_download_button,
    render_export_docx_button,
    render_export_summary,
    render_extract_button,
    render_extraction_summary,
    render_file_summary,
    render_header,
    render_load_selected_pages_button,
    render_page_range_selector,
    render_page_range_summary,
    render_placeholder_next_steps,
    render_resume_translation_button,
    render_save_button,
    render_saved_file_summary,
    render_selected_pages_summary,
    render_status_panel,
    render_translate_chunks_button,
    render_translated_summary,
    render_upload_section,
    validate_page_range,
    validate_uploaded_file,
)
from services.chunk_service import (
    build_chunk_preview,
    build_selected_text_preview,
    count_chunk_total_characters,
    count_total_characters,
    create_chunks_from_selected_pages,
    load_extracted_json,
    select_page_range,
)
from services.docx_service import (
    build_docx_preview_lines,
    extract_docx_pages,
    save_extracted_docx_result,
)
from services.export_service import export_translated_docx
from services.file_service import save_uploaded_file
from services.pdf_service import (
    build_preview_lines,
    count_weak_or_empty_pages,
    extract_pdf_pages,
    save_extracted_pdf_result,
)
from services.translation_service import (
    build_checkpoint_json_path,
    build_translated_preview,
    find_remaining_chunks,
    load_translation_checkpoint,
    merge_translated_chunks,
    save_translated_chunks,
    save_translation_checkpoint,
    translate_single_chunk,
    validate_translation_settings,
)

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout=APP_LAYOUT,
)


def clear_downstream_after_extraction() -> None:
    st.session_state["selected_start_page"] = 1
    st.session_state["selected_end_page"] = st.session_state.get("extracted_page_count", 1)
    st.session_state["page_range_confirmed"] = False
    st.session_state["selected_pages_loaded"] = False
    st.session_state["selected_page_items"] = []
    st.session_state["selected_text_preview"] = []
    st.session_state["selected_total_characters"] = 0
    st.session_state["chunks_created"] = False
    st.session_state["chunk_items"] = []
    st.session_state["chunk_preview"] = []
    st.session_state["chunk_count"] = 0
    st.session_state["chunk_total_characters"] = 0
    st.session_state["translation_started"] = False
    st.session_state["translation_completed"] = False
    st.session_state["translated_chunk_items"] = []
    st.session_state["translated_preview"] = []
    st.session_state["translated_chunk_count"] = 0
    st.session_state["translated_json_path"] = None
    st.session_state["translation_checkpoint_path"] = None
    st.session_state["translation_partial_count"] = 0
    st.session_state["weak_page_count_after_extraction"] = 0
    st.session_state["export_completed"] = False
    st.session_state["output_docx_path"] = None
    st.session_state["output_docx_name"] = None


def clear_downstream_after_page_range_change() -> None:
    st.session_state["selected_pages_loaded"] = False
    st.session_state["selected_page_items"] = []
    st.session_state["selected_text_preview"] = []
    st.session_state["selected_total_characters"] = 0
    st.session_state["chunks_created"] = False
    st.session_state["chunk_items"] = []
    st.session_state["chunk_preview"] = []
    st.session_state["chunk_count"] = 0
    st.session_state["chunk_total_characters"] = 0
    st.session_state["translation_started"] = False
    st.session_state["translation_completed"] = False
    st.session_state["translated_chunk_items"] = []
    st.session_state["translated_preview"] = []
    st.session_state["translated_chunk_count"] = 0
    st.session_state["translated_json_path"] = None
    st.session_state["translation_checkpoint_path"] = None
    st.session_state["translation_partial_count"] = 0
    st.session_state["export_completed"] = False
    st.session_state["output_docx_path"] = None
    st.session_state["output_docx_name"] = None


def load_existing_checkpoint_into_state() -> None:
    source_file_name = st.session_state.get("uploaded_file_name")
    if not source_file_name:
        return

    checkpoint_path = build_checkpoint_json_path(source_file_name)

    if not checkpoint_path.exists():
        st.session_state["translation_checkpoint_path"] = None
        st.session_state["translation_partial_count"] = 0
        return

    try:
        checkpoint_data = load_translation_checkpoint(str(checkpoint_path))
        translated_chunk_items = checkpoint_data.get("translated_chunks", [])

        st.session_state["translated_chunk_items"] = translated_chunk_items
        st.session_state["translated_preview"] = build_translated_preview(translated_chunk_items)
        st.session_state["translated_chunk_count"] = len(translated_chunk_items)
        st.session_state["translation_checkpoint_path"] = str(checkpoint_path)
        st.session_state["translation_partial_count"] = len(translated_chunk_items)
    except Exception:
        st.session_state["translation_checkpoint_path"] = None
        st.session_state["translation_partial_count"] = 0


def run_translation_flow(resume_mode: bool) -> None:
    settings_error = validate_translation_settings()

    if settings_error:
        st.session_state["error_message"] = settings_error
        return

    try:
        chunk_items = st.session_state.get("chunk_items", [])
        source_file_name = st.session_state.get("uploaded_file_name")
        start_page = st.session_state.get("selected_start_page")
        end_page = st.session_state.get("selected_end_page")

        existing_translated_items = st.session_state.get("translated_chunk_items", []) if resume_mode else []
        remaining_chunks = find_remaining_chunks(chunk_items, existing_translated_items)

        if not remaining_chunks:
            merged_items = merge_translated_chunks(existing_translated_items, [])
            translated_preview = build_translated_preview(merged_items)

            final_json_path = save_translated_chunks(
                source_file_name=source_file_name,
                start_page=start_page,
                end_page=end_page,
                translated_chunk_items=merged_items,
            )

            st.session_state["translated_chunk_items"] = merged_items
            st.session_state["translated_preview"] = translated_preview
            st.session_state["translated_chunk_count"] = len(merged_items)
            st.session_state["translated_json_path"] = str(final_json_path)
            st.session_state["translation_completed"] = True
            st.session_state["translation_partial_count"] = len(merged_items)
            st.session_state["error_message"] = None
            st.rerun()
            return

        st.session_state["translation_started"] = True

        progress_bar = st.progress(0)
        status_box = st.empty()

        total_remaining = len(remaining_chunks)
        newly_translated_items = []

        for index, chunk_item in enumerate(remaining_chunks, start=1):
            status_box.info("Translating remaining part {0} of {1}...".format(index, total_remaining))

            translated_chunk = translate_single_chunk(chunk_item)
            newly_translated_items.append(translated_chunk)

            merged_items = merge_translated_chunks(existing_translated_items, newly_translated_items)

            checkpoint_path = save_translation_checkpoint(
                source_file_name=source_file_name,
                start_page=start_page,
                end_page=end_page,
                total_chunks=len(chunk_items),
                translated_chunk_items=merged_items,
            )

            st.session_state["translated_chunk_items"] = merged_items
            st.session_state["translated_preview"] = build_translated_preview(merged_items)
            st.session_state["translated_chunk_count"] = len(merged_items)
            st.session_state["translation_checkpoint_path"] = str(checkpoint_path)
            st.session_state["translation_partial_count"] = len(merged_items)

            progress_bar.progress(index / float(total_remaining))

        final_items = merge_translated_chunks(existing_translated_items, newly_translated_items)
        translated_preview = build_translated_preview(final_items)

        final_json_path = save_translated_chunks(
            source_file_name=source_file_name,
            start_page=start_page,
            end_page=end_page,
            translated_chunk_items=final_items,
        )

        st.session_state["translated_chunk_items"] = final_items
        st.session_state["translated_preview"] = translated_preview
        st.session_state["translated_chunk_count"] = len(final_items)
        st.session_state["translated_json_path"] = str(final_json_path)
        st.session_state["translation_completed"] = True
        st.session_state["translation_partial_count"] = len(final_items)
        st.session_state["export_completed"] = False
        st.session_state["output_docx_path"] = None
        st.session_state["output_docx_name"] = None
        st.session_state["error_message"] = None

        status_box.success("All parts translated successfully.")
        st.rerun()
    except Exception as exc:
        st.session_state["error_message"] = "Translation stopped: {0}".format(exc)


def main() -> None:
    ensure_directories()
    initialize_state()

    render_header()
    render_architecture_note()
    render_status_panel()

    st.divider()

    uploaded_file = render_upload_section()

    if uploaded_file is None:
        reset_file_state()
    else:
        is_valid, error_message = validate_uploaded_file(uploaded_file)

        if not is_valid:
            reset_file_state()
            st.session_state["error_message"] = error_message
        else:
            current_name = uploaded_file.name
            previous_name = st.session_state.get("uploaded_file_name")

            if previous_name != current_name:
                reset_file_state()

            st.session_state["uploaded_file_name"] = uploaded_file.name
            st.session_state["uploaded_file_type"] = Path(uploaded_file.name).suffix.lower()
            st.session_state["upload_ready"] = True
            st.session_state["error_message"] = None

            render_file_summary(uploaded_file)

            if not st.session_state.get("file_saved"):
                if render_save_button():
                    try:
                        saved_path = save_uploaded_file(uploaded_file)
                        st.session_state["uploaded_file_path"] = str(saved_path)
                        st.session_state["file_saved"] = True
                        st.rerun()
                    except Exception as exc:
                        st.session_state["error_message"] = "Failed to save file: {0}".format(exc)
            else:
                render_saved_file_summary()

    if not st.session_state.get("file_saved"):
        st.divider()
        render_placeholder_next_steps()
        return

    file_type = st.session_state.get("uploaded_file_type")
    saved_file_path = st.session_state.get("uploaded_file_path")

    st.divider()

    if not st.session_state.get("extraction_completed"):
        if render_extract_button(file_type):
            try:
                if file_type == ".pdf":
                    extracted_document = extract_pdf_pages(saved_file_path)
                    extracted_json_path = save_extracted_pdf_result(extracted_document)
                    preview_lines = build_preview_lines(extracted_document)
                    weak_page_count = count_weak_or_empty_pages(extracted_document)
                    st.session_state["weak_page_count_after_extraction"] = weak_page_count
                elif file_type == ".docx":
                    extracted_document = extract_docx_pages(saved_file_path)
                    extracted_json_path = save_extracted_docx_result(extracted_document)
                    preview_lines = build_docx_preview_lines(extracted_document)
                    st.session_state["weak_page_count_after_extraction"] = 0
                else:
                    raise ValueError("Unsupported file type for extraction: {0}".format(file_type))

                st.session_state["extraction_completed"] = True
                st.session_state["extracted_json_path"] = str(extracted_json_path)
                st.session_state["extracted_page_count"] = extracted_document.total_pages
                st.session_state["extracted_preview"] = preview_lines
                clear_downstream_after_extraction()
                st.rerun()
            except Exception as exc:
                st.session_state["error_message"] = "Failed to extract document: {0}".format(exc)
        st.divider()
        render_placeholder_next_steps()
        return

    render_extraction_summary()

    st.divider()

    total_pages = st.session_state.get("extracted_page_count", 0)
    if total_pages > 0:
        start_page, end_page, confirm_clicked = render_page_range_selector(total_pages)

        if confirm_clicked:
            is_valid_range, range_error = validate_page_range(
                start_page=start_page,
                end_page=end_page,
                total_pages=total_pages,
            )

            if not is_valid_range:
                st.session_state["error_message"] = range_error
                st.session_state["page_range_confirmed"] = False
            else:
                old_start = st.session_state.get("selected_start_page")
                old_end = st.session_state.get("selected_end_page")

                st.session_state["selected_start_page"] = start_page
                st.session_state["selected_end_page"] = end_page
                st.session_state["page_range_confirmed"] = True
                st.session_state["error_message"] = None

                if old_start != start_page or old_end != end_page:
                    clear_downstream_after_page_range_change()

                st.rerun()

    if not st.session_state.get("page_range_confirmed"):
        st.divider()
        render_placeholder_next_steps()
        return

    render_page_range_summary()

    st.divider()

    if not st.session_state.get("selected_pages_loaded"):
        if render_load_selected_pages_button():
            try:
                extracted_json_path = st.session_state.get("extracted_json_path")
                selected_start_page = st.session_state.get("selected_start_page")
                selected_end_page = st.session_state.get("selected_end_page")

                extracted_data = load_extracted_json(extracted_json_path)
                selected_page_items = select_page_range(
                    extracted_data=extracted_data,
                    start_page=selected_start_page,
                    end_page=selected_end_page,
                )
                selected_text_preview = build_selected_text_preview(selected_page_items)
                selected_total_characters = count_total_characters(selected_page_items)

                clear_downstream_after_page_range_change()
                st.session_state["selected_pages_loaded"] = True
                st.session_state["selected_page_items"] = selected_page_items
                st.session_state["selected_text_preview"] = selected_text_preview
                st.session_state["selected_total_characters"] = selected_total_characters
                st.session_state["error_message"] = None
                st.rerun()
            except Exception as exc:
                st.session_state["error_message"] = "Failed to load selected pages: {0}".format(exc)
        st.divider()
        render_placeholder_next_steps()
        return

    render_selected_pages_summary()

    st.divider()

    if not st.session_state.get("chunks_created"):
        if render_create_chunks_button():
            try:
                selected_page_items = st.session_state.get("selected_page_items", [])
                chunk_items = create_chunks_from_selected_pages(
                    selected_pages=selected_page_items,
                    max_chars_per_chunk=3000,
                )
                chunk_preview = build_chunk_preview(chunk_items)
                chunk_count = len(chunk_items)
                chunk_total_characters = count_chunk_total_characters(chunk_items)

                st.session_state["chunks_created"] = True
                st.session_state["chunk_items"] = chunk_items
                st.session_state["chunk_preview"] = chunk_preview
                st.session_state["chunk_count"] = chunk_count
                st.session_state["chunk_total_characters"] = chunk_total_characters
                st.session_state["translation_started"] = False
                st.session_state["translation_completed"] = False
                st.session_state["translated_chunk_items"] = []
                st.session_state["translated_preview"] = []
                st.session_state["translated_chunk_count"] = 0
                st.session_state["translated_json_path"] = None
                st.session_state["translation_checkpoint_path"] = None
                st.session_state["translation_partial_count"] = 0
                st.session_state["export_completed"] = False
                st.session_state["output_docx_path"] = None
                st.session_state["output_docx_name"] = None
                st.session_state["error_message"] = None
                st.rerun()
            except Exception as exc:
                st.session_state["error_message"] = "Failed to create chunks: {0}".format(exc)
        st.divider()
        render_placeholder_next_steps()
        return

    load_existing_checkpoint_into_state()
    render_chunk_summary()

    st.divider()

    if not st.session_state.get("translation_completed"):
        if st.session_state.get("translation_partial_count", 0) > 0:
            if render_resume_translation_button():
                run_translation_flow(resume_mode=True)
        else:
            if render_translate_chunks_button():
                run_translation_flow(resume_mode=False)

        st.divider()
        render_placeholder_next_steps()
        return

    render_translated_summary()

    st.divider()

    if not st.session_state.get("export_completed"):
        if render_export_docx_button():
            try:
                source_file_name = st.session_state.get("uploaded_file_name")
                translated_chunk_items = st.session_state.get("translated_chunk_items", [])
                start_page = st.session_state.get("selected_start_page")
                end_page = st.session_state.get("selected_end_page")

                output_path = export_translated_docx(
                    source_file_name=source_file_name,
                    translated_chunk_items=translated_chunk_items,
                    start_page=start_page,
                    end_page=end_page,
                )

                st.session_state["export_completed"] = True
                st.session_state["output_docx_path"] = str(output_path)
                st.session_state["output_docx_name"] = Path(output_path).name
                st.session_state["error_message"] = None
                st.rerun()
            except Exception as exc:
                st.session_state["error_message"] = "Failed to export Word file: {0}".format(exc)
        st.divider()
        render_placeholder_next_steps()
        return

    render_export_summary()

    output_docx_path = st.session_state.get("output_docx_path")
    output_docx_name = st.session_state.get("output_docx_name")

    if output_docx_path and output_docx_name:
        with open(output_docx_path, "rb") as output_file:
            file_bytes = output_file.read()

        render_download_button(
            file_bytes=file_bytes,
            output_file_name=output_docx_name,
        )

    st.divider()



if __name__ == "__main__":
    main()