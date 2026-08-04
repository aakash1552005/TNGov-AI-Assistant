"""ChromaDB vector store — persistence layer for embedded chunks.

Provides:
- Collection creation with metadata (embedding_model, pipeline_version)
- Config drift detection (warns if collection was built with different settings)
- Batched upserts (configurable batch size, default 100)
- Vector similarity search
- Collection statistics
"""

from __future__ import annotations

import logging

import chromadb

from app.core.config import settings
from ingestion.chunker import Chunk

logger = logging.getLogger(__name__)

# ── Collection Metadata Keys ─────────────────────────────────
_META_EMBEDDING_MODEL = "embedding_model"
_META_PIPELINE_VERSION = "pipeline_version"


# ── Client / Collection Management ───────────────────────────

_client: chromadb.ClientAPI | None = None


def get_chunk_count() -> int:
    """Return the total number of chunks in the collection."""
    try:
        col = get_collection()
        return col.count()
    except Exception:
        return 0


def _get_client() -> chromadb.ClientAPI:
    """Get or create the persistent ChromaDB client."""
    global _client
    if _client is None:
        logger.info("Initializing ChromaDB at '%s'", settings.chroma_db_path)
        _client = chromadb.PersistentClient(path=settings.chroma_db_path)
    return _client


def _check_collection_metadata(collection: chromadb.Collection) -> None:
    """Warn if the collection was built with different config values.

    Compares the stored ``embedding_model`` and ``pipeline_version``
    against the current settings. If they differ, logs a WARNING so
    the user knows the collection should be rebuilt.
    """
    meta = collection.metadata or {}

    stored_model = meta.get(_META_EMBEDDING_MODEL)
    stored_version = meta.get(_META_PIPELINE_VERSION)

    if stored_model and stored_model != settings.embedding_model:
        logger.warning(
            "COLLECTION CONFIG MISMATCH: collection was built with "
            "embedding_model='%s', but current config uses '%s'. "
            "The collection should be rebuilt (run `python -m ingestion.cli clear` "
            "then `python -m ingestion.cli ingest`).",
            stored_model,
            settings.embedding_model,
        )

    if stored_version and stored_version != settings.pipeline_version:
        logger.warning(
            "COLLECTION CONFIG MISMATCH: collection was built with "
            "pipeline_version='%s', but current config uses '%s'. "
            "The collection should be rebuilt.",
            stored_version,
            settings.pipeline_version,
        )


def get_collection() -> chromadb.Collection:
    """Get or create the named collection with metadata.

    If an existing collection was built with a different embedding model,
    it is deleted and recreated to prevent dimension mismatch errors.

    Returns:
        The ChromaDB collection for scheme documents.
    """
    client = _get_client()
    col = None
    try:
        existing_col = client.get_collection(settings.chroma_collection_name)
        meta = existing_col.metadata or {}
        stored_model = meta.get(_META_EMBEDDING_MODEL)
        if stored_model and stored_model != settings.embedding_model:
            logger.warning(
                "COLLECTION CONFIG MISMATCH: Deleting collection built with '%s' (current model: '%s')",
                stored_model,
                settings.embedding_model,
            )
            client.delete_collection(settings.chroma_collection_name)
        else:
            col = existing_col
    except Exception:
        col = None

    if col is None:
        col = client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={
                _META_EMBEDDING_MODEL: settings.embedding_model,
                _META_PIPELINE_VERSION: settings.pipeline_version,
                "hnsw:space": "cosine",
            },
        )
    return col


# ── Upsert ───────────────────────────────────────────────────


def upsert_chunks(
    chunks: list[Chunk],
    embeddings: list[list[float]],
    *,
    batch_size: int | None = None,
) -> int:
    """Upsert chunks with embeddings into ChromaDB in batches.

    Uses chunk_id as the document ID, making this operation
    idempotent — safe to re-run with the same data.

    Args:
        chunks: List of Chunk objects to store.
        embeddings: Corresponding embedding vectors.
        batch_size: Number of chunks per upsert batch
            (default from config: 100).

    Returns:
        Total number of chunks upserted.
    """
    if not chunks:
        return 0

    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Chunk count ({len(chunks)}) != embedding count ({len(embeddings)})"
        )

    collection = get_collection()
    bs = batch_size or settings.chroma_upsert_batch_size
    total = len(chunks)

    for start in range(0, total, bs):
        end = min(start + bs, total)
        batch_chunks = chunks[start:end]
        batch_embeddings = embeddings[start:end]

        collection.upsert(
            ids=[c.chunk_id for c in batch_chunks],
            documents=[c.text for c in batch_chunks],
            embeddings=batch_embeddings,
            metadatas=[c.to_metadata() for c in batch_chunks],
        )

        logger.info("Upserted batch %d–%d of %d chunks", start + 1, end, total)

    return total


# ── Query ────────────────────────────────────────────────────


def query_similar(
    query_embedding: list[float],
    *,
    top_k: int = 5,
    where: dict | None = None,
) -> dict:
    """Search for chunks similar to a query embedding.

    Args:
        query_embedding: The query vector.
        top_k: Number of results to return.
        where: Optional metadata filter dict.

    Returns:
        ChromaDB query results dict with ids, documents,
        metadatas, and distances.
    """
    collection = get_collection()
    kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    return collection.query(**kwargs)


# ── Stats / Management ───────────────────────────────────────


def get_stats() -> dict:
    """Return collection statistics.

    Returns:
        Dict with collection name, chunk count, and metadata.
    """
    collection = get_collection()
    return {
        "collection_name": collection.name,
        "chunk_count": collection.count(),
        "metadata": collection.metadata,
    }


def clear_collection() -> None:
    """Delete and recreate the collection.

    This removes all stored chunks and embeddings. The collection
    is recreated with current config metadata.
    """
    client = _get_client()
    try:
        client.delete_collection(settings.chroma_collection_name)
        logger.info("Deleted collection '%s'", settings.chroma_collection_name)
    except ValueError:
        logger.info("Collection '%s' does not exist — nothing to delete",
                     settings.chroma_collection_name)

    # Recreate with current metadata
    get_collection()
    logger.info("Recreated collection '%s'", settings.chroma_collection_name)
