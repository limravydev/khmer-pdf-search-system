import os
import time
import re
import base64
from io import BytesIO
import datetime as dt

import streamlit as st
from pdf2image import convert_from_path
from utils import PDF_SCROLL_CSS, pages_to_html

from extract_text import extract_text_from_pdf
from search_engine import (
    add_document,
    search,
    clean_missing_files,
    get_index_stats,
    get_document_text,
    get_document_keywords
)

from style import inject_css, FILE_LIST_CSS,HIDE_STREAMLIT_STYLE,inject_production_style
st.markdown(FILE_LIST_CSS, unsafe_allow_html=True)
st.markdown(HIDE_STREAMLIT_STYLE, unsafe_allow_html=True)

import os
if os.environ.get("STREAMLIT_RUNTIME", "") == "cloud":
    inject_production_style()
    
st.markdown("""
<style>
/* Reduce spacing between buttons */
.block-container {
    padding-top: 1rem;
}

.small-col > div {
    padding-right: 0px !important;
    margin-right: 0px !important;
}

/* Make View & Download buttons smaller + closer */
button[kind="secondary"] {
    padding: 0.35rem 0.75rem !important;
    margin-right: 0.2rem !important;
}
button[kind="primary"] {
    padding: 0.35rem 0.75rem !important;
}
</style>
""", unsafe_allow_html=True)

st.title("Khmer PDF Keyword Search System")
st.caption("Upload Khmer documents, run OCR, and search by exact keyword at page level.")

st.markdown("""
<style>
.result-card {
  border:1px solid #E5E7EB;
  padding:12px 14px;
  border-radius:10px;
  margin-bottom:12px;
  background:#FFFFFF;
}
</style>
""", unsafe_allow_html=True)


