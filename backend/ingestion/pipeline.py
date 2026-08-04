"""Ingestion pipeline orchestrator.

Coordinates the full document ingestion flow:
  source_log.json → PDF loading → cleaning → chunking → embedding → ChromaDB

Supports incremental ingestion: computes a SHA-256 hash of each source
PDF and skips files that have not changed since the last ingestion.

Persists extracted page text as intermediate artifacts in data/extracted/
so PDFs don't need to be re-parsed if cleaning or chunking logic changes.

Writes a timestamped ingestion manifest to logs/ after each run.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.rag import vector_store
from ingestion import cleaner, chunker, embedder

logger = logging.getLogger(__name__)

# ── Hash Tracking ─────────────────────────────────────────────

_HASH_FILE = "ingested_hashes.json"


def _hash_file(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            sha256.update(block)
    return sha256.hexdigest()


def _load_hash_registry(data_dir: Path) -> dict[str, str]:
    """Load previously ingested file hashes.

    Returns:
        Dict mapping filename → SHA-256 hash.
    """
    hash_file = data_dir / "metadata" / _HASH_FILE
    if hash_file.exists():
        with open(hash_file) as f:
            return json.load(f)
    return {}


def _save_hash_registry(data_dir: Path, registry: dict[str, str]) -> None:
    """Persist the hash registry to disk."""
    hash_file = data_dir / "metadata" / _HASH_FILE
    hash_file.parent.mkdir(parents=True, exist_ok=True)
    with open(hash_file, "w") as f:
        json.dump(registry, f, indent=2)


# ── Source Log ────────────────────────────────────────────────


@dataclass
class DocumentEntry:
    """A single entry from the source metadata log."""

    file_name: str
    scheme_name: str
    department: str
    source_url: str
    language: str
    last_updated: str


def load_source_log(metadata_file: Path) -> list[DocumentEntry]:
    """Load and validate the source metadata log.

    Args:
        metadata_file: Path to source_log.json.

    Returns:
        List of DocumentEntry objects.

    Raises:
        FileNotFoundError: If the metadata file does not exist.
        ValueError: If any required fields are missing.
    """
    if not metadata_file.exists():
        raise FileNotFoundError(f"Source log not found: {metadata_file}")

    with open(metadata_file) as f:
        entries = json.load(f)

    required_fields = {"file_name", "scheme_name", "department", "source_url", "language", "last_updated"}
    documents: list[DocumentEntry] = []

    for i, entry in enumerate(entries):
        missing = required_fields - set(entry.keys())
        if missing:
            raise ValueError(
                f"Entry {i} in source_log.json is missing required fields: {missing}"
            )
        documents.append(DocumentEntry(**{k: entry[k] for k in required_fields}))

    return documents


# ── Pipeline Results ──────────────────────────────────────────


@dataclass
class IngestResult:
    """Summary of a single document's ingestion."""

    file_name: str
    pages_extracted: int
    chunks_created: int
    status: str  # "ingested", "skipped", "error"
    error: str | None = None


@dataclass
class PipelineResult:
    """Summary of the full pipeline run."""

    total_documents: int
    ingested: int
    skipped: int
    errors: int
    total_chunks: int
    total_pages: int
    duration_seconds: float
    results: list[IngestResult]


# ── Main Pipeline ─────────────────────────────────────────────


