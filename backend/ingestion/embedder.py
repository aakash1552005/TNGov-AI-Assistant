"""Embedding generation using sentence-transformers.

Wraps the ``intfloat/multilingual-e5-large`` model with the required
``"passage: "`` / ``"query: "`` prefix convention. The E5 model family
requires these prefixes — without them, retrieval quality degrades
significantly.

The model is loaded lazily on first use and cached in memory.
"""

from __future__ import annotations

import logging

from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Lazy-loaded model ─────────────────────────────────────────
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Load the embedding model on first use."""
    global _model
    if _model is None:
        logger.info("Loading embedding model '%s'...", settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model)
        logger.info(
            "Embedding model loaded (dimension=%d)", _model.get_embedding_dimension()
        )
    return _model


def embed_passages(
    texts: list[str],
    *,
    batch_size: int | None = None,
) -> list[list[float]]:
    """Generate embeddings for document passages.

    Applies the ``"passage: "`` prefix required by E5 models for
    document/passage embeddings.

    Args:
        texts: List of passage texts to embed.
        batch_size: Batch size for encoding (default from config).

    Returns:
        List of embedding vectors, one per input text.
    """
    if not texts:
        return []

    model = _get_model()
    bs = batch_size or settings.embedding_batch_size

    # E5 models require "passage: " prefix for document embeddings
    prefixed = [f"passage: {text}" for text in texts]

    embeddings = model.encode(
        prefixed,
        batch_size=bs,
        show_progress_bar=False,
        normalize_embeddings=True,
    )

    logger.info("Embedded %d passages (batch_size=%d)", len(texts), bs)
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """Generate an embedding for a search query.

    Applies the ``"query: "`` prefix required by E5 models for
    query embeddings.

    Args:
        query: The search query text.

    Returns:
        Embedding vector for the query.
    """
    model = _get_model()

    # E5 models require "query: " prefix for query embeddings
    prefixed = f"query: {query}"

    embedding = model.encode(
        prefixed,
        show_progress_bar=False,
        normalize_embeddings=True,
    )

    return embedding.tolist()
