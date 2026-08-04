"""Unit tests for confidence calculation and related schemes ranking logic."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.rag.retrieval_models import RetrievedChunk
from app.services.generation_service import answer_question


def _make_retrieved_chunk(
    scheme_name: str,
    department: str = "General",
    vector_score: float | None = 0.20,
    bm25_score: float | None = 10.0,
    rrf_score: float = 0.035,
    final_rank: int = 1,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="test-id",
        doc_id="test-doc",
        chunk_text="Sample text for testing TN Gov scheme.",
        metadata={"scheme_name": scheme_name, "department": department},
        vector_score=vector_score,
        bm25_score=bm25_score,
        rrf_score=rrf_score,
        final_rank=final_rank,
    )


class TestConfidenceCalculation:
    """Validate confidence assignment logic."""

    def test_high_confidence_vector_threshold(self, monkeypatch):
        """Vector score <= 0.35 yields High confidence."""
        mock_chunks = [_make_retrieved_chunk("KMUT", vector_score=0.20, rrf_score=0.020)]
        monkeypatch.setattr("app.services.generation_service._retrieval_service.retrieve", lambda q: mock_chunks)
        monkeypatch.setattr("app.services.generation_service._get_llm_client", lambda: MagicMock(generate=lambda q, c: "Answer"))

        res = answer_question("KMUT")
        assert res.retrieval_metadata.confidence_level == "High"

    def test_high_confidence_rrf_threshold(self, monkeypatch):
        """Top RRF score >= 0.030 yields High confidence."""
        mock_chunks = [_make_retrieved_chunk("KMUT", vector_score=0.40, rrf_score=0.032)]
        monkeypatch.setattr("app.services.generation_service._retrieval_service.retrieve", lambda q: mock_chunks)
        monkeypatch.setattr("app.services.generation_service._get_llm_client", lambda: MagicMock(generate=lambda q, c: "Answer"))

        res = answer_question("KMUT")
        assert res.retrieval_metadata.confidence_level == "High"

    def test_medium_confidence(self, monkeypatch):
        """Vector score > 0.35 and RRF < 0.030 yields Medium confidence when above min score."""
        mock_chunks = [_make_retrieved_chunk("KMUT", vector_score=0.38, bm25_score=6.0, rrf_score=0.025)]
        monkeypatch.setattr("app.services.generation_service._retrieval_service.retrieve", lambda q: mock_chunks)
        monkeypatch.setattr("app.services.generation_service._get_llm_client", lambda: MagicMock(generate=lambda q, c: "Answer"))

        res = answer_question("KMUT")
        assert res.retrieval_metadata.confidence_level == "Medium"


class TestRelatedSchemesRanking:
    """Validate department-based ranking for related schemes."""

    def test_related_schemes_prioritizes_same_department(self, monkeypatch):
        mock_chunks = [
            _make_retrieved_chunk("Pudhumai Penn", department="Social Welfare", rrf_score=0.035),
            _make_retrieved_chunk("Other Welfare", department="Revenue", rrf_score=0.030),
            _make_retrieved_chunk("KMUT", department="Social Welfare", rrf_score=0.025),
        ]
        monkeypatch.setattr("app.services.generation_service._retrieval_service.retrieve", lambda q: mock_chunks)
        monkeypatch.setattr("app.services.generation_service._get_llm_client", lambda: MagicMock(generate=lambda q, c: "Answer"))

        res = answer_question("Pudhumai Penn")
        # KMUT shares department 'Social Welfare', so it should be prioritized over 'Other Welfare'
        assert res.related_schemes == ["KMUT", "Other Welfare"]
