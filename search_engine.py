# search_engine.py
import os
import json
import re
from typing import List, Dict, Any

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "docs.json")
os.makedirs(DB_DIR, exist_ok=True)

# In-memory index
# One item = one page:
# {
#   "filename": "file.pdf",
#   "page": 3,
#   "text": "...",        # original text
#   "text_lower": "...",  # cached lowercase version
# }
docs: List[Dict[str, Any]] = []


# -------------------------------------------------------------------
# Page splitting
# -------------------------------------------------------------------

# Matches headers like: [PAGE 1/5 – OCR angle=0°]
PAGE_PATTERN = re.compile(
    r"\[PAGE\s+(\d+)/(\d+)\s+–\s+OCR angle=(-?\d+)°\]\n"
)


def _split_into_pages(text: str) -> List[Dict[str, Any]]:
    """
    Split big OCR text (with [PAGE ...] headers) into page chunks.

    Returns:
        [
            {"page": 1, "text": "..."},
            {"page": 2, "text": "..."},
            ...
        ]
    """
    text = (text or "").strip()
    if not text:
        return []

    # If no PAGE markers, treat as single page
    if "[PAGE" not in text:
        return [{"page": 1, "text": text}]

    matches = list(PAGE_PATTERN.finditer(text))
    if not matches:
        return [{"page": 1, "text": text}]

    pages: List[Dict[str, Any]] = []
    for i, m in enumerate(matches):
        page_num = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        page_text = text[start:end].strip()
        if page_text:
            pages.append({"page": page_num, "text": page_text})

    if not pages:
        pages.append({"page": 1, "text": text})

    return pages


# -------------------------------------------------------------------
# DB load / save
# -------------------------------------------------------------------

def _load_db() -> None:
    """Load docs from disk into memory, normalize structure."""
    global docs

    if not os.path.exists(DB_PATH):
        docs = []
        return

    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        docs = []
        return

    normalized: List[Dict[str, Any]] = []

    if isinstance(data, list):
        source = data
    elif isinstance(data, dict) and isinstance(data.get("documents"), list):
        source = data["documents"]
    else:
        source = []

    for d in source:
        if not isinstance(d, dict):
            continue
        filename = d.get("filename", "")
        page = d.get("page")
        text = d.get("text", "") or ""
        # some old entries might have 'embedding' we ignore now

        text_lower = d.get("text_lower")
        if text_lower is None:
            text_lower = text.lower()

        normalized.append(
            {
                "filename": filename,
                "page": page,
                "text": text,
                "text_lower": text_lower,
            }
        )

    docs = normalized


def _save_db() -> None:
    """Save docs back to JSON."""
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)


# Load once on import
_load_db()


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def add_document(filename: str, text: str) -> None:
    """
    Index a document at page level, keyword-only.

    - Removes any existing pages for this filename
    - Splits text into pages
    - Stores:
        filename, page, text, text_lower
    """
    global docs

    filename = os.path.basename(filename)
    pages = _split_into_pages(text)
    if not pages:
        return

    # Remove old entries for this file
    docs = [d for d in docs if d.get("filename") != filename]

    # Add new pages
    for p in pages:
        page_num = p.get("page", 1)
        page_text = (p.get("text") or "").strip()
        if not page_text:
            continue

        docs.append(
            {
                "filename": filename,
                "page": page_num,
                "text": page_text,
                "text_lower": page_text.lower(),
            }
        )

    _save_db()


def search(query: str, k: int = 50) -> List[Dict[str, Any]]:
    """
    Exact keyword search (page level), fast.

    - No embeddings
    - Case-insensitive for ASCII, preserves Khmer
    - Returns top-k pages where query appears

    Result:
        {
            "filename": str,
            "page": int,
            "text": str,
            "score": float  # simple relevance score
        }
    """
    q = (query or "").strip()
    if not q:
        return []

    if not docs:
        return []

    q_lower = q.lower()

    results: List[Dict[str, Any]] = []

    for d in docs:
        txt = d.get("text", "")
        txt_lower = d.get("text_lower", "").lower()  # safe

        if q_lower in txt_lower:
            # simple relevance: earlier position + how many matches
            pos = txt_lower.find(q_lower)
            count = txt_lower.count(q_lower)
            score = 1.0 / (1 + pos) + count * 0.01

            results.append(
                {
                    "filename": d.get("filename", ""),
                    "page": d.get("page", None),
                    "text": txt,
                    "score": float(score),
                }
            )

    if not results:
        return []

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]


def clean_missing_files(pdf_dir: str = "pdf_storage") -> None:
    """
    Remove pages whose PDF file no longer exists.
    """
    global docs

    if not docs:
        return

    cleaned: List[Dict[str, Any]] = []
    for d in docs:
        fname = d.get("filename")
        if not fname:
            continue
        pdf_path = os.path.join(pdf_dir, fname)
        if os.path.exists(pdf_path):
            cleaned.append(d)

    if len(cleaned) != len(docs):
        docs = cleaned
        _save_db()


def get_index_stats(pdf_dir: str = "pdf_storage") -> Dict[str, Any]:
    """
    Return:
        {
            "indexed_docs": number of unique PDFs,
            "indexed_filenames": [...],
            "orphan_docs": [... filenames with missing PDF]
        }
    """
    if not docs:
        return {
            "indexed_docs": 0,
            "indexed_filenames": [],
            "orphan_docs": [],
        }

    filenames = sorted({d.get("filename", "") for d in docs if d.get("filename")})
    orphan = []
    for fname in filenames:
        pdf_path = os.path.join(pdf_dir, fname)
        if not os.path.exists(pdf_path):
            orphan.append(fname)

    return {
        "indexed_docs": len(filenames),
        "indexed_filenames": filenames,
        "orphan_docs": orphan,
    }


def get_document_text(filename: str) -> str:
    """
    Return full document text by concatenating pages for that filename.
    """
    filename = os.path.basename(filename)
    pages = [d for d in docs if d.get("filename") == filename]
    if not pages:
        return ""

    pages_sorted = sorted(pages, key=lambda d: d.get("page", 0))

    parts = []
    for d in pages_sorted:
        page_num = d.get("page")
        page_text = d.get("text", "")
        if page_num is not None:
            parts.append(f"[PAGE {page_num}]\n{page_text}")
        else:
            parts.append(page_text)

    return "\n\n".join(parts)