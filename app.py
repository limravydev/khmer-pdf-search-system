# app.py
import os
import re
import unicodedata
import io
import base64

import streamlit as st
import pdfplumber  # for PDF page preview as image
from PIL import Image

# from extract_text import extract_text_from_pdf
# from search_engine import (
#     add_document,
#     search,
#     clean_missing_files,
#     get_index_stats,
#     get_document_text,
# )

from extract_text import extract_text_from_pdf
from search_engine import add_document, search

# --------------------------------------------------------
# Page config
# --------------------------------------------------------
st.set_page_config("Khmer PDF Search System", layout="wide")

# --------------------------------------------------------
# Global CSS (tabs + buttons + cards + layout)
# --------------------------------------------------------
st.markdown(
    """
    <style>
    body {
        background-color: #fafafa;
    }
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 18px;
        border-radius: 12px 12px 0 0;
        background-color: #f5f5f5;
        font-weight: 500;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #ffffff;
        border-bottom: 3px solid #ff4b4b;
    }

    /* Buttons (primary style) */
    .stButton > button, .stDownloadButton > button {
        background-color: #0d6efd;
        color: white;
        border-radius: 999px;
        border: none;
        padding: 0.45rem 1.2rem;
        font-size: 0.9rem;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background-color: #0b5ed7;
        color: white;
    }

    /* Result card */
    .result-card {
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 16px;
        border: 1px solid #ececec;
        background-color: #fafafa;
    }

    /* File list row */
    .file-row {
        padding: 6px 0;
        border-bottom: 1px solid #f0f0f0;
    }
    .file-row span.filename {
        font-size: 14px;
    }
    .file-row span.badge-current {
        display: inline-block;
        margin-left: 6px;
        padding: 2px 8px;
        font-size: 11px;
        border-radius: 999px;
        background-color: #e0f2fe;
        color: #0369a1;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------
# Session state
# --------------------------------------------------------
defaults = {
    "current_text": "",
    "current_filename": None,
    "current_pdf_path": None,
    "search_results": [],
    "search_query": "",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# --------------------------------------------------------
# Helper functions
# --------------------------------------------------------
def normalize_khmer(text: str) -> str:
    """Normalize Khmer text to improve matching."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[\u200b\u200c\u200d]", "", text)
    return text


def make_snippet(text: str, query: str, window: int = 180) -> str:
    """Return a short snippet around the first match of query."""
    if not text:
        return ""
    if not query.strip():
        return text[: window * 2]

    idx = text.find(query)
    if idx == -1:
        return text[: window * 2]

    start = max(0, idx - window)
    end = min(len(text), idx + window)
    return text[start:end]


def highlight(text: str, query: str) -> str:
    """Highlight query inside text using simple HTML span."""
    if not query.strip():
        return text

    pattern = re.escape(query)

    def repl(m):
        return f"<span style='background-color:#fff3bf'>{m.group(0)}</span>"

    return re.sub(pattern, repl, text)


# --------------------------------------------------------
# Clean index + compute stats
# --------------------------------------------------------
# clean_missing_files()

# Count PDFs in folder
if os.path.exists("pdf_storage"):
    pdf_files = [
        f for f in os.listdir("pdf_storage")
        if f.lower().endswith(".pdf")
    ]
else:
    pdf_files = []

# stats = get_index_stats(pdf_dir="pdf_storage")

# --------------------------------------------------------
# Title + Stats bar + Tabs
# --------------------------------------------------------
st.title("Khmer PDF Search System")
st.caption("Upload Khmer PDFs, run OCR, and search them by keyword (Khmer or English).")

with st.container():
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Uploaded PDFs", len(pdf_files))
    # col_b.metric("Indexed documents", stats["indexed_docs"])
    # col_c.metric("Orphan docs", stats["orphan_docs"])

st.markdown("---")

tab_upload, tab_search = st.tabs(["📄 Upload & Index", "🔍 Search"])

