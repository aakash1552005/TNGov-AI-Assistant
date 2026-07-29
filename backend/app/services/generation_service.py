"""Generation service — orchestrates retrieval → relevance check → LLM → citations.

Entry point: ``answer_question(query)`` returns a ``GenerationResponse``.
This module is consumed by the FastAPI API layer in Milestone 4.
"""

from __future__ import annotations

import logging
import time

from app.core.config import settings
from app.rag.llm_client import GeminiClient, GroqClient, LLMClient, OpenAIClient
from app.rag.retrieval_models import (
    Citation,
    GenerationResponse,
    RetrievalMetadata,
    RetrievedChunk,
)
from app.rag.retrieval_service import RetrievalService
from app.utils.sanitizer import sanitize_query

logger = logging.getLogger(__name__)

# ── Module-level singletons ───────────────────────────────────
_retrieval_service = RetrievalService()
_llm_client: LLMClient | None = None


def _get_llm_client() -> LLMClient:
    """Select LLMClient implementation based on settings.llm_provider."""
    if _llm_client is not None:
        return _llm_client

    if settings.llm_provider == "gemini":
        return GeminiClient()
    elif settings.llm_provider == "openai":
        return OpenAIClient()
    elif settings.llm_provider == "groq":
        return GroqClient()
    else:
        raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")

_NO_RELEVANT_INFO = (
    "No relevant official information found. Please check with the "
    "concerned department directly for accurate information.\n\n"
    "⚠️ This is an AI assistant, not an official government source. "
    "Please verify all information with the concerned department "
    "before taking any action."
)


