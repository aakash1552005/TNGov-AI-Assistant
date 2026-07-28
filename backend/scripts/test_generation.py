"""End-to-end demo: retrieval → generation pipeline.

Usage::

    cd backend
    python scripts/test_generation.py

Requires:
- ChromaDB populated with ingested documents (run `make ingest` first)
- BM25 index built (automatically built after ingestion)
- OPENAI_API_KEY set in .env or environment

This script demonstrates the complete pipeline:
  question → hybrid retrieval → relevance check → GPT-4.1 → cited answer
"""

from __future__ import annotations

import logging
import os
import sys

# Ensure backend/ is on sys.path so `app` is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Force UTF-8 output on Windows (avoids cp1252 encoding errors with emoji)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Set up logging so retrieval diagnostics are visible
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

# Suppress noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)


def main() -> None:
    from app.core.config import settings
    from app.services.generation_service import answer_question

    print(f"Running generation test with LLM Provider: {settings.llm_provider}")

    # ── Test Questions ────────────────────────────────────────
    questions = [
        "What are the eligibility criteria for the Chief Minister's Comprehensive Health Insurance Scheme?",
        "முதலமைச்சரின் விரிவான மருத்துவக் காப்பீட்டுத் திட்டத்தின் தகுதி என்ன?",
        "What are the benefits under the Prime Minister's Employment Generation Programme (PMEGP)?",
        "What is the capital of France?",  # Out-of-scope
    ]

    for i, question in enumerate(questions, start=1):
        print(f"\n{'=' * 70}")
        print(f"QUESTION {i}: {question}")
        print("=" * 70)

        response = answer_question(question)

        # Answer
        print(f"\nANSWER:\n{response.answer}")

        # Citations
        if response.citations:
            print(f"\nCITATIONS ({len(response.citations)}):")
            for j, cite in enumerate(response.citations, 1):
                print(f"  [{j}] {cite.scheme_name} | {cite.document_name} | "
                      f"Page {cite.page_number} | {cite.source_url}")
                if cite.excerpt:
                    print(f"      Excerpt: {cite.excerpt[:100]}...")

        # Retrieval Metadata
        meta = response.retrieval_metadata
        if meta:
            print(f"\nRETRIEVAL METADATA:")
            print(f"  Total retrieved : {meta.total_retrieved}")
            print(f"  Top RRF score   : {meta.top_rrf_score}")
            print(f"  Vector results  : {meta.vector_results_count}")
            print(f"  BM25 results    : {meta.bm25_results_count}")
            print(f"  LLM called      : {meta.llm_called}")

        # Retrieved chunks (scores only)
        if response.retrieved_chunks:
            print(f"\nRETRIEVED CHUNKS ({len(response.retrieved_chunks)}):")
            for chunk in response.retrieved_chunks:
                print(
                    f"  rank={chunk.final_rank}  rrf={chunk.rrf_score:.4f}  "
                    f"vector={chunk.vector_score if chunk.vector_score is not None else 'N/A':>8}  "
                    f"bm25={chunk.bm25_score if chunk.bm25_score is not None else 'N/A':>8}  "
                    f"scheme={chunk.metadata.get('scheme_name', '?')}"
                )

        print("-" * 70)


if __name__ == "__main__":
    main()
