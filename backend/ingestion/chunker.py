"""Document chunking using LangChain's RecursiveCharacterTextSplitter.

Splits cleaned page text into overlapping chunks sized by token count
(using the multilingual-e5-large tokenizer for accurate multilingual
measurement). Each chunk is annotated with full source metadata.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Lazy-loaded tokenizer ─────────────────────────────────────
_tokenizer: AutoTokenizer | None = None


def _get_tokenizer() -> AutoTokenizer:
    """Load the embedding model tokenizer on first use."""
    global _tokenizer
    if _tokenizer is None:
        logger.info("Loading tokenizer for '%s'...", settings.embedding_model)
        _tokenizer = AutoTokenizer.from_pretrained(settings.embedding_model)
    return _tokenizer


def _token_length(text: str) -> int:
    """Count tokens using the embedding model tokenizer."""
    tokenizer = _get_tokenizer()
    return len(tokenizer.encode(text, add_special_tokens=False))


# ── Chunk Data Model ──────────────────────────────────────────


@dataclass(frozen=True)
class Chunk:
    """A text chunk with full metadata for ChromaDB storage.

    Attributes:
        chunk_id: Deterministic SHA-256 hash of content + document metadata.
        text: The chunk text content.
        scheme_name: Name of the government scheme.
        department: Owning department (e.g., Social Welfare).
        document_name: Source PDF filename.
        page_number: 1-indexed page from the source PDF.
        source_url: Official URL for the source document.
        language: Language code (e.g., 'en', 'ta').
        last_updated: Date the source document was last updated.
        document_hash: SHA-256 hash of the source PDF file.
        ingested_at: ISO 8601 timestamp of when this chunk was created.
    """

    chunk_id: str
    text: str
    scheme_name: str
    department: str
    document_name: str
    page_number: int
    source_url: str
    language: str
    last_updated: str
    document_hash: str
    ingested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_metadata(self) -> dict[str, str | int]:
        """Return metadata dict for ChromaDB storage (excludes text)."""
        return {
            "chunk_id": self.chunk_id,
            "scheme_name": self.scheme_name,
            "department": self.department,
            "document_name": self.document_name,
            "page_number": self.page_number,
            "source_url": self.source_url,
            "language": self.language,
            "last_updated": self.last_updated,
            "document_hash": self.document_hash,
            "ingested_at": self.ingested_at,
        }


# ── Chunking Logic ────────────────────────────────────────────


def _generate_chunk_id(text: str, document_name: str, page_number: int) -> str:
    """Generate a deterministic chunk ID from content + location.

    This makes ingestion idempotent — re-running with the same
    documents produces the same chunk IDs, enabling upsert.
    """
    content = f"{document_name}:{page_number}:{text}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def create_splitter(
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> RecursiveCharacterTextSplitter:
    """Create a token-aware text splitter.

    Args:
        chunk_size: Target chunk size in tokens (default from config: 700).
        chunk_overlap: Overlap between chunks in tokens (default from config: 125).

    Returns:
        Configured RecursiveCharacterTextSplitter.
    """
    size = chunk_size or settings.chunk_size
    overlap = chunk_overlap or settings.chunk_overlap

    return RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        length_function=_token_length,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
        keep_separator=True,
    )


def chunk_pages(
    page_texts: list[str],
    page_numbers: list[int],
    *,
    scheme_name: str,
    department: str,
    document_name: str,
    source_url: str,
    language: str,
    last_updated: str,
    document_hash: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """Split cleaned page texts into metadata-annotated chunks.

    Args:
        page_texts: Cleaned text content per page.
        page_numbers: Corresponding 1-indexed page numbers.
        scheme_name: Government scheme name.
        department: Owning department.
        document_name: Source PDF filename.
        source_url: Official URL for the document.
        language: Language code.
        last_updated: Date string for when the document was last updated.
        document_hash: SHA-256 hash of the source PDF file.
        chunk_size: Optional override for chunk size in tokens.
        chunk_overlap: Optional override for chunk overlap in tokens.

    Returns:
        List of Chunk objects with full metadata attached.
    """
    splitter = create_splitter(chunk_size, chunk_overlap)
    ingested_at = datetime.now(timezone.utc).isoformat()
    chunks: list[Chunk] = []

    for text, page_num in zip(page_texts, page_numbers):
        if not text.strip():
            continue

        split_texts = splitter.split_text(text)

        for fragment in split_texts:
            chunk_id = _generate_chunk_id(fragment, document_name, page_num)
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    text=fragment,
                    scheme_name=scheme_name,
                    department=department,
                    document_name=document_name,
                    page_number=page_num,
                    source_url=source_url,
                    language=language,
                    last_updated=last_updated,
                    document_hash=document_hash,
                    ingested_at=ingested_at,
                )
            )

    logger.info(
        "Chunked '%s' into %d chunks (from %d pages)",
        document_name,
        len(chunks),
        len(page_texts),
    )
    return chunks
