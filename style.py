import streamlit as st

# --------------------------------------------------------
#  GLOBAL CSS: tabs, PDF preview, buttons, typography
# --------------------------------------------------------

TAB_CSS = """
/* Tab Container */
.stTabs [data-baseweb="tab-list"] {
    gap: 2rem;
    border-bottom: 2px solid #e5e5e5;
    padding-bottom: 6px;
}

/* Normal Tab */
.stTabs [data-baseweb="tab"] {
    font-size: 16px;
    font-weight: 500;
    padding: 10px 22px;
    border-radius: 12px 12px 0 0;
    background-color: #f5f7ff;
    color: #444;
    transition: all 0.25s ease;
    border: 1px solid transparent;
}

/* Remove Streamlit default underline bar */
.stTabs [data-baseweb="tab-highlight"] {
    background-color: transparent !important;
}

/* Active Tab */
.stTabs [aria-selected="true"] {
    background: white;
    color: #2b59ff;
    font-weight: 700;
    border: 1px solid #d0d0d0;
    border-bottom: 3px solid transparent !important;
    box-shadow: 0px -2px 10px rgba(0,0,0,0.06);
}

/* Hover effect */
.stTabs [data-baseweb="tab"]:hover {
    background-color: #e9eeff;
    color: #2b59ff;
}
"""

PDF_PREVIEW_CSS = """
/* Scrollable PDF Container */
.pdf-scroll {
    max-height: 800px;
    overflow-y: auto;
    overflow-x: hidden;
    border: 1px solid #e5e5e5;
    padding: 10px;
    border-radius: 8px;
    background-color: #fafafa;
}

/* PDF Images */
.pdf-scroll img {
    max-width: 100% !important;
    height: auto !important;
    display: block;
    border-radius: 6px;
    margin-bottom: 10px;
}
"""

GLOBAL_UI_CSS = """
/* Improve spacing */
h1, h2, h3, h4, h5, h6 {
    letter-spacing: -0.3px;
}

/* Improve default buttons */
.stButton > button {
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 600;
}

/* Better text area */
.stTextArea textarea {
    border-radius: 8px;
    font-size: 15px;
    line-height: 1.5;
}

"""

FILE_LIST_CSS = """
<style>
hr {
    border: none;
    border-top: 1px solid #f1f3f6;
}
</style>
"""

HIDE_STREAMLIT_STYLE = """
<style>
/* Hide hamburger menu */
#MainMenu {visibility: hidden;}

/* Hide footer */
footer {visibility: hidden;}

/* Hide header */
header {visibility: hidden;}

/* Optional: Remove Streamlit default padding */
.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}
</style>
"""


# --------------------------------------------------------
#  Inject CSS (Called once in app.py)
# --------------------------------------------------------

def inject_css():
    """Inject all global CSS styles into Streamlit."""
    full_css = TAB_CSS + PDF_PREVIEW_CSS + GLOBAL_UI_CSS
    st.markdown(f"<style>{full_css}</style>", unsafe_allow_html=True)