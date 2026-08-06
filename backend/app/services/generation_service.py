"""Generation service — orchestrates retrieval → topic guard → LLM → citations.

Pipeline:
  1. Sanitize query
  2. Retrieve chunks (hybrid BM25 + vector)
  3. Pre-LLM topic guard — model-independent refusal for out-of-domain queries
  4. LLM generation (only reached if guard passes)
  5. Build citations & return GenerationResponse

Entry point: ``answer_question(query)`` returns a ``GenerationResponse``.
"""

from __future__ import annotations

import logging
import time

from app.core.config import settings
from app.rag.llm_client import GroqClient, LLMClient
from app.rag.query_expander import suggest_did_you_mean
from app.rag.retrieval_models import (
    Citation,
    GenerationResponse,
    RetrievalMetadata,
    RetrievedChunk,
)
from app.rag.retrieval_service import RetrievalService
from app.rag.topic_guard import should_refuse
from app.utils.sanitizer import sanitize_query

logger = logging.getLogger(__name__)

# ── Module-level singletons ───────────────────────────────────
_retrieval_service = RetrievalService()
_llm_client: LLMClient | None = None


def _get_llm_client() -> LLMClient:
    """Get the Groq LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = GroqClient()
    return _llm_client


def _build_refusal_response(
    query: str,
    chunks: list[RetrievedChunk],
    vector_count: int,
    bm25_count: int,
    reason: str = "domain",
) -> GenerationResponse:
    """Build a helpful, diagnostic refusal message with fuzzy match suggestions.

    Args:
        query: The user's original query.
        chunks: Retrieved chunks (may be empty for out-of-domain).
        vector_count: Number of vector-matched chunks.
        bm25_count: Number of BM25-matched chunks.
        reason: 'domain' | 'threshold' — reason for refusal (for logging).
    """
    logger.info("Refusal triggered (reason=%s) for query: %s", reason, query[:80])
    suggestions = suggest_did_you_mean(query)

    msg_lines = [
        "This assistant only answers officially indexed Tamil Nadu Government schemes.",
        "No matching scheme was found for your query.",
        "",
        "Possible reasons:",
        "• Your query may not relate to a Tamil Nadu Government welfare scheme",
        "• The scheme name or spelling may differ from official government terminology",
        "• The scheme may not yet be indexed in this system",
    ]

    if suggestions:
        msg_lines.append("")
        msg_lines.append("You may be looking for one of these official schemes:")
        for s in suggestions:
            msg_lines.append(f"• {s}")
        msg_lines.append("")
        msg_lines.append("Try rephrasing with one of the above scheme names.")

    msg_lines.append(
        "\n⚠️ This is an AI assistant, not an official government source. "
        "Please verify all information with the concerned department directly."
    )

    return GenerationResponse(
        answer="\n".join(msg_lines),
        citations=[],
        retrieved_chunks=chunks,
        retrieval_metadata=RetrievalMetadata(
            total_retrieved=len(chunks),
            top_rrf_score=chunks[0].rrf_score if chunks else None,
            vector_results_count=vector_count,
            bm25_results_count=bm25_count,
            llm_called=False,
            confidence_level="Low",
        ),
        suggestions=suggestions,
    )


def answer_question(query: str, context_prefix: str | None = None) -> GenerationResponse:
    """Execute the full retrieval → generation pipeline."""
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
                confidence_level="Low",
            ),
        )

    # 2. Retrieve chunks
    effective_query = f"{context_prefix} {clean_query}".strip() if context_prefix else clean_query
    try:
        chunks = _retrieval_service.retrieve(effective_query)
    except Exception:
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
                confidence_level="Low",
            ),
        )

    # Build retrieval metadata
    top_rrf = chunks[0].rrf_score if chunks else None
    vector_count = sum(1 for c in chunks if c.vector_score is not None)
    bm25_count = sum(1 for c in chunks if c.bm25_score is not None)

    # 3. Pre-LLM topic guard — model-independent domain relevance check.
    #    This runs BEFORE any LLM call so refusal is consistent across all
    #    primary and fallback models.
    top_chunk = chunks[0] if chunks else None

    if should_refuse(clean_query, chunks, top_rrf, settings.retrieval_min_score):
        logger.info(
            "Topic guard refused query (top_rrf=%s): %s",
            f"{top_rrf:.4f}" if top_rrf else "None",
            clean_query[:80],
        )
        return _build_refusal_response(
            clean_query, chunks, vector_count, bm25_count, reason="domain"
        )

    # 3b. Secondary retrieval quality check (vector + BM25 thresholds)
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
        return _build_refusal_response(
            clean_query, chunks, vector_count, bm25_count, reason="threshold"
        )

    # Determine confidence level
    confidence_level = "Medium"
    if top_chunk and top_chunk.vector_score is not None and top_chunk.vector_score <= 0.35:
        confidence_level = "High"
    elif top_rrf and top_rrf >= 0.030:
        confidence_level = "High"

    # Extract related schemes — ranked by department match, then RRF score.
    # Schemes from the same department as the primary result are more relevant.
    related_schemes: list[str] = []
    main_scheme = top_chunk.metadata.get("scheme_name", "") if top_chunk else ""
    main_dept = top_chunk.metadata.get("department", "") if top_chunk else ""

    # Build candidates with sort key: (dept_match=0 preferred, -rrf_score)
    candidates: list[tuple[int, float, str]] = []
    for c in chunks:
        scheme = str(c.metadata.get("scheme_name", "")).strip()
        if not scheme or scheme == main_scheme:
            continue
        dept = str(c.metadata.get("department", "")).strip()
        dept_mismatch = 0 if (dept and dept == main_dept) else 1
        rrf = c.rrf_score if c.rrf_score is not None else 0.0
        candidates.append((dept_mismatch, -rrf, scheme))

    candidates.sort()
    seen_related: set[str] = set()
    for _, _, scheme in candidates:
        if scheme not in seen_related:
            related_schemes.append(scheme)
            seen_related.add(scheme)

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
    except Exception:
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
            confidence_level=confidence_level,
        ),
        related_schemes=related_schemes,
        suggestions=[],
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
