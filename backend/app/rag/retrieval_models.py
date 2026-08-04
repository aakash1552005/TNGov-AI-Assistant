"""Shared data models for the retrieval and generation pipeline.

These dataclasses define the contract between the retrieval layer,
generation layer, and the API layer (Milestone 4). Keeping them in
a shared module ensures they can be reused unchanged across layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Citation:
    """A structured source citation built from chunk metadata.

    Attributes:
        scheme_name: Name of the government scheme.
        department: Owning department.
        document_name: Source PDF filename.
        page_number: Page number in the source document (None if unknown).
        source_url: Official URL for the source document.
        excerpt: First ~200 characters of the chunk text (for display).
    """

    scheme_name: str
    department: str
    document_name: str
    page_number: int | None
    source_url: str
    excerpt: str | None


@dataclass
class RetrievedChunk:
    """A document chunk retrieved via hybrid search.

    Only ``chunk_text`` and ``metadata`` are passed into the LLM prompt.
    Score fields are internal — used for logging, debugging, and
    relevance gating only.

    Attributes:
        chunk_id: Unique identifier for this chunk.
        chunk_text: The text content of the chunk.
        metadata: Full metadata dict from ChromaDB.
        vector_score: Cosine distance from ChromaDB (lower = more similar).
            None if the chunk was not returned by vector search.
        bm25_score: Raw BM25 score. None if the chunk was not returned
            by BM25 search.
        rrf_score: Fused Reciprocal Rank Fusion score.
        final_rank: 1-indexed rank after RRF fusion and sorting.
    """

    chunk_id: str
    chunk_text: str
    metadata: dict[str, str | int]
    vector_score: float | None
    bm25_score: float | None
    rrf_score: float
    final_rank: int


@dataclass
class RetrievalMetadata:
    """Diagnostic metadata about a retrieval operation.

    Attributes:
        total_retrieved: Number of unique chunks after fusion.
        top_rrf_score: Highest RRF score among retrieved chunks.
        vector_results_count: Number of results from vector search.
        bm25_results_count: Number of results from BM25 search.
        llm_called: Whether the LLM was invoked (False if relevance
            threshold was not met).
        confidence_level: Rated confidence ("High", "Medium", "Low").
    """

    total_retrieved: int
    top_rrf_score: float | None
    vector_results_count: int
    bm25_results_count: int
    llm_called: bool
    confidence_level: str = "Low"


@dataclass
class GenerationResponse:
    """Complete response from the generation pipeline."""

    answer: str
    citations: list[Citation]
    retrieved_chunks: list[RetrievedChunk]
    retrieval_metadata: RetrievalMetadata | None = None
    related_schemes: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
