import streamlit as st


DEFAULT_STATE = {
    "uploaded_file_name": None,
    "uploaded_file_type": None,
    "uploaded_file_path": None,
    "upload_ready": False,
    "file_saved": False,
    "extraction_completed": False,
    "extracted_json_path": None,
    "extracted_page_count": 0,
    "extracted_preview": [],
    "selected_start_page": 1,
    "selected_end_page": 1,
    "page_range_confirmed": False,
    "selected_pages_loaded": False,
    "selected_page_items": [],
    "selected_text_preview": [],
    "selected_total_characters": 0,
    "chunks_created": False,
    "chunk_items": [],
    "chunk_preview": [],
    "chunk_count": 0,
    "chunk_total_characters": 0,
    "translation_started": False,
    "translation_completed": False,
    "translated_chunk_items": [],
    "translated_preview": [],
    "translated_chunk_count": 0,
    "translated_json_path": None,
    "translation_checkpoint_path": None,
    "translation_partial_count": 0,
    "export_completed": False,
    "output_docx_path": None,
    "output_docx_name": None,
    "error_message": None,
}


def initialize_state() -> None:
    """Set default Streamlit session state values once."""
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_file_state() -> None:
    """Reset file-related session values."""
    st.session_state["uploaded_file_name"] = None
    st.session_state["uploaded_file_type"] = None
    st.session_state["uploaded_file_path"] = None
    st.session_state["upload_ready"] = False
    st.session_state["file_saved"] = False
    st.session_state["extraction_completed"] = False
    st.session_state["extracted_json_path"] = None
    st.session_state["extracted_page_count"] = 0
    st.session_state["extracted_preview"] = []
    st.session_state["selected_start_page"] = 1
    st.session_state["selected_end_page"] = 1
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
    st.session_state["export_completed"] = False
    st.session_state["output_docx_path"] = None
    st.session_state["output_docx_name"] = None
    st.session_state["error_message"] = None