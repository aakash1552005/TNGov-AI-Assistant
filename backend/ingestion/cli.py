"""Command-line interface for the ingestion pipeline.

Provides three commands:
- ``ingest``: Run the full ingestion pipeline
- ``stats``:  Show ChromaDB collection statistics
- ``clear``:  Clear the ChromaDB collection

Usage::

    python -m ingestion.cli ingest [--data-dir PATH] [--force]
    python -m ingestion.cli stats
    python -m ingestion.cli clear
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# ── Logging Setup ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Commands ──────────────────────────────────────────────────


def cmd_ingest(args: argparse.Namespace) -> None:
    """Run the full ingestion pipeline."""
    from ingestion.pipeline import run_pipeline

    data_dir = Path(args.data_dir) if args.data_dir else None
    metadata_file = Path(args.metadata_file) if args.metadata_file else None

    result = run_pipeline(
        data_dir=data_dir,
        metadata_file=metadata_file,
        force=args.force,
    )

    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    print(f"  Total documents : {result.total_documents}")
    print(f"  Ingested        : {result.ingested}")
    print(f"  Skipped (cached): {result.skipped}")
    print(f"  Errors          : {result.errors}")
    print(f"  Total pages     : {result.total_pages}")
    print(f"  Total chunks    : {result.total_chunks}")
    print(f"  Duration        : {result.duration_seconds}s")
    print("-" * 60)

    for r in result.results:
        status_icon = {"ingested": "[OK]", "skipped": "[SKIP]", "error": "[FAIL]"}.get(r.status, "[?]")
        line = f"  {status_icon} {r.file_name} — {r.status}"
        if r.status == "ingested":
            line += f" ({r.pages_extracted} pages, {r.chunks_created} chunks)"
        if r.error:
            line += f" — {r.error}"
        print(line)

    print("=" * 60)

    if result.errors > 0:
        sys.exit(1)


def cmd_stats(args: argparse.Namespace) -> None:
    """Show ChromaDB collection statistics."""
    from app.rag.vector_store import get_stats

    stats = get_stats()

    print("\n" + "=" * 60)
    print("CHROMADB COLLECTION STATS")
    print("=" * 60)
    print(f"  Collection name : {stats['collection_name']}")
    print(f"  Chunk count     : {stats['chunk_count']}")
    print(f"  Metadata        : {stats['metadata']}")
    print("=" * 60)


def cmd_clear(args: argparse.Namespace) -> None:
    """Clear the ChromaDB collection."""
    from app.rag.vector_store import clear_collection

    if not args.yes:
        confirm = input("This will delete ALL stored chunks. Continue? [y/N] ")
        if confirm.lower() != "y":
            print("Aborted.")
            return

    clear_collection()
    print("Collection cleared and recreated.")


# ── Argument Parser ───────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="ingestion",
        description="TN Gov AI Assistant — Document Ingestion Pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ingest
    ingest_parser = subparsers.add_parser("ingest", help="Run the ingestion pipeline")
    ingest_parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Root data directory (default: from config)",
    )
    ingest_parser.add_argument(
        "--metadata-file",
        type=str,
        default=None,
        help="Path to source_log.json (default: data_dir/metadata/source_log.json)",
    )
    ingest_parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-ingestion of all documents (ignore hash cache)",
    )
    ingest_parser.set_defaults(func=cmd_ingest)

    # stats
    stats_parser = subparsers.add_parser("stats", help="Show collection statistics")
    stats_parser.set_defaults(func=cmd_stats)

    # clear
    clear_parser = subparsers.add_parser("clear", help="Clear the collection")
    clear_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    clear_parser.set_defaults(func=cmd_clear)

    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