# ========================================================
# TAB 1: Upload & Index
# ========================================================
with tab_upload:
    st.markdown("### Step 1 · Upload PDF")
    st.write(
        "Upload a Khmer PDF. The app will run OCR, extract text, and index it "
        "so it becomes searchable immediately."
    )

    uploaded = st.file_uploader(
        "Drag and drop or browse a PDF file",
        type="pdf",
        key="uploader",
    )

    if uploaded is not None:
        os.makedirs("pdf_storage", exist_ok=True)

        pdf_path = os.path.join("pdf_storage", uploaded.name)
        with open(pdf_path, "wb") as f:
            f.write(uploaded.getbuffer())

        # Show spinner while OCR + indexing run
        with st.spinner("Running OCR and indexing this PDF..."):
            text = extract_text_from_pdf(pdf_path) or ""

            # Save to session for editor
            st.session_state.current_filename = uploaded.name
            st.session_state.current_pdf_path = pdf_path
            st.session_state.current_text = text

            # Immediately index so it is searchable
            if text.strip():
                add_document(uploaded.name, text)

        st.success(
            "PDF uploaded and indexed. You can review and edit the text below, "
            "then click **Save & index this document** again to update the index."
        )

    # ---------- Current PDF editor ----------
    if st.session_state.current_pdf_path:
        st.markdown("### Step 2 · Review and edit extracted text")

        st.info(
            f"Currently loaded file: **{st.session_state.current_filename}**"
        )

        col1, col2 = st.columns(2)

        # Left: PDF preview as image + download
        with col1:
            st.markdown("#### Original PDF (preview)")

            if st.session_state.current_pdf_path:
                try:
                    # Open PDF and render selected page as an image
                    with pdfplumber.open(st.session_state.current_pdf_path) as pdf:
                        num_pages = len(pdf.pages)

                        if num_pages > 1:
                            page_num = st.slider(
                                "Page",
                                min_value=1,
                                max_value=num_pages,
                                value=1,
                                key="pdf_preview_page",
                            )
                        else:
                            page_num = 1

                        page = pdf.pages[page_num - 1]
                        pil_img = page.to_image(resolution=150).original

                    # Convert PIL image to PNG bytes
                    buf = io.BytesIO()
                    pil_img.save(buf, format="PNG")
                    img_bytes = buf.getvalue()
                    img_b64 = base64.b64encode(img_bytes).decode()

                    # Scrollable & bordered container with the image
                    pdf_html = f"""
                    <div style="
                        border: 1px solid #ddd;
                        border-radius: 12px;
                        padding: 8px;
                        height: 700px;
                        overflow-y: auto;
                        background-color: #ffffff;
                    ">
                        <img src="data:image/png;base64,{img_b64}" style="width:100%; display:block;" />
                    </div>
                    """

                    st.markdown(pdf_html, unsafe_allow_html=True)
                    st.caption(f"Page {page_num} of {num_pages}")

                    # Download button under preview
                    with open(st.session_state.current_pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                    st.download_button(
                        label="Download PDF",
                        data=pdf_bytes,
                        file_name=st.session_state.current_filename,
                        mime="application/pdf",
                    )
                except Exception as e:
                    st.error(f"Cannot preview PDF: {e}")

        # Right: text editor + save
        with col2:
            st.markdown("#### Extracted text (OCR result)")
            st.write("You can correct OCR errors here before indexing.")

            st.session_state.current_text = st.text_area(
                "Extracted / OCR text",
                value=st.session_state.current_text,
                height=700,
            )

            if st.button("Save & index this document"):
                if st.session_state.current_text.strip():
                    with st.spinner("Updating index for this document..."):
                        add_document(
                            st.session_state.current_filename,
                            st.session_state.current_text,
                        )
                    st.success("Text updated and re-indexed.")
                else:
                    st.warning("Text is empty. Please check OCR result before saving.")

    # ---------- List all uploaded PDFs ----------
    st.markdown("---")
    st.markdown("### Step 3 · Manage uploaded PDFs")

    if not os.path.exists("pdf_storage"):
        st.info("No PDFs uploaded yet.")
    else:
        files = [
            f for f in os.listdir("pdf_storage")
            if f.lower().endswith(".pdf")
        ]
        if not files:
            st.info("No PDFs uploaded yet.")
        else:
            for fname in sorted(files):
                col_a, col_b = st.columns([5, 1])
                with col_a:
                    is_current = (
                        st.session_state.current_filename == fname
                    )
                    badge_html = (
                        "<span class='badge-current'>Currently open</span>"
                        if is_current
                        else ""
                    )
                    st.markdown(
                        f"<div class='file-row'>"
                        f"<span class='filename'>📄 {fname}</span> {badge_html}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with col_b:
                    if st.button(
                        "Open", key=f"open_{fname}", disabled=is_current
                    ):
                        path = os.path.join("pdf_storage", fname)

                        # 1) Try to get text from index (fast)
                        text = get_document_text(fname)

                        # 2) Fallback OCR only if not indexed
                        if not text:
                            with st.spinner("Running OCR for this PDF..."):
                                text = extract_text_from_pdf(path) or ""
                                if text.strip():
                                    add_document(fname, text)

                        st.session_state.current_filename = fname
                        st.session_state.current_pdf_path = path
                        st.session_state.current_text = text

# ========================================================
# TAB 2: Search
# ========================================================
with tab_search:
    st.markdown("### Search indexed documents")
    st.write(
        "Type a keyword in Khmer or English. The system will search all indexed PDFs "
        "by meaning, and highlight matches when the exact text appears."
    )

    query = st.text_input(
        "Search by keyword",
        value=st.session_state.search_query,
        key="search_input",
        placeholder="e.g. ឥណទាន, loan policy, interest rate…",
    )

    col_search_btn, col_clear_btn = st.columns([1, 1])
    with col_search_btn:
        if st.button("Search", key="search_button"):
            st.session_state.search_query = query
            if query.strip():
                with st.spinner("Searching indexed documents..."):
                    raw_results = search(query)
                    q_norm = normalize_khmer(query)
                    exact = [
                        r for r in raw_results
                        if q_norm in normalize_khmer(r["text"])
                    ]
                    st.session_state.search_results = exact if exact else raw_results
            else:
                st.session_state.search_results = []
    with col_clear_btn:
        if st.button("Clear"):
            st.session_state.search_query = ""
            st.session_state.search_results = []
            query = ""

    results = st.session_state.search_results
    q = st.session_state.search_query

    st.markdown("---")

    if results:
        st.markdown("#### Results")
        q_norm = normalize_khmer(q)
        has_exact = any(q_norm in normalize_khmer(r["text"]) for r in results)
        if has_exact:
            st.caption(
                "Showing documents that contain the keyword text, ranked by semantic similarity."
            )
        else:
            st.caption(
                "No clean exact match detected. Showing most semantically similar documents."
            )

        for r in results:
            snippet_raw = make_snippet(r["text"], q)
            snippet_html = highlight(snippet_raw, q)

            st.markdown(
                f"""
                <div class="result-card">
                    <div style="font-weight:600;font-size:15px;margin-bottom:4px;">
                        📄 {r['filename']}
                    </div>
                    <div style="font-size:12px;color:#999;">
                        Score: {r['score']:.3f}
                    </div>
                    <div style="margin-top:10px;font-size:14px;line-height:1.6;">
                        {snippet_html}…
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            pdf_path = os.path.join("pdf_storage", r["filename"])

            # Buttons row
            cols_btn = st.columns([1, 1, 5])
            with cols_btn[0]:
                if os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                    st.download_button(
                        "Download PDF",
                        data=pdf_bytes,
                        file_name=r["filename"],
                        mime="application/pdf",
                        key=f"dl_{r['filename']}",
                    )
                else:
                    st.caption("PDF not found.")

            with cols_btn[1]:
                if os.path.exists(pdf_path):
                    if st.button(
                        "Open in editor", key="open_editor_" + r["filename"]
                    ):
                        # 1) Try to read from index
                        text = get_document_text(r["filename"])

                        # 2) Fallback OCR only if needed
                        if not text:
                            with st.spinner("Running OCR for this PDF..."):
                                text = extract_text_from_pdf(pdf_path) or ""
                                if text.strip():
                                    add_document(r["filename"], text)

                        st.session_state.current_filename = r["filename"]
                        st.session_state.current_pdf_path = pdf_path
                        st.session_state.current_text = text
                        st.info(
                            "Switched document. Go to the **Upload & Index** tab to review it."
                        )
                else:
                    st.caption("Missing file.")

    elif q.strip():
        st.info("No matching documents found.")