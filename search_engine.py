# search_engine.py
import os
import json
from typing import List, Dict, Any, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "docs.json")

os.makedirs(DB_DIR, exist_ok=True)

MODEL_NAME = "sentence-transformers/distiluse-base-multilingual-cased-v2"
model: SentenceTransformer = SentenceTransformer(MODEL_NAME)

# In-memory storage
docs: List[Dict[str, Any]] = []
emb_matrix: Optional[np.ndarray] = None  # shape (N, D)


# -------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------
def _normalize(vec: np.ndarray) -> np.ndarray:
    """L2-normalize a 1D or 2D vector."""
    if vec.ndim == 1:
        norm = np.linalg.norm(vec) + 1e-10
        return vec / norm
    norms = np.linalg.norm(vec, axis=1, keepdims=True) + 1e-10
    return vec / norms


def _save_db() -> None:
    """Save docs (including embeddings) to JSON."""
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)


def _rebuild_emb_matrix() -> None:
    """Rebuild NumPy embedding matrix from docs list."""
    global emb_matrix
    if not docs:
        emb_matrix = None
        return

    emb_matrix = np.array([d["embedding"] for d in docs], dtype="float32")


def _load_db() -> None:
    """Load docs from JSON, deduplicate by filename, recompute embeddings."""
    global docs, emb_matrix

    if not os.path.exists(DB_PATH):
        docs = []
        emb_matrix = None
        return

    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        docs = []
        emb_matrix = None
        return

    if not isinstance(raw, list):
        docs = []
        emb_matrix = None
        return

    # Deduplicate by filename (keep last)
    by_filename: Dict[str, Dict[str, Any]] = {}
    for item in raw:
        fn = item.get("filename")
        if not fn:
            continue
        by_filename[fn] = {
            "filename": fn,
            "text": item.get("text", ""),
        }

    docs = list(by_filename.values())

    if not docs:
        emb_matrix = None
        return

    texts = [d["text"] for d in docs]
    embs = model.encode(texts, batch_size=8, show_progress_bar=False)
    embs = np.asarray(embs, dtype="float32")
    embs = _normalize(embs)

    for d, e in zip(docs, embs):
        d["embedding"] = e.tolist()

    emb_matrix = embs
    _save_db()


# Load database once at import
_load_db()


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------
def add_document(filename: str, text: str) -> None:
    """
    Add or update a document.

    - If filename already exists, its text & embedding are UPDATED (no duplicates).
    - If it's new, it is appended.
    """
    global docs, emb_matrix

    if not text or not text.strip():
        return

    # Compute normalized embedding
    emb = model.encode([text], show_progress_bar=False)[0]
    emb = np.asarray(emb, dtype="float32")
    emb = _normalize(emb)

    # Find existing document by filename
    existing_idx = None
    for i, d in enumerate(docs):
        if d["filename"] == filename:
            existing_idx = i
            break

    if existing_idx is not None:
        docs[existing_idx]["text"] = text
        docs[existing_idx]["embedding"] = emb.tolist()
    else:
        docs.append(
            {
                "filename": filename,
                "text": text,
                "embedding": emb.tolist(),
            }
        )

    _rebuild_emb_matrix()
    _save_db()


def search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Search for the top-k most similar documents for the given query.

    Returns a list of document dicts:
        { "filename": ..., "text": ..., "score": float }
    """
    if not docs or emb_matrix is None:
        return []

    # Query embedding
    q_emb = model.encode([query], show_progress_bar=False)[0]
    q_emb = np.asarray(q_emb, dtype="float32")
    q_emb = _normalize(q_emb)

    # Cosine similarity = dot product for normalized vectors
    sims = emb_matrix @ q_emb  # shape (N,)

    # Top-k indices
    top_k = min(k, len(docs))
    idxs = np.argsort(-sims)[:top_k]

    results: List[Dict[str, Any]] = []
    for i in idxs:
        d = docs[int(i)]
        item = {
            "filename": d["filename"],
            "text": d["text"],
            "score": float(sims[int(i)]),
        }
        results.append(item)

    return results


def clean_missing_files(pdf_dir: str = "pdf_storage") -> None:
    """
    Remove indexed documents if the corresponding PDF file
    is missing in the pdf_storage/ folder.
    """
    global docs, emb_matrix

    if not os.path.exists(pdf_dir):
        return

    valid_docs = []
    for d in docs:
        filename = d["filename"]
        pdf_path = os.path.join(pdf_dir, filename)
        if os.path.exists(pdf_path):
            valid_docs.append(d)

    if len(valid_docs) != len(docs):
        docs = valid_docs
        _rebuild_emb_matrix()
        _save_db()


def get_index_stats(pdf_dir: str = "pdf_storage") -> Dict[str, Any]:
    """
    Return simple statistics about the index:
      - indexed_docs: number of docs in index
      - indexed_filenames: list of filenames in index
      - orphan_docs: docs in index whose PDF file is missing
    """
    if not docs:
        return {
            "indexed_docs": 0,
            "indexed_filenames": [],
            "orphan_docs": 0,
        }

    indexed_filenames = [d["filename"] for d in docs]

    missing = 0
    if os.path.exists(pdf_dir):
        for fn in indexed_filenames:
            if not os.path.exists(os.path.join(pdf_dir, fn)):
                missing += 1

    return {
        "indexed_docs": len(docs),
        "indexed_filenames": indexed_filenames,
        "orphan_docs": missing,
    }


def get_document_text(filename: str) -> str:
    """
    Return the stored text for a document from the index.
    If not found, returns "".
    """
    for d in docs:
        if d["filename"] == filename:
            return d.get("text", "")
    return ""