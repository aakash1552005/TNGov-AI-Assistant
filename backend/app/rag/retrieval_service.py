"""Hybrid retrieval service: vector + BM25 + Reciprocal Rank Fusion.

Encapsulates the full retrieval pipeline in a single class, kept
separate from the generation/API layer. This is organization, not
abstraction — no interfaces or protocols.

For every query, logs vector_score, bm25_score, rrf_score, and
final_rank for each retrieved chunk (for debugging and tuning).
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.rag import bm25_index, vector_store
from app.rag.retrieval_models import RetrievedChunk
from ingestion.embedder import embed_query

logger = logging.getLogger(__name__)


class RetrievalService:
    """Hybrid retrieval: vector + BM25, fused via Reciprocal Rank Fusion.

    Usage::

        service = RetrievalService()
        chunks = service.retrieve("old age pension eligibility")
    """

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        """Run hybrid retrieval for a query.

        Steps:
            1. Embed query via the E5 embedder
            2. Vector search: ChromaDB top-k
            3. BM25 search: keyword index top-k
            4. RRF fusion: merge by chunk_id
            5. Sort by fused score descending
            6. Return top ``retrieval_final_context_k`` chunks

        Args:
            query: The user's question text.

        Returns:
            List of RetrievedChunk objects, sorted by RRF score
            descending, limited to ``retrieval_final_context_k``.
        """
        # 1. Embed query
        query_embedding = embed_query(query)

        # 2. Vector search
        vector_results = vector_store.query_similar(
            query_embedding,
            top_k=settings.retrieval_vector_top_k,
        )
        vector_hits = self._parse_vector_results(vector_results)

        # 3. BM25 search
        bm25_hits = bm25_index.search(query, top_k=settings.retrieval_bm25_top_k)

        # 4. RRF fusion
        fused = self._rrf_fusion(vector_hits, bm25_hits)

        # 5. Sort and limit
        fused_sorted = sorted(fused.values(), key=lambda c: c.rrf_score, reverse=True)
        top_k = fused_sorted[: settings.retrieval_final_context_k]

        # Assign final ranks
        for rank, chunk in enumerate(top_k, start=1):
            # RetrievedChunk is not frozen, so we can set final_rank
            object.__setattr__(chunk, "final_rank", rank)

        # 6. Log all scores for debugging
        self._log_retrieval(query, top_k, len(vector_hits), len(bm25_hits))

        return top_k

    def _parse_vector_results(
        self, results: dict
    ) -> dict[str, tuple[str, dict, float]]:
        """Parse ChromaDB query results into a lookup dict.

        Args:
            results: Raw ChromaDB query results.

        Returns:
            Dict mapping chunk_id → (text, metadata, distance).
        """
        hits: dict[str, tuple[str, dict, float]] = {}

        if not results or not results.get("ids") or not results["ids"][0]:
            return hits

        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for chunk_id, text, meta, dist in zip(ids, documents, metadatas, distances):
            hits[chunk_id] = (text, meta, dist)

        return hits

    def _rrf_fusion(
        self,
        vector_hits: dict[str, tuple[str, dict, float]],
        bm25_hits: list[tuple[str, float]],
    ) -> dict[str, RetrievedChunk]:
        """Fuse vector and BM25 results via Reciprocal Rank Fusion.

        RRF score for each chunk:
            rrf_score = Σ  1 / (rrf_k + rank_in_list)

        Chunks appearing in only one list get the score from that
        list alone.

        Args:
            vector_hits: Dict of chunk_id → (text, metadata, distance)
                from vector search.
            bm25_hits: List of (chunk_id, bm25_score) from BM25 search.

        Returns:
            Dict of chunk_id → RetrievedChunk with fused scores.
        """
        rrf_k = settings.rrf_k
        fused: dict[str, dict] = {}

        # Score vector results by their rank
        for rank, (chunk_id, (text, meta, distance)) in enumerate(
            vector_hits.items(), start=1
        ):
            fused[chunk_id] = {
                "chunk_text": text,
                "metadata": meta,
                "vector_score": distance,
                "bm25_score": None,
                "rrf_score": 1.0 / (rrf_k + rank),
            }

        # Score BM25 results by their rank and merge
        for rank, (chunk_id, bm25_score) in enumerate(bm25_hits, start=1):
            rrf_contrib = 1.0 / (rrf_k + rank)

            if chunk_id in fused:
                fused[chunk_id]["bm25_score"] = bm25_score
                fused[chunk_id]["rrf_score"] += rrf_contrib
            else:
                # BM25-only hit — need to fetch text and metadata from ChromaDB
                text, meta = self._fetch_chunk(chunk_id)
                fused[chunk_id] = {
                    "chunk_text": text,
                    "metadata": meta,
                    "vector_score": None,
                    "bm25_score": bm25_score,
                    "rrf_score": rrf_contrib,
                }

        # Convert to RetrievedChunk objects
        return {
            chunk_id: RetrievedChunk(
                chunk_id=chunk_id,
                chunk_text=data["chunk_text"],
                metadata=data["metadata"],
                vector_score=data["vector_score"],
                bm25_score=data["bm25_score"],
                rrf_score=data["rrf_score"],
                final_rank=0,  # Assigned after sorting
            )
            for chunk_id, data in fused.items()
        }

    def _fetch_chunk(self, chunk_id: str) -> tuple[str, dict]:
        """Fetch a single chunk's text and metadata from ChromaDB.

        Used when a BM25-only hit needs its full content.

        Args:
            chunk_id: The chunk ID to look up.

        Returns:
            Tuple of (text, metadata).
        """
        collection = vector_store.get_collection()
        result = collection.get(ids=[chunk_id], include=["documents", "metadatas"])

        if result["documents"]:
            return result["documents"][0], result["metadatas"][0]

        logger.warning("Chunk '%s' not found in ChromaDB", chunk_id)
        return "", {}

    def _log_retrieval(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        vector_count: int,
        bm25_count: int,
    ) -> None:
        """Log retrieval diagnostics for debugging and tuning."""
        logger.info(
            "Retrieval for query='%s': %d vector hits, %d BM25 hits, %d fused results",
            query[:80],
            vector_count,
            bm25_count,
            len(chunks),
        )
        for chunk in chunks:
            logger.info(
                "  rank=%d  rrf=%.4f  vector=%s  bm25=%s  chunk_id=%s  scheme=%s",
                chunk.final_rank,
                chunk.rrf_score,
                f"{chunk.vector_score:.4f}" if chunk.vector_score is not None else "N/A",
                f"{chunk.bm25_score:.4f}" if chunk.bm25_score is not None else "N/A",
                chunk.chunk_id[:12],
                chunk.metadata.get("scheme_name", "?"),
            )
