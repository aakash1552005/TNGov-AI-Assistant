"""Tests for the document chunking logic.

These tests mock the tokenizer to avoid downloading the full
embedding model during testing, while still verifying chunk
sizing, metadata attachment, and ID generation.
"""

from __future__ import annotations

from unittest.mock import patch

from ingestion.chunker import Chunk, _generate_chunk_id, chunk_pages, create_splitter


# ── Mock tokenizer to avoid model download in tests ───────────

def _mock_token_length(text: str) -> int:
    """Approximate token count: ~4 chars per token for English."""
    return max(1, len(text) // 4)


class TestGenerateChunkId:
    """Test deterministic chunk ID generation."""

    def test_same_input_same_id(self) -> None:
        id1 = _generate_chunk_id("hello world", "doc.pdf", 1)
        id2 = _generate_chunk_id("hello world", "doc.pdf", 1)
        assert id1 == id2

    def test_different_text_different_id(self) -> None:
        id1 = _generate_chunk_id("hello", "doc.pdf", 1)
        id2 = _generate_chunk_id("world", "doc.pdf", 1)
        assert id1 != id2

    def test_different_page_different_id(self) -> None:
        id1 = _generate_chunk_id("hello", "doc.pdf", 1)
        id2 = _generate_chunk_id("hello", "doc.pdf", 2)
        assert id1 != id2

    def test_is_hex_string(self) -> None:
        chunk_id = _generate_chunk_id("text", "doc.pdf", 1)
        assert len(chunk_id) == 64  # SHA-256 hex
        int(chunk_id, 16)  # Should not raise


class TestCreateSplitter:
    """Test splitter configuration."""

    @patch("ingestion.chunker._token_length", side_effect=_mock_token_length)
    def test_default_config(self, mock_len: object) -> None:
        splitter = create_splitter(chunk_size=100, chunk_overlap=20)
        # Should split long text into chunks
        long_text = "word " * 500  # ~500 tokens at 4 chars/token
        chunks = splitter.split_text(long_text)
        assert len(chunks) > 1

    @patch("ingestion.chunker._token_length", side_effect=_mock_token_length)
    def test_short_text_single_chunk(self, mock_len: object) -> None:
        splitter = create_splitter(chunk_size=100, chunk_overlap=20)
        chunks = splitter.split_text("Short text.")
        assert len(chunks) == 1


class TestChunkPages:
    """Test the chunk_pages function with metadata attachment."""

    @patch("ingestion.chunker._token_length", side_effect=_mock_token_length)
    def test_metadata_attached(self, mock_len: object) -> None:
        chunks = chunk_pages(
            page_texts=["This is a test document with enough content to form a chunk."],
            page_numbers=[1],
            scheme_name="Test Scheme",
            department="Social Welfare",
            document_name="test.pdf",
            source_url="https://example.com",
            language="en",
            last_updated="2025-01-15",
            document_hash="abc123",
            chunk_size=500,
            chunk_overlap=50,
        )
        assert len(chunks) >= 1
        chunk = chunks[0]
        assert isinstance(chunk, Chunk)
        assert chunk.scheme_name == "Test Scheme"
        assert chunk.department == "Social Welfare"
        assert chunk.document_name == "test.pdf"
        assert chunk.page_number == 1
        assert chunk.source_url == "https://example.com"
        assert chunk.language == "en"
        assert chunk.last_updated == "2025-01-15"
        assert chunk.document_hash == "abc123"
        assert chunk.chunk_id  # non-empty
        assert chunk.ingested_at  # non-empty

    @patch("ingestion.chunker._token_length", side_effect=_mock_token_length)
    def test_to_metadata_dict(self, mock_len: object) -> None:
        chunks = chunk_pages(
            page_texts=["Some text content for testing."],
            page_numbers=[3],
            scheme_name="Scheme X",
            department="Agriculture",
            document_name="doc.pdf",
            source_url="https://example.com/doc",
            language="ta",
            last_updated="2025-06-01",
            document_hash="def456",
            chunk_size=500,
            chunk_overlap=50,
        )
        meta = chunks[0].to_metadata()
        expected_keys = {
            "chunk_id", "scheme_name", "department", "document_name",
            "page_number", "source_url", "language", "last_updated",
            "document_hash", "ingested_at",
        }
        assert set(meta.keys()) == expected_keys
        assert meta["page_number"] == 3
        assert meta["language"] == "ta"

    @patch("ingestion.chunker._token_length", side_effect=_mock_token_length)
    def test_empty_page_skipped(self, mock_len: object) -> None:
        chunks = chunk_pages(
            page_texts=["", "   "],
            page_numbers=[1, 2],
            scheme_name="Test",
            department="Test",
            document_name="test.pdf",
            source_url="https://example.com",
            language="en",
            last_updated="2025-01-01",
            document_hash="ghi789",
            chunk_size=500,
            chunk_overlap=50,
        )
        assert len(chunks) == 0

    @patch("ingestion.chunker._token_length", side_effect=_mock_token_length)
    def test_multiple_pages_produce_chunks(self, mock_len: object) -> None:
        page1 = "First page content. " * 50
        page2 = "Second page content. " * 50
        chunks = chunk_pages(
            page_texts=[page1, page2],
            page_numbers=[1, 2],
            scheme_name="Multi Page Scheme",
            department="Social Welfare",
            document_name="multi.pdf",
            source_url="https://example.com",
            language="en",
            last_updated="2025-01-01",
            document_hash="jkl012",
            chunk_size=100,
            chunk_overlap=20,
        )
        assert len(chunks) > 2
        # Verify page numbers are correctly assigned
        page_nums = {c.page_number for c in chunks}
        assert 1 in page_nums
        assert 2 in page_nums
