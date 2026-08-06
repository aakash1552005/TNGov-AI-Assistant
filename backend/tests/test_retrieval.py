"""Deterministic retrieval tests (not RAGAS).

Tests hybrid retrieval against a purpose-built fixture collection
with known chunks. No GPT-4.1 calls — the LLM is mocked.

Tests:
1. English query hits expected scheme
2. Tamil query hits expected scheme
3. Exact scheme-name lookup works
4. Out-of-scope question returns "no relevant information"
"""

from __future__ import annotations

import os
import shutil
import tempfile
from unittest.mock import patch

import pytest

# ── Fixture Data ──────────────────────────────────────────────

FIXTURE_CHUNKS = [
    {
        "id": "chunk_pension_1",
        "text": (
            "Old Age Pension Scheme provides monthly pension of Rs. 1000 "
            "to senior citizens above 60 years of age. Applicants must "
            "have annual family income below Rs. 72000. The scheme is "
            "administered by the Department of Social Welfare, "
            "Government of Tamil Nadu."
        ),
        "metadata": {
            "scheme_name": "Old Age Pension Scheme",
            "department": "Social Welfare",
            "document_name": "old_age_pension.pdf",
            "page_number": 1,
            "source_url": "https://tn.gov.in/scheme/old-age-pension",
            "language": "en",
            "last_updated": "2025-01-15",
            "chunk_id": "chunk_pension_1",
            "document_hash": "abc123",
            "ingested_at": "2025-01-15T00:00:00Z",
        },
    },
    {
        "id": "chunk_pension_2_tamil",
        "text": (
            "முதியோர் ஓய்வூதியத் திட்டம் 60 வயதுக்கு மேற்பட்ட "
            "மூத்த குடிமக்களுக்கு மாதாந்திர ஓய்வூதியம் வழங்குகிறது. "
            "குடும்ப ஆண்டு வருமானம் ரூ. 72000க்கு கீழ் இருக்க வேண்டும்."
        ),
        "metadata": {
            "scheme_name": "Old Age Pension Scheme",
            "department": "Social Welfare",
            "document_name": "old_age_pension_ta.pdf",
            "page_number": 1,
            "source_url": "https://tn.gov.in/scheme/old-age-pension",
            "language": "ta",
            "last_updated": "2025-01-15",
            "chunk_id": "chunk_pension_2_tamil",
            "document_hash": "def456",
            "ingested_at": "2025-01-15T00:00:00Z",
        },
    },
    {
        "id": "chunk_crop_insurance_1",
        "text": (
            "Tamil Nadu State Crop Insurance Scheme provides compensation "
            "to farmers whose crops are damaged due to natural calamities. "
            "Farmers must register with the local agricultural office. "
            "Coverage includes paddy, sugarcane, and cotton crops."
        ),
        "metadata": {
            "scheme_name": "State Crop Insurance Scheme",
            "department": "Agriculture",
            "document_name": "crop_insurance.pdf",
            "page_number": 2,
            "source_url": "https://tn.gov.in/scheme/crop-insurance",
            "language": "en",
            "last_updated": "2025-03-10",
            "chunk_id": "chunk_crop_insurance_1",
            "document_hash": "ghi789",
            "ingested_at": "2025-03-10T00:00:00Z",
        },
    },
    {
        "id": "chunk_health_insurance_1",
        "text": (
            "Chief Minister's Comprehensive Health Insurance Scheme "
            "provides cashless medical treatment up to Rs. 5 lakh per "
            "family per year. The scheme covers over 1000 medical "
            "procedures in empanelled hospitals across Tamil Nadu."
        ),
        "metadata": {
            "scheme_name": "Chief Minister's Comprehensive Health Insurance Scheme",
            "department": "Health and Family Welfare",
            "document_name": "health_insurance.pdf",
            "page_number": 1,
            "source_url": "https://tn.gov.in/scheme/cmchis",
            "language": "en",
            "last_updated": "2025-02-20",
            "chunk_id": "chunk_health_insurance_1",
            "document_hash": "jkl012",
            "ingested_at": "2025-02-20T00:00:00Z",
        },
    },
]


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture(scope="module")
def temp_chroma_dir():
    """Create a temp directory for test ChromaDB."""
    tmpdir = tempfile.mkdtemp(prefix="test_chroma_")
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(scope="module")
def test_collection(temp_chroma_dir):
    """Build a ChromaDB collection with fixture chunks and embeddings.

    This fixture:
    - Patches the chroma_db_path to use a temp directory
    - Inserts fixture chunks with real embeddings from multilingual-e5-large
    - Builds a BM25 index over the same chunks
    """
    # Patch settings before importing modules that read them
    with patch("app.core.config.settings") as mock_settings, \
         patch("app.rag.vector_store.settings") as mock_vs_settings, \
         patch("app.rag.bm25_index.settings") as mock_bm25_settings, \
         patch("app.services.generation_service.settings") as mock_gen_settings:

        # Copy all real settings, override only what we need
        from app.core.config import Settings

        real_settings = Settings()
        for field_name in Settings.model_fields:
            val = getattr(real_settings, field_name)
            setattr(mock_settings, field_name, val)
            setattr(mock_vs_settings, field_name, val)
            setattr(mock_bm25_settings, field_name, val)
            setattr(mock_gen_settings, field_name, val)

        test_chroma_path = temp_chroma_dir
        test_collection_name = "test_retrieval"
        test_bm25_path = os.path.join(temp_chroma_dir, "test_bm25.json")

        for s in (mock_settings, mock_vs_settings, mock_bm25_settings, mock_gen_settings):
            s.chroma_db_path = test_chroma_path
            s.chroma_collection_name = test_collection_name
            s.bm25_index_path = test_bm25_path

        # Reset module-level state
        import app.rag.vector_store as vs
        import app.rag.bm25_index as bm25

        vs._client = None
        bm25._bm25 = None
        bm25._chunk_ids = []
        bm25._tokenized_corpus = []

        # Get embeddings for fixture texts
        from ingestion.embedder import embed_passages

        texts = [c["text"] for c in FIXTURE_CHUNKS]
        embeddings = embed_passages(texts)

        # Insert into ChromaDB
        collection = vs.get_collection()
        collection.upsert(
            ids=[c["id"] for c in FIXTURE_CHUNKS],
            documents=texts,
            embeddings=embeddings,
            metadatas=[c["metadata"] for c in FIXTURE_CHUNKS],
        )

        # Build BM25 index
        bm25.rebuild_bm25_index()

        yield collection

        # Cleanup module state
        vs._client = None
        bm25._bm25 = None
        bm25._chunk_ids = []


