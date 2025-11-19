# search_engine.py
"""
Simple search engine for Khmer PDF Search System.

Public API (used by app.py):

    add_document(filename: str, text: str) -> None
    search(query: str, k: int = 10) -> List[dict]

Each search() result item looks like:
    {
        "filename": str,
        "text": str,
        "score": float,
    }

Index is stored in "index.json" in the project folder.
"""

import json
import os
from typing import List, Dict, Any, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
INDEX_PATH = "index.json"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L6-v2"

# -------------------------------------------------------------------
# Global state (in-memory)
# -------------------------------------------------------------------
_docs: List[Dict[str, Any]] = []
_emb_matrix: Optional[np.ndarray] = None
_model: Optional[SentenceTransformer] = None


# -------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------

def _get_model() -> SentenceTransformer:
    """Load the SentenceTransformer model once per process."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _load_index() -> None:
    """Load docs from disk into _docs."""
    global _docs
    if not os.path.exists(INDEX_PATH):
        _docs = []
        return

    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Expect a list of documents
        if isinstance(data, list):
            _docs = data
        elif isinstance(data, dict) and isinstance(data.get("documents"), list):
            # allow old format: {"documents": [...]}
            _docs = data["documents"]
        else:
            _docs = []
    except Exception:
        _docs = []


def _save_index() -> None:
    """Persist _docs to disk."""
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(_docs, f, ensure_ascii=False, indent=2)


def _rebuild_emb_matrix() -> None:
    """Rebuild the embedding matrix from _docs."""
    global _emb_matrix

    if not _docs:
        _emb_matrix = None
        return

    embs = []
    for d in _docs:
        emb_list = d.get("embedding")
        if not emb_list:
            continue
        emb = np.asarray(emb_list, dtype=np.float32)
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        embs.append(emb)

    if not embs:
        _emb_matrix = None
        return

    _emb_matrix = np.stack(embs, axis=0)  # (N, D)


# Load index when module is imported
_load_index()
_rebuild_emb_matrix()


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def add_document(filename: str, text: str) -> None:
    """
    Add or update a document in the index.

    - filename: PDF filename (used as key)
    - text: full extracted text (Khmer + English, OCR result)

    This function:
        * computes an embedding for the text
        * updates or appends the document
        * saves the index
        * rebuilds the in-memory embedding matrix
    """
    global _docs

    if not text or not text.strip():
        return

    filename = os.path.basename(filename)

    model = _get_model()
    # encode single string -> 1D numpy array
    emb = model.encode(text, convert_to_numpy=True)
    emb = emb.astype(np.float32)
    norm = np.linalg.norm(emb)
    if norm > 0:
        emb = emb / norm

    # check if doc already exists
    existing = None
    for d in _docs:
        if d.get("filename") == filename:
            existing = d
            break

    if existing is not None:
        existing["text"] = text
        existing["embedding"] = emb.tolist()
    else:
        _docs.append(
            {
                "filename": filename,
                "text": text,
                "embedding": emb.tolist(),
            }
        )

    _save_index()
    _rebuild_emb_matrix()


def search(query: str, k: int = 10) -> List[Dict[str, Any]]:
    """
    Search the index for the top-k most similar documents.

    Your app calls: raw_results = search(query)

    Returns a list of dicts:
        {
            "filename": str,
            "text": str,
            "score": float,
        }
    """
    query = (query or "").strip()
    if not query:
        return []

    if not _docs or _emb_matrix is None or _emb_matrix.size == 0:
        return []

    model = _get_model()
    q_emb = model.encode(query, convert_to_numpy=True)
    q_emb = q_emb.astype(np.float32)
    norm = np.linalg.norm(q_emb)
    if norm == 0:
        return []

    q_emb = q_emb / norm

    # cosine sim because all vectors are unit-normalized
    scores = _emb_matrix @ q_emb  # shape (N,)

    k = min(k, scores.shape[0])
    # indices of top-k scores
    top_idx = np.argsort(scores)[-k:][::-1]

    results: List[Dict[str, Any]] = []
    for idx in top_idx:
        d = _docs[int(idx)]
        score = float(scores[int(idx)])
        results.append(
            {
                "filename": d.get("filename", ""),
                "text": d.get("text", ""),
                "score": score,
            }
        )

    return results