def run_pipeline(
    data_dir: Path | None = None,
    metadata_file: Path | None = None,
    force: bool = False,
) -> PipelineResult:
    """Execute the full ingestion pipeline.

    Args:
        data_dir: Root data directory (default from config).
        metadata_file: Path to source_log.json (default: data_dir/metadata/source_log.json).
        force: If True, re-ingest all documents regardless of hash.

    Returns:
        PipelineResult with per-document summaries and totals.
    """
    start_time = time.monotonic()
    data_path = Path(data_dir) if data_dir else Path(settings.data_dir)
    raw_dir = data_path / "raw_documents"
    meta_file = metadata_file or (data_path / "metadata" / "source_log.json")

    # Ensure extracted text output directory exists
    extracted_dir = data_path / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting ingestion pipeline")
    logger.info("Data directory: %s", data_path)
    logger.info("Metadata file: %s", meta_file)

    # Load source metadata
    entries = load_source_log(meta_file)
    logger.info("Found %d documents in source log", len(entries))

    # Load hash registry for incremental ingestion
    hash_registry = _load_hash_registry(data_path)
    results: list[IngestResult] = []
    total_chunks = 0

    for entry in entries:
        pdf_path = raw_dir / entry.file_name
        stem = Path(entry.file_name).stem
        json_path = extracted_dir / f"{stem}.json"

        target_file = json_path if json_path.exists() else (pdf_path if pdf_path.exists() else None)

        if not target_file:
            logger.error("Neither PDF nor Extracted JSON found for: %s — skipping", entry.file_name)
            results.append(IngestResult(
                file_name=entry.file_name,
                pages_extracted=0,
                chunks_created=0,
                status="error",
                error=f"File not found: {pdf_path} or {json_path}",
            ))
            continue

        # Check if document has changed (SHA-256 incremental ingestion)
        current_hash = _hash_file(target_file)
        if not force and hash_registry.get(entry.file_name) == current_hash:
            logger.info("'%s' unchanged (hash match) — skipping", entry.file_name)
            results.append(IngestResult(
                file_name=entry.file_name,
                pages_extracted=0,
                chunks_created=0,
                status="skipped",
            ))
            continue

        # Process the document
        try:
            result = _ingest_document(entry, target_file, current_hash, extracted_dir)
            total_chunks += result.chunks_created
            results.append(result)

            # Update hash registry on success
            hash_registry[entry.file_name] = current_hash

        except Exception as exc:
            logger.exception("Failed to ingest '%s'", entry.file_name)
            results.append(IngestResult(
                file_name=entry.file_name,
                pages_extracted=0,
                chunks_created=0,
                status="error",
                error=str(exc),
            ))

    # Persist updated hashes
    _save_hash_registry(data_path, hash_registry)

    duration = time.monotonic() - start_time
    ingested = sum(1 for r in results if r.status == "ingested")
    skipped = sum(1 for r in results if r.status == "skipped")
    errors = sum(1 for r in results if r.status == "error")
    total_pages = sum(r.pages_extracted for r in results)

    logger.info(
        "Pipeline complete: %d ingested, %d skipped, %d errors, %d total chunks (%.1fs)",
        ingested, skipped, errors, total_chunks, duration,
    )

    pipeline_result = PipelineResult(
        total_documents=len(entries),
        ingested=ingested,
        skipped=skipped,
        errors=errors,
        total_chunks=total_chunks,
        total_pages=total_pages,
        duration_seconds=round(duration, 2),
        results=results,
    )

    # Write ingestion manifest
    _write_manifest(data_path, pipeline_result)

    # Rebuild BM25 index if any documents changed
    if ingested > 0:
        from app.rag.bm25_index import rebuild_bm25_index

        bm25_count = rebuild_bm25_index()
        logger.info("BM25 index rebuilt: %d chunks indexed", bm25_count)
    else:
        logger.info("No documents changed — reusing existing BM25 index")

    return pipeline_result