st.markdown(
    """
<style>
.keyword-chip {
    display: inline-block;
    background-color: #e0f2fe; /* light blue */
    color: #0369a1; /* darker blue */
    padding: 2px 8px;
    margin: 2px 4px 2px 0;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
}
</style>
""",
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# Basic config
# -------------------------------------------------------------------
PDF_DIR = "pdf_storage"
os.makedirs(PDF_DIR, exist_ok=True)

st.set_page_config(
    page_title="Khmer PDF Keyword Search System",
    layout="wide",
)
inject_css()

# Global CSS
st.markdown(
    """
<style>
.pdf-scroll {
    max-height: 800px;
    overflow-y: auto;
    overflow-x: hidden;
    border: 1px solid #e5e5e5;
    padding: 8px;
    border-radius: 6px;
    background-color: #fafafa;
}
.pdf-scroll img {
    max-width: 100% !important;
    height: auto !important;
    display: block;
}
</style>
""",
    unsafe_allow_html=True,
)

# Clean index from missing PDF files once at start
clean_missing_files(pdf_dir=PDF_DIR)


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------

def list_pdfs() -> list:
    try:
        return sorted(
            [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
        )
    except FileNotFoundError:
        return []


def highlight_keyword(text: str, query: str) -> str:
    """
    Highlight query inside text with a yellow background.
    Case-insensitive for ASCII letters; exact substring for Khmer.
    """
    if not text or not query:
        return text

    escaped = re.escape(query)
    pattern = re.compile(escaped, flags=re.IGNORECASE)

    def repl(m: re.Match) -> str:
        s = m.group(0)
        return (
            f"<span style='background-color:#fff3b0;"
            f" padding:0 2px; border-radius:2px;'>{s}</span>"
        )

    highlighted = pattern.sub(repl, text)
    highlighted = highlighted.replace("\n", "<br>")
    return highlighted


@st.cache_resource
def load_pdf_pages(path: str):
    """Convert PDF to list of PIL images (one per page)."""
    try:
        pages = convert_from_path(path, dpi=130)
        return pages
    except Exception:
        return []
    
    
@st.dialog("Full text")
def show_full_text_dialog(fname: str):
    from search_engine import get_document_text

    full_text = get_document_text(fname) or "(No text in index)"

    # Read-only text area inside the dialog
    st.text_area(
        f"Full text of {fname}",
        full_text,
        height=500,
    )
    
    
def render_keyword_chips(keywords: list[str]) -> str:
    """
    Convert list of keywords into small rounded UI tags.
    Returns HTML string usable in st.markdown(..., unsafe_allow_html=True).
    """
    chips = []
    for kw in keywords:
        chips.append(f"<span class='keyword-chip'>{kw}</span>")
    return " ".join(chips)

# -------------------------------------------------------------------
# Sidebar: index stats
# -------------------------------------------------------------------

with st.sidebar:
    st.header("Index status")

    stats = get_index_stats(pdf_dir=PDF_DIR)
    st.metric("Indexed PDFs", stats.get("indexed_docs", 0))

    orphan_docs = stats.get("orphan_docs", []) or []
    if orphan_docs:
        st.warning(
            f"{len(orphan_docs)} indexed file(s) are missing in the "
            f"`{PDF_DIR}` folder."
        )
        if st.button("Clean missing files now"):
            clean_missing_files(pdf_dir=PDF_DIR)
            st.experimental_rerun()

    st.divider()
    st.caption(f"PDFs are stored in `{PDF_DIR}/`")


# -------------------------------------------------------------------
# Tabs
# -------------------------------------------------------------------

tab_upload, tab_search = st.tabs(["📥 Upload & Index", "🔍 Search"])


# -------------------------------------------------------------------
# Tab 1: Upload & Index
# -------------------------------------------------------------------
with tab_upload:
    st.subheader("Upload PDF and extract text with OCR")

    uploaded = st.file_uploader("Upload a PDF file", type=["pdf"], key="uploader")

    if uploaded is not None:
        # Save PDF into pdf_storage
        pdf_path = os.path.join(PDF_DIR, uploaded.name)
        with open(pdf_path, "wb") as f:
            f.write(uploaded.getbuffer())
        st.success(f"Saved PDF to `{pdf_path}`")

        # Remember current PDF path + filename in session
        st.session_state.current_pdf_path = pdf_path
        st.session_state.current_filename = uploaded.name

        col_a, _ = st.columns([1, 4])
        with col_a:
            if st.button("Run OCR and preview text", type="primary", key="btn_ocr"):
                with st.spinner("Extracting text from PDF using OCR..."):
                    text = extract_text_from_pdf(pdf_path) or ""

                st.session_state.current_text = text

    # Show preview + extracted text side by side if we have them
    if (
        "current_pdf_path" in st.session_state
        and st.session_state.get("current_pdf_path")
        and st.session_state.get("current_text")
    ):
        col_left, col_right = st.columns(2)

        # Left: PDF preview (scrollable vertical with all pages)
        with col_left:
            st.subheader("Original PDF (preview)")
            pdf_path_preview = st.session_state.current_pdf_path
            pages = load_pdf_pages(pdf_path_preview) if pdf_path_preview else []

            if pages:
                html_images = pages_to_html(pages)
                st.markdown(
                    f"<div class='pdf-scroll'>{html_images}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.info("Cannot preview this PDF (conversion failed).")

        # Right: Extracted text & index button
        with col_right:
            st.subheader("Extracted text (this PDF)")
            text_value = st.session_state.current_text

            edited_text = st.text_area(
                "Extracted OCR text (you can correct it before indexing)",
                text_value,
                height=600,
                label_visibility="collapsed",
            )
            st.session_state.current_text = edited_text

            col_i, _ = st.columns([1, 4])
            with col_i:
                if st.button(
                    "Save & index this document",
                    type="primary",
                    key="btn_index",
                ):
                    with st.spinner(
                        "Indexing pages for keyword search (page-level)..."
                    ):
                        add_document(
                            st.session_state.current_filename,
                            st.session_state.current_text,
                        )
                    st.success("Document indexed successfully ✅")

    # st.divider()
    # st.subheader("2. Indexed PDFs")

    # indexed_files = stats.get("indexed_filenames", []) or []

    # if not indexed_files:
    #     st.info("No PDFs indexed yet. Upload, extract, and index a PDF above.")
    # else:
    #     for fname in indexed_files:
    #         col1, col2, col3 = st.columns([4, 1.2, 1.5])
    #         with col1:
    #             st.write(f"📄 {fname}")
    #         with col2:
    #             if st.button("View text", key=f"view_{fname}"):
    #                 full_text = get_document_text(fname)
    #                 with st.expander(f"Full text of {fname}", expanded=False):
    #                     st.write(full_text or "(No text in index)")

    #         with col3:
    #             pdf_path = os.path.join(PDF_DIR, fname)
    #             if os.path.exists(pdf_path):
    #                 with open(pdf_path, "rb") as f:
    #                     pdf_bytes = f.read()
    #                 st.download_button(
    #                     "Download PDF",
    #                     data=pdf_bytes,
    #                     file_name=fname,
    #                     mime="application/pdf",
    #                     key=f"dl_{fname}",
    #                 )
    
    
    st.divider()
    st.subheader("PDFs File List")

    indexed_files = stats.get("indexed_filenames", []) or []

    if not indexed_files:
        st.info("No PDFs indexed yet. Upload, extract, and index a PDF above.")
    else:
        # Header row
        h1, h2, h3, h4, h5 = st.columns([0.5, 4, 1.2, 2.0, 2.5])
        with h1:
            st.markdown(" ")
        with h2:
            st.markdown("**File name**")
        with h3:
            st.markdown("**Size**")
        with h4:
            st.markdown("**Created**")
        with h5:
            st.markdown("**Actions**")

        st.markdown("---")

        for fname in indexed_files:
            pdf_path = os.path.join(PDF_DIR, fname)

            # Default values
            size_label = "—"
            created_label = "—"

            if os.path.exists(pdf_path):
                # Size in MB
                size_bytes = os.path.getsize(pdf_path)
                size_mb = size_bytes / (1024 * 1024)
                size_label = f"{size_mb:.1f} MB"

                # Created time
                ctime = os.path.getctime(pdf_path)
                created_dt = dt.datetime.fromtimestamp(ctime)
                created_label = created_dt.strftime("%Y-%m-%d %H:%M")

            # One row per file
            c_icon, c_name, c_size, c_created, c_actions = st.columns(
                [0.5, 4, 1.2, 2.0, 2.5]
            )

            with c_icon:
                st.markdown("📄")

            with c_name:
                st.markdown(f"**{fname}**")
                
                # NEW: document-level keywords
                keywords = get_document_keywords(fname, top_n=8)
                if keywords:
                    chips_html = render_keyword_chips(keywords)
                    st.markdown(chips_html, unsafe_allow_html=True)

            with c_size:
                st.caption(size_label)

            with c_created:
                st.caption(created_label)

            # with c_actions:
            #     b1, b2 = st.columns([1, 1])

            #     # View text (same behaviour as before)
            #     with b1:
            #         if st.button("View text", key=f"view_{fname}"):
            #             full_text = get_document_text(fname)
            #             with st.expander(f"Full text of {fname}", expanded=False):
            #                 st.write(full_text or "(No text in index)")

            #     # Download PDF (same behaviour as before)
            #     with b2:
            #         if os.path.exists(pdf_path):
            #             with open(pdf_path, "rb") as f:
            #                 pdf_bytes = f.read()
            #             st.download_button(
            #                 "Download",
            #                 data=pdf_bytes,
            #                 file_name=fname,
            #                 mime="application/pdf",
            #                 key=f"dl_{fname}",
            #             )
            with c_actions:
                b1, b2 = st.columns([1, 1])

                # View text -> open dialog
                with b1:
                    if st.button("📄 View text", key=f"view_{fname}"):
                        show_full_text_dialog(fname)

                # Download (keep as-is)
                with b2:
                    if os.path.exists(pdf_path):
                        with open(pdf_path, "rb") as f:
                            pdf_bytes = f.read()
                        st.download_button(
                            "⬇️ Download",
                            data=pdf_bytes,
                            file_name=fname,
                            mime="application/pdf",
                            key=f"dl_{fname}",
                        )


# -------------------------------------------------------------------
# Tab 2: Search
# -------------------------------------------------------------------
with tab_search:
    st.markdown('<div class="result-card">', unsafe_allow_html=True)
    st.subheader("Search in indexed PDFs (exact keyword, page-level)")

    query = st.text_input("Keyword to search", key="query_input")

    # Results per search
    # k = st.slider("Max results", min_value=5, max_value=50, value=20, step=5)
    k = 100

    col_search_btn, _ = st.columns([1, 5])
    with col_search_btn:
        do_search = st.button("🔍 Search", type="primary", key="btn_search")

    if do_search:
        if not query.strip():
            st.warning("Please enter a keyword to search.")
        else:
            with st.spinner("Searching pages..."):
                t0 = time.time()
                results = search(query, k=k)
                elapsed = time.time() - t0

            st.caption(f"Search time (backend): {elapsed:.3f} seconds")

            if not results:
                st.info("No pages matched your keyword.")
            else:
                st.write(f"Found **{len(results)}** matching page(s).")
                st.divider()

                for r in results:
                    filename = r.get("filename", "")
                    page = r.get("page", None)
                    title = filename
                    if page is not None:
                        title = f"{filename} — Page {page}"

                    # Header row with title and a small "Download PDF" button
                    row1_col1, row1_col2 = st.columns([4, 1.5])

                    with row1_col1:
                        st.markdown(f"### 📄 {title}")
                    with row1_col2:
                        pdf_path = os.path.join(PDF_DIR, filename)
                        if os.path.exists(pdf_path):
                            with open(pdf_path, "rb") as f:
                                pdf_bytes = f.read()
                            st.download_button(
                                "⬇️ Download PDF",
                                data=pdf_bytes,
                                file_name=filename,
                                mime="application/pdf",
                                key=f"dl_search_{filename}_{page}",
                            )

                    st.caption(f"Relevance score: {r['score']:.3f}")

                    text = r.get("text", "") or ""
                    # Make snippet around first match
                    lower = text.lower()
                    q_lower = query.lower()
                    pos = lower.find(q_lower)
                    if pos == -1:
                        # fallback: just take the first 600 chars
                        snippet = text[:600]
                    else:
                        start = max(0, pos - 80)
                        end = min(len(text), pos + len(query) + 320)
                        snippet = text[start:end]

                    # Highlight in snippet
                    snippet_marked = highlight_keyword(snippet, query)
                    st.markdown(snippet_marked, unsafe_allow_html=True)

                    # Full page text with highlight
                    full_marked = highlight_keyword(text, query)
                    with st.expander("Show full page text"):
                        st.markdown(full_marked, unsafe_allow_html=True)

                    st.markdown("---")
    st.markdown('</div>', unsafe_allow_html=True)