def answer_question(query: str) -> GenerationResponse:
    """Execute the full retrieval → generation pipeline.

    Steps:
        1. Validate query length
        2. Retrieve chunks via hybrid search (vector + BM25 + RRF)
        3. Check relevance threshold — if top RRF score < min_score,
           skip the LLM call and return "no relevant info"
        4. Build context strings from top-k chunks
        5. Call LLM to generate a grounded answer
        6. Build structured citations from chunk metadata
        7. Return GenerationResponse

    Args:
        query: The user's question (English or Tamil).

    Returns:
        GenerationResponse with answer, citations, retrieved chunks,
        and retrieval metadata.
    """
    start = time.monotonic()
    clean_query = sanitize_query(query)

    # 1. Validate query length
    if len(clean_query) > settings.max_query_length:
        return GenerationResponse(
            answer=(
                f"Your question is too long (max {settings.max_query_length} "
                f"characters). Please shorten your question and try again."
            ),
            citations=[],
            retrieved_chunks=[],
            retrieval_metadata=RetrievalMetadata(
                total_retrieved=0,
                top_rrf_score=None,
                vector_results_count=0,
                bm25_results_count=0,
                llm_called=False,
            ),
        )

    # 2. Retrieve chunks
    try:
        chunks = _retrieval_service.retrieve(clean_query)
    except Exception as exc:
        logger.exception("Retrieval failed for query: %s", clean_query[:80])
        return GenerationResponse(
            answer="Unable to search for relevant information at the moment. Please try again later.",
            citations=[],
            retrieved_chunks=[],
            retrieval_metadata=RetrievalMetadata(
                total_retrieved=0,
                top_rrf_score=None,
                vector_results_count=0,
                bm25_results_count=0,
                llm_called=False,
            ),
        )

    # Build retrieval metadata
    top_rrf = chunks[0].rrf_score if chunks else None
    vector_count = sum(1 for c in chunks if c.vector_score is not None)
    bm25_count = sum(1 for c in chunks if c.bm25_score is not None)

    # 3. Relevance threshold check
    top_chunk = chunks[0] if chunks else None
    has_relevant_vector = (
        top_chunk is not None
        and top_chunk.vector_score is not None
        and top_chunk.vector_score <= settings.retrieval_max_vector_distance
    )
    has_relevant_bm25 = (
        top_chunk is not None
        and top_chunk.bm25_score is not None
        and top_chunk.bm25_score >= settings.retrieval_min_bm25_score
    )

    is_relevant = (
        bool(chunks)
        and (top_rrf is not None and top_rrf >= settings.retrieval_min_score)
        and (has_relevant_vector or has_relevant_bm25)
    )

    if not is_relevant:
        logger.info(
            "Below relevance threshold (top_rrf=%s, vector_score=%s, bm25_score=%s) — skipping LLM call",
            f"{top_rrf:.4f}" if top_rrf else "None",
            f"{top_chunk.vector_score:.4f}" if top_chunk and top_chunk.vector_score is not None else "None",
            f"{top_chunk.bm25_score:.4f}" if top_chunk and top_chunk.bm25_score is not None else "None",
        )
        return GenerationResponse(
            answer=_NO_RELEVANT_INFO,
            citations=[],
            retrieved_chunks=chunks,
            retrieval_metadata=RetrievalMetadata(
                total_retrieved=len(chunks),
                top_rrf_score=top_rrf,
                vector_results_count=vector_count,
                bm25_results_count=bm25_count,
                llm_called=False,
            ),
        )

    # 4. Build context strings — only chunk_text goes into the prompt
    context_strings = []
    for chunk in chunks:
        # Include metadata as a header so the LLM can cite properly
        meta = chunk.metadata
        header = (
            f"Source: {meta.get('scheme_name', 'Unknown')} | "
            f"{meta.get('document_name', 'Unknown')} | "
            f"Page {meta.get('page_number', '?')}"
        )
        context_strings.append(f"{header}\n{chunk.chunk_text}")

    # 5. Call LLM
    llm_called = True
    try:
        client = _get_llm_client()
        answer = client.generate(clean_query, context_strings)
    except Exception as exc:
        logger.exception("LLM call failed for query: %s", clean_query[:80])
        answer = "Unable to generate a response at the moment. Please try again later."
        llm_called = False  # Failed, not truly called successfully

    # 6. Build structured citations
    citations = _build_citations(chunks)

    elapsed = time.monotonic() - start
    logger.info("answer_question completed in %.2fs (llm_called=%s)", elapsed, llm_called)

    # 7. Return GenerationResponse
    return GenerationResponse(
        answer=answer,
        citations=citations,
        retrieved_chunks=chunks,
        retrieval_metadata=RetrievalMetadata(
            total_retrieved=len(chunks),
            top_rrf_score=top_rrf,
            vector_results_count=vector_count,
            bm25_results_count=bm25_count,
            llm_called=llm_called,
        ),
    )


def _build_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    """Build structured Citation objects from retrieved chunk metadata.

    Deduplicates by (scheme_name, document_name, page_number) to
    avoid listing the same source multiple times.

    Args:
        chunks: Retrieved chunks with metadata.

    Returns:
        List of unique Citation objects.
    """
    seen: set[tuple] = set()
    citations: list[Citation] = []

    for chunk in chunks:
        meta = chunk.metadata
        scheme_name = meta.get("scheme_name", "")
        doc_name = meta.get("document_name", "")

        if not scheme_name or scheme_name == "Unknown" or not doc_name or doc_name == "Unknown":
            continue

        key = (
            scheme_name,
            doc_name,
            meta.get("page_number"),
        )

        if key in seen:
            continue
        seen.add(key)

        # Excerpt: first ~200 chars of the chunk text
        excerpt = chunk.chunk_text[:200].strip()
        if len(chunk.chunk_text) > 200:
            excerpt += "…"

        citations.append(
            Citation(
                scheme_name=meta.get("scheme_name", "Unknown"),
                department=meta.get("department", "Unknown"),
                document_name=meta.get("document_name", "Unknown"),
                page_number=meta.get("page_number"),
                source_url=meta.get("source_url", ""),
                excerpt=excerpt,
            )
        )

    return citations