def _ingest_document(
    entry: DocumentEntry,
    target_path: Path,
    document_hash: str,
    extracted_dir: Path,
) -> IngestResult:
    """Ingest a single document (PDF or Extracted JSON) through the full pipeline."""
    logger.info("Ingesting '%s' (%s / %s)", entry.file_name, entry.department, entry.scheme_name)

    page_texts: list[str] = []
    page_numbers: list[int] = []

    if target_path.suffix.lower() == ".pdf" and target_path.exists():
        from ingestion import pdf_loader
        pages = pdf_loader.load_pdf(target_path)
        if not pages:
            logger.warning("No text extracted from '%s'", entry.file_name)
            return IngestResult(
                file_name=entry.file_name,
                pages_extracted=0,
                chunks_created=0,
                status="ingested",
            )
        _save_extracted_text(pages, entry.file_name, extracted_dir)
        page_texts = [p.text for p in pages]
        page_numbers = [p.page_number for p in pages]
    elif target_path.suffix.lower() == ".json" and target_path.exists():
        with open(target_path, encoding="utf-8") as f:
            data = json.load(f)
        for page in data.get("pages", []):
            page_texts.append(page.get("text", ""))
            page_numbers.append(page.get("page_number", 1))
    else:
        raise FileNotFoundError(f"Unsupported or missing target file: {target_path}")

    # 2. Clean text (with cross-page header/footer detection)
    cleaned_texts = cleaner.clean_pages(page_texts)

    # 3. Chunk with metadata
    chunks = chunker.chunk_pages(
        page_texts=cleaned_texts,
        page_numbers=page_numbers,
        scheme_name=entry.scheme_name,
        department=entry.department,
        document_name=entry.file_name,
        source_url=entry.source_url,
        language=entry.language,
        last_updated=entry.last_updated,
        document_hash=document_hash,
    )

    if not chunks:
        logger.warning("No chunks created from '%s'", entry.file_name)
        return IngestResult(
            file_name=entry.file_name,
            pages_extracted=len(page_texts),
            chunks_created=0,
            status="ingested",
        )

    # 4. Generate embeddings
    chunk_texts = [c.text for c in chunks]
    embeddings = embedder.embed_passages(chunk_texts)

    # 5. Upsert into ChromaDB
    vector_store.upsert_chunks(chunks, embeddings)

    logger.info(
        "Ingested '%s': %d pages → %d chunks → stored in ChromaDB",
        entry.file_name, len(page_texts), len(chunks),
    )

    return IngestResult(
        file_name=entry.file_name,
        pages_extracted=len(page_texts),
        chunks_created=len(chunks),
        status="ingested",
    )


# ── Intermediate Artifact Persistence ─────────────────────────


def _save_extracted_text(
    pages: list[pdf_loader.PageContent],
    file_name: str,
    extracted_dir: Path,
) -> None:
    """Persist raw extracted page text as a JSON artifact.

    Saves one file per source document in ``data/extracted/`` with
    page boundaries preserved. This avoids re-parsing the PDF if
    cleaning or chunking logic changes later.

    Args:
        pages: List of PageContent objects from the PDF loader.
        file_name: Original PDF filename (used to derive output name).
        extracted_dir: Directory to save the extracted text file.
    """
    stem = Path(file_name).stem
    output_path = extracted_dir / f"{stem}.json"

    extracted = {
        "document_name": file_name,
        "total_pages": len(pages),
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "pages": [
            {
                "page_number": page.page_number,
                "text": page.text,
            }
            for page in pages
        ],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extracted, f, indent=2, ensure_ascii=False)

    logger.info("Saved extracted text to '%s'", output_path)


# ── Ingestion Manifest ───────────────────────────────────────


def _write_manifest(data_path: Path, result: PipelineResult) -> None:
    """Write a timestamped ingestion manifest to logs/.

    The manifest captures everything needed to audit and reproduce
    the ingestion run: document counts, chunk counts, model used,
    pipeline version, and duration.

    Args:
        data_path: Root data directory (logs/ is created as a sibling).
        result: The completed pipeline result.
    """
    # logs/ lives at the project root level, alongside data/
    logs_dir = data_path.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    manifest_path = logs_dir / f"ingestion_{timestamp}.json"

    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_documents": result.total_documents,
        "documents_ingested": result.ingested,
        "documents_skipped": result.skipped,
        "documents_errored": result.errors,
        "total_pages_extracted": result.total_pages,
        "total_chunks_created": result.total_chunks,
        "embedding_model": settings.embedding_model,
        "pipeline_version": settings.pipeline_version,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "embedding_batch_size": settings.embedding_batch_size,
        "duration_seconds": result.duration_seconds,
        "documents": [
            {
                "file_name": r.file_name,
                "status": r.status,
                "pages_extracted": r.pages_extracted,
                "chunks_created": r.chunks_created,
                "error": r.error,
            }
            for r in result.results
        ],
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    logger.info("Ingestion manifest written to '%s'", manifest_path)
