# search_engine.py
import os
import json
from typing import List, Dict, Any, Optional

import numpy as np
import streamlit as st
from sentence_transformers import SentenceTransformer

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "docs.json")

os.makedirs(DB_DIR, exist_ok=True)

# Use a multilingual model (you already chose this)
# MODEL_NAME = "sentence-transformers/distiluse-base-multilingual-cased-v2"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


# -------------------------------------------------------------------
# Model caching (Step 1)
# -------------------------------------------------------------------

@st.cache_resource
def get_model() -> SentenceTransformer:
    """
    Load the SentenceTransformer model once and reuse it.
    Streamlit will keep this in memory between reruns.
    """
    return SentenceTransformer(MODEL_NAME)


# -------------------------------------------------------------------
# In-memory storage
# -------------------------------------------------------------------
docs: List[Dict[str, Any]] = []
emb_matrix: Optional[np.ndarray] = None  # shape (N, D)


# -------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------

def _normalize(vec: np.ndarray) -> np.ndarray:
    """L2-normalize a 1D or 2D vector."""
    if vec.ndim == 1:
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec
    elif vec.ndim == 2:
        norms = np.linalg.norm(vec, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vec / norms
    return vec


def _load_db() -> None:
    """Load documents from disk into the global docs list."""
    global docs, emb_matrix
    if not os.path.exists(DB_PATH):
        docs = []
        emb_matrix = None
        return

    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            docs = data
        elif isinstance(data, dict) and isinstance(data.get("documents"), list):
            # allow old format: {"documents": [...]}
            docs = data["documents"]
        else:
            docs = []
    except Exception:
        docs = []

    _rebuild_emb_matrix()


def _save_db() -> None:
    """Persist docs to disk."""
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)


def _rebuild_emb_matrix() -> None:
    """
    Rebuild the embedding matrix from docs.

    Step 2: We DO NOT recompute embeddings here.
    We only read the 'embedding' list already stored in each document.
    """
    global emb_matrix

    if not docs:
        emb_matrix = None
        return

    embs = []
    for d in docs:
        emb_list = d.get("embedding")
        if not emb_list:
            continue
        emb = np.asarray(emb_list, dtype="float32")
        emb = _normalize(emb)
        embs.append(emb)

    if not embs:
        emb_matrix = None
        return

    emb_matrix = np.stack(embs, axis=0)  # (N, D)


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

    Step 2: document embedding is computed only here (index time).
    """
    global docs, emb_matrix

    if not text or not text.strip():
        return

    filename = os.path.basename(filename)

    # Compute normalized embedding (using cached model)
    model = get_model()
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

    Step 2: only the query is embedded here (docs were embedded at index time).
    """
    if not docs or emb_matrix is None:
        return []

    query = (query or "").strip()
    if not query:
        return []

    # Query embedding (using cached model)
    model = get_model()
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

    if not docs:
        return

    valid_docs: List[Dict[str, Any]] = []
    for d in docs:
        fname = d.get("filename")
        if not fname:
            continue
        pdf_path = os.path.join(pdf_dir, fname)
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
            "orphan_docs": [],
        }

    indexed_filenames = [d["filename"] for d in docs]
    missing = []
    for fname in indexed_filenames:
        pdf_path = os.path.join(pdf_dir, fname)
        if not os.path.exists(pdf_path):
            missing.append(fname)

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