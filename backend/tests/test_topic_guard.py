"""Unit tests for the pre-LLM topic guard module.

Tests verify that the guard correctly classifies out-of-domain and
in-domain queries without any external dependencies.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.rag.topic_guard import (
    is_out_of_domain,
    retrieval_has_known_scheme,
    should_refuse,
)


# ---------------------------------------------------------------------------
# is_out_of_domain tests
# ---------------------------------------------------------------------------

class TestIsOutOfDomain:
    """Test the hard-coded keyword blocklist."""

    # --- Out-of-domain queries ---
    @pytest.mark.parametrize("query", [
        "What is NASA Mars rover welfare scheme in Tamil Nadu?",
        "What is the current stock price of Infosys?",
        "IPL cricket welfare scheme Tamil Nadu",
        "Bitcoin price today",
        "cryptocurrency welfare scheme",
        "Chennai Super Kings team details",
        "weather forecast for Chennai",
        "Nifty 50 scheme",
        "Netflix subscription scheme",
        "Today's movie release scheme",
    ])
    def test_ood_queries_detected(self, query: str):
        assert is_out_of_domain(query) is True, f"Should be OOD: {query!r}"

    # --- In-domain queries (must NOT be blocked) ---
    @pytest.mark.parametrize("query", [
        "What is Kalaignar Magalir Urimai Thogai?",
        "free bus",
        "widow pension",
        "Pudhumai Penn",
        "old age pension",
        "KMUT scheme eligibility",
        "மகளிர் உரிமை",
        "Makkalai Thedi Maruthuvam",
        "Chief Minister Breakfast Scheme",
        "marriage assistance Tamil Nadu",
        "disability pension",
        "health insurance scheme",
    ])
    def test_indomain_queries_not_blocked(self, query: str):
        assert is_out_of_domain(query) is False, f"Should NOT be OOD: {query!r}"


# ---------------------------------------------------------------------------
# retrieval_has_known_scheme tests
# ---------------------------------------------------------------------------

def _make_chunk(scheme_name: str):
    """Helper: create a mock RetrievedChunk with given scheme_name."""
    chunk = MagicMock()
    chunk.metadata = {"scheme_name": scheme_name}
    return chunk


class TestRetrievalHasKnownScheme:
    def test_returns_true_for_known_scheme(self):
        chunks = [_make_chunk("Kalaignar Magalir Urimai Thogai Scheme")]
        assert retrieval_has_known_scheme(chunks) is True

    def test_returns_true_for_any_known_scheme(self):
        chunks = [
            _make_chunk("Unknown Scheme XYZ"),
            _make_chunk("Chief Minister's Breakfast Scheme"),
        ]
        assert retrieval_has_known_scheme(chunks) is True

    def test_returns_false_for_unknown_schemes(self):
        chunks = [
            _make_chunk("NASA Mars Welfare Program"),
            _make_chunk("IPL Cricket Benefit Scheme"),
        ]
        assert retrieval_has_known_scheme(chunks) is False

    def test_returns_false_for_empty_chunks(self):
        assert retrieval_has_known_scheme([]) is False


# ---------------------------------------------------------------------------
# should_refuse integration tests
# ---------------------------------------------------------------------------

class TestShouldRefuse:
    def test_refuses_ood_keyword_query(self):
        """OOD keyword → refuse even if chunks have high RRF."""
        chunks = [_make_chunk("Kalaignar Magalir Urimai Thogai Scheme")]
        # Attach rrf_score
        chunks[0].rrf_score = 0.05
        assert should_refuse("NASA Mars rover welfare scheme", chunks, 0.05) is True

    def test_refuses_no_chunks(self):
        assert should_refuse("free bus", [], None) is True

    def test_refuses_below_min_rrf(self):
        chunks = [_make_chunk("Kalaignar Magalir Urimai Thogai Scheme")]
        chunks[0].rrf_score = 0.001
        assert should_refuse("free bus", chunks, 0.001, retrieval_min_score=0.015) is True

    def test_allows_valid_known_scheme(self):
        chunks = [_make_chunk("Kalaignar Magalir Urimai Thogai Scheme")]
        chunks[0].rrf_score = 0.033
        assert should_refuse("What is KMUT?", chunks, 0.033) is False

    def test_allows_colloquial_query_with_good_rrf(self):
        chunks = [_make_chunk("Free Bus Travel for Women (Vidiyal Payanam Scheme)")]
        chunks[0].rrf_score = 0.033
        assert should_refuse("free bus", chunks, 0.033) is False

    def test_case_insensitive_ood(self):
        """OOD detection must be case-insensitive."""
        chunks = [_make_chunk("Kalaignar Magalir Urimai Thogai Scheme")]
        chunks[0].rrf_score = 0.05
        assert should_refuse("what is nasa doing in Tamil Nadu?", chunks, 0.05) is True