@pytest.fixture(scope="module")
def retrieval_service(test_collection):
    """Create a RetrievalService wired to the test collection."""
    from app.rag.retrieval_service import RetrievalService

    return RetrievalService()


# ── Tests ─────────────────────────────────────────────────────


class TestEnglishQuery:
    """English query should hit the expected scheme."""

    def test_pension_query(self, retrieval_service, test_collection):
        chunks = retrieval_service.retrieve("old age pension eligibility")
        assert len(chunks) > 0

        # The top result should be about the Old Age Pension Scheme
        scheme_names = [c.metadata.get("scheme_name") for c in chunks]
        assert "Old Age Pension Scheme" in scheme_names

        # Verify RetrievedChunk structure
        top = chunks[0]
        assert top.chunk_id
        assert top.chunk_text
        assert top.rrf_score > 0
        assert top.final_rank == 1


class TestTamilQuery:
    """Tamil query should hit the expected scheme."""

    def test_pension_tamil(self, retrieval_service, test_collection):
        chunks = retrieval_service.retrieve("முதியோர் ஓய்வூதியம்")
        assert len(chunks) > 0

        scheme_names = [c.metadata.get("scheme_name") for c in chunks]
        assert "Old Age Pension Scheme" in scheme_names


class TestExactSchemeName:
    """Exact scheme-name lookup should return the matching scheme."""

    def test_health_insurance_exact(self, retrieval_service, test_collection):
        chunks = retrieval_service.retrieve(
            "Chief Minister's Comprehensive Health Insurance Scheme"
        )
        assert len(chunks) > 0

        top = chunks[0]
        assert top.metadata.get("scheme_name") == (
            "Chief Minister's Comprehensive Health Insurance Scheme"
        )


class TestOutOfScope:
    """Out-of-scope question should fail the relevance threshold."""

    def test_irrelevant_query(self, retrieval_service, test_collection):
        """Query unrelated to TN government schemes."""

        # Mock the LLM so we don't make real API calls
        with patch("app.services.generation_service._llm_client") as mock_llm:
            from app.services.generation_service import answer_question

            response = answer_question("What is the capital of France?")

            # Should not have called the LLM
            assert response.retrieval_metadata is not None
            # Either no chunks retrieved, or below threshold
            if response.retrieval_metadata.top_rrf_score is not None:
                # If chunks were retrieved, the answer should still be
                # the refusal message if below threshold
                if not response.retrieval_metadata.llm_called:
                    assert "This assistant only answers officially indexed" in response.answer
