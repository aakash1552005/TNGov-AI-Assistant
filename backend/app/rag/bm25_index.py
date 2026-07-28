"""BM25 keyword index over ChromaDB chunks.

Builds, persists, loads, and searches a BM25 index using the
``rank_bm25`` library. The index is rebuilt from ChromaDB's stored
chunks (not raw text) to guarantee it always matches the vector store.

Persistence format: JSON file at ``BM25_INDEX_PATH`` containing
tokenized documents, chunk ID mapping, and index metadata.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.rag import vector_store

logger = logging.getLogger(__name__)

# ── Module State ──────────────────────────────────────────────
_bm25: BM25Okapi | None = None
_chunk_ids: list[str] = []
_tokenized_corpus: list[list[str]] = []


def _tokenize(text: str) -> list[str]:
    """Simple whitespace tokenizer with lowercasing.

    Adequate for BM25 keyword matching on government document
    terms (scheme names, GO numbers, department names, legal
    terminology). A more sophisticated tokenizer can be swapped
    in later if needed.
    """
    return text.lower().split()


# ── Build & Persist ───────────────────────────────────────────


def rebuild_bm25_index() -> int:
    """Rebuild the BM25 index from all chunks in ChromaDB.

    Reads all documents and chunk IDs from the ChromaDB collection,
    tokenizes them, fits a BM25Okapi model, and persists the index
    to disk.

    Returns:
        Number of chunks indexed.
    """
    global _bm25, _chunk_ids, _tokenized_corpus

    collection = vector_store.get_collection()
    count = collection.count()

    if count == 0:
        logger.warning("ChromaDB collection is empty — BM25 index will be empty")
        _bm25 = None
        _chunk_ids = []
        _tokenized_corpus = []
        _persist_index()
        return 0

    logger.info("Rebuilding BM25 index from %d chunks...", count)

    # Fetch all documents from ChromaDB
    # ChromaDB .get() returns all docs when no IDs/filters are specified
    all_data = collection.get(include=["documents"])
    chunk_ids = all_data["ids"]
    documents = all_data["documents"]

    # Tokenize
    tokenized = [_tokenize(doc) for doc in documents]

    # Build BM25 index
    _bm25 = BM25Okapi(tokenized)
    _chunk_ids = chunk_ids
    _tokenized_corpus = tokenized

    # Persist to disk
    _persist_index()

    logger.info("BM25 index rebuilt: %d chunks indexed", count)
    return count


def _persist_index() -> None:
    """Serialize the BM25 index to JSON."""
    index_path = Path(settings.bm25_index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "chunk_ids": _chunk_ids,
        "tokenized_corpus": _tokenized_corpus,
        "chunk_count": len(_chunk_ids),
        "embedding_model": settings.embedding_model,
        "pipeline_version": settings.pipeline_version,
    }

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    logger.info("BM25 index persisted to '%s'", index_path)


def _load_index() -> bool:
    """Load a persisted BM25 index from disk.

    Returns:
        True if the index was loaded successfully, False otherwise.
    """
    global _bm25, _chunk_ids, _tokenized_corpus

    index_path = Path(settings.bm25_index_path)
    if not index_path.exists():
        logger.info("No persisted BM25 index found at '%s'", index_path)
        return False

    with open(index_path, encoding="utf-8") as f:
        data = json.load(f)

    _chunk_ids = data["chunk_ids"]
    _tokenized_corpus = data["tokenized_corpus"]

    if not _chunk_ids:
        logger.info("Persisted BM25 index is empty")
        _bm25 = None
        return True

    _bm25 = BM25Okapi(_tokenized_corpus)
    logger.info("BM25 index loaded from disk: %d chunks", len(_chunk_ids))
    return True


def _ensure_loaded() -> None:
    """Ensure the BM25 index is loaded (from disk or by rebuilding)."""
    global _bm25
    if _bm25 is None and not _chunk_ids:
        if not _load_index():
            logger.info("Building BM25 index for the first time...")
            rebuild_bm25_index()


# ── Search ────────────────────────────────────────────────────


def search(query: str, *, top_k: int | None = None) -> list[tuple[str, float]]:
    """Search the BM25 index for a query.

    Args:
        query: The search query text.
        top_k: Number of results to return (default from config).

    Returns:
        List of (chunk_id, bm25_score) tuples, sorted by score descending.
        Returns an empty list if the index is empty.
    """
    _ensure_loaded()

    if _bm25 is None or not _chunk_ids:
        logger.warning("BM25 index is empty — returning no results")
        return []

    k = top_k or settings.retrieval_bm25_top_k
    tokenized_query = _tokenize(query)

    scores = _bm25.get_scores(tokenized_query)

    # Get top-k indices sorted by score descending
    scored_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True,
    )[:k]

    results = [
        (_chunk_ids[i], float(scores[i]))
        for i in scored_indices
        if scores[i] > 0  # Skip zero-score results
    ]

    return results


def get_stats() -> dict:
    """Return BM25 index statistics."""
    _ensure_loaded()
    return {
        "chunk_count": len(_chunk_ids),
        "index_loaded": _bm25 is not None,
        "index_path": settings.bm25_index_path,
    }
