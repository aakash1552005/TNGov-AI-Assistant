"""Retrieval-only evaluation script for TNGov-AI-Assistant.

Evaluates BM25-only, Dense-only (ChromaDB), and Hybrid (BM25 + Dense with RRF)
across the 50 benchmark queries without any LLM calls or paid APIs.

Features fair latency measurement (single shared service instance, identical
ID-to-metadata hydration across methods), 95% bootstrap confidence intervals,
and isolated execution against a temporary copy of backend/seed_data.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import platform
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# Ensure project root and backend are on PYTHONPATH
project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

# ── Isolate Seed Data to Temp Directory ───────────────────────
temp_data_dir = Path(tempfile.gettempdir()) / "tngov_eval_seed_data"
if temp_data_dir.exists():
    shutil.rmtree(temp_data_dir, ignore_errors=True)

seed_source = backend_dir / "seed_data"
shutil.copytree(seed_source, temp_data_dir)

os.environ["CHROMA_DB_PATH"] = str(temp_data_dir / "chroma_db")
os.environ["BM25_INDEX_PATH"] = str(temp_data_dir / "bm25_index.json")
os.environ["EMBEDDING_MODEL"] = "intfloat/multilingual-e5-large"

logging.basicConfig(level=logging.WARNING)

import numpy as np
import psutil
import torch
from app.core.config import settings
settings.chroma_db_path = str(temp_data_dir / "chroma_db")
settings.bm25_index_path = str(temp_data_dir / "bm25_index.json")
settings.embedding_model = "intfloat/multilingual-e5-large"
from app.rag import bm25_index, vector_store
from app.rag.query_expander import expand_query
from app.rag.retrieval_models import RetrievedChunk
from app.rag.retrieval_service import RetrievalService
from backend.evaluation.benchmark_50_eval import BENCHMARK_50_SUITE
from ingestion.embedder import embed_query

# ── Singleton Instances Outside Timed Loops ──────────────────
_RETRIEVAL_SVC = RetrievalService()
_COLLECTION = vector_store.get_collection()


def get_hardware_info() -> dict[str, Any]:
    """Measure and return detailed hardware specifications."""
    cpu_processor = platform.processor() or "Unknown"
    phys_cores = psutil.cpu_count(logical=False) or 0
    log_cores = psutil.cpu_count(logical=True) or 0
    total_ram_gb = round(psutil.virtual_memory().total / (1024**3), 2)
    torch_threads = torch.get_num_threads()
    os_info = f"{platform.system()} {platform.release()}"

    return {
        "cpu": cpu_processor,
        "physical_cores": phys_cores,
        "logical_cores": log_cores,
        "total_ram_gb": total_ram_gb,
        "torch_threads": torch_threads,
        "os": os_info,
    }


def _hydrate_chunks(
    chunk_ids: list[str],
    scores: list[float],
    score_type: str,
) -> list[RetrievedChunk]:
    """Hydrate chunk IDs to RetrievedChunk objects using batched ChromaDB get."""
    if not chunk_ids:
        return []

    res = _COLLECTION.get(ids=chunk_ids, include=["metadatas", "documents"])
    meta_map = {cid: meta for cid, meta in zip(res["ids"], res["metadatas"])}
    doc_map = {cid: doc for cid, doc in zip(res["ids"], res["documents"])}

    chunks: list[RetrievedChunk] = []
    for rank, (cid, score) in enumerate(zip(chunk_ids, scores), start=1):
        chunk_kwargs = {
            "chunk_id": cid,
            "chunk_text": doc_map.get(cid, ""),
            "metadata": meta_map.get(cid, {}),
            "vector_score": score if score_type == "vector" else None,
            "bm25_score": score if score_type == "bm25" else None,
            "rrf_score": 0.0,
            "final_rank": rank,
        }
        chunks.append(RetrievedChunk(**chunk_kwargs))
    return chunks


def search_bm25_only(query: str, top_k: int = 5) -> list[RetrievedChunk]:
    """BM25-only retrieval with batched metadata hydration."""
    search_query = expand_query(query)
    bm25_hits = bm25_index.search(search_query, top_k=top_k)
    chunk_ids = [cid for cid, _ in bm25_hits]
    scores = [score for _, score in bm25_hits]
    return _hydrate_chunks(chunk_ids, scores, score_type="bm25")


def search_dense_only(query: str, top_k: int = 5) -> list[RetrievedChunk]:
    """Dense-only retrieval with batched metadata hydration."""
    search_query = expand_query(query)
    query_embedding = embed_query(search_query)
    vector_results = vector_store.query_similar(query_embedding, top_k=top_k)

    chunk_ids = vector_results["ids"][0] if vector_results and vector_results.get("ids") else []
    distances = vector_results["distances"][0] if vector_results and vector_results.get("distances") else []
    return _hydrate_chunks(chunk_ids, distances, score_type="vector")


def search_hybrid(query: str, top_k: int = 5) -> list[RetrievedChunk]:
    """Production Hybrid RRF retrieval path."""
    return _RETRIEVAL_SVC.retrieve(query)[:top_k]


def is_chunk_relevant(chunk: RetrievedChunk, expected_scheme: str | None) -> bool:
    """Relevance check: chunk scheme_name matches expected target scheme."""
    if not expected_scheme:
        return False
    scheme_name = str(chunk.metadata.get("scheme_name", ""))
    return scheme_name == expected_scheme or expected_scheme.lower() in scheme_name.lower()


def evaluate_query(
    query_item: dict[str, Any], retriever_func: Any, top_k: int = 5
) -> dict[str, Any]:
    """Evaluate a single query against a retriever function."""
    qtext = query_item["q"]
    exp_scheme = query_item["scheme"]

    chunks = retriever_func(qtext, top_k=top_k)

    matched_rank = 0
    for idx, chunk in enumerate(chunks, start=1):
        if is_chunk_relevant(chunk, exp_scheme):
            if matched_rank == 0:
                matched_rank = idx

    rr = (1.0 / matched_rank) if matched_rank > 0 else 0.0
    hit_at_5 = 1.0 if (1 <= matched_rank <= 5) else 0.0
    hit_at_4 = 1.0 if (1 <= matched_rank <= 4) else 0.0

    return {
        "matched_rank": matched_rank,
        "rr": rr,
        "hit_at_5": hit_at_5,
        "hit_at_4": hit_at_4,
        "chunks_count": len(chunks),
    }


def bootstrap_ci(
    data: list[float], n_bootstrap: int = 1000, ci: float = 0.95
) -> tuple[float, float, float]:
    """Compute mean and 95% bootstrap confidence interval."""
    if not data:
        return 0.0, 0.0, 0.0
    arr = np.array(data)
    mean_val = float(np.mean(arr))
    rng = np.random.default_rng(42)
    boot_means = [
        float(np.mean(rng.choice(arr, size=len(arr), replace=True)))
        for _ in range(n_bootstrap)
    ]
    lower = float(np.percentile(boot_means, (1.0 - ci) / 2.0 * 100))
    upper = float(np.percentile(boot_means, (1.0 + ci) / 2.0 * 100))
    return mean_val, lower, upper


def measure_latencies(
    retriever_func: Any, queries: list[str], n_repeats: int = 3, n_warmup: int = 5
) -> tuple[float, float]:
    """Measure P50 and P95 latency in ms after warm-up across N repeats."""
    for q in queries[:n_warmup]:
        retriever_func(q, top_k=5)

    timings = []
    for _ in range(n_repeats):
        for q in queries:
            t0 = time.perf_counter()
            retriever_func(q, top_k=5)
            t_ms = (time.perf_counter() - t0) * 1000.0
            timings.append(t_ms)

    p50 = float(np.percentile(timings, 50))
    p95 = float(np.percentile(timings, 95))
    return p50, p95


def run_evaluation() -> dict[str, Any]:
    """Run full benchmark evaluation."""
    queries = BENCHMARK_50_SUITE
    all_qtexts = [item["q"] for item in queries]
    target_queries = [item for item in queries if item["scheme"] is not None]
    refusal_queries = [item for item in queries if item["scheme"] is None]

    methods = {
        "BM25-only": search_bm25_only,
        "Dense-only": search_dense_only,
        "Hybrid": search_hybrid,
    }

    raw_results: list[dict[str, Any]] = []

    for item in queries:
        row: dict[str, Any] = {
            "id": item["id"],
            "cat": item["cat"],
            "query": item["q"],
            "expected_scheme": item["scheme"] or "[REFUSAL]",
            "is_refusal": item.get("refusal", False),
        }
        for name, fn in methods.items():
            res = evaluate_query(item, fn, top_k=5)
            row[f"{name}_rank"] = res["matched_rank"] if res["matched_rank"] > 0 else "N/A"
            row[f"{name}_rr"] = round(res["rr"], 4)
            row[f"{name}_hit@4"] = int(res["hit_at_4"])
            row[f"{name}_hit@5"] = int(res["hit_at_5"])
            row[f"{name}_chunks_returned"] = res["chunks_count"]

        # Head-to-head comparison
        h_rr = row["Hybrid_rr"]
        d_rr = row["Dense-only_rr"]
        if h_rr > d_rr:
            row["hybrid_vs_dense"] = "BETTER"
        elif h_rr == d_rr:
            row["hybrid_vs_dense"] = "EQUAL"
        else:
            row["hybrid_vs_dense"] = "WORSE"

        raw_results.append(row)

    # Save raw CSV
    reports_dir = project_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    csv_path = reports_dir / "retrieval_eval_results.csv"

    fieldnames = list(raw_results[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(raw_results)

    # Scored target queries
    scored = [r for r in raw_results if not r["is_refusal"]]
    en_scored = [r for r in scored if r["cat"] != "Tamil"]
    ta_scored = [r for r in scored if r["cat"] == "Tamil"]

    def summarize_slice(subset: list[dict[str, Any]]) -> dict[str, Any]:
        res: dict[str, Any] = {}
        for name in methods:
            hit4_vals = [float(r[f"{name}_hit@4"]) for r in subset]
            hit5_vals = [float(r[f"{name}_hit@5"]) for r in subset]
            rr_vals = [float(r[f"{name}_rr"]) for r in subset]

            hit4_m, hit4_l, hit4_h = bootstrap_ci(hit4_vals)
            hit5_m, hit5_l, hit5_h = bootstrap_ci(hit5_vals)
            mrr_m, mrr_l, mrr_h = bootstrap_ci(rr_vals)

            res[name] = {
                "hit@4": (round(hit4_m, 4), round(hit4_l, 4), round(hit4_h, 4)),
                "hit@5": (round(hit5_m, 4), round(hit5_l, 4), round(hit5_h, 4)),
                "mrr": (round(mrr_m, 4), round(mrr_l, 4), round(mrr_h, 4)),
                "correct_at_4": f"{int(sum(hit4_vals))}/{len(subset)}",
                "correct_at_5": f"{int(sum(hit5_vals))}/{len(subset)}",
            }
        return res

    summary_overall = summarize_slice(scored)
    summary_en = summarize_slice(en_scored)
    summary_ta = summarize_slice(ta_scored)

    # Latencies
    for name in methods:
        p50, p95 = measure_latencies(methods[name], all_qtexts, n_repeats=3, n_warmup=5)
        avg_chunks = float(np.mean([r[f"{name}_chunks_returned"] for r in scored]))
        summary_overall[name]["latency_p50_ms"] = round(p50, 2)
        summary_overall[name]["latency_p95_ms"] = round(p95, 2)
        summary_overall[name]["avg_chunks_returned"] = round(avg_chunks, 2)

    better_count = sum(1 for r in scored if r["hybrid_vs_dense"] == "BETTER")
    equal_count = sum(1 for r in scored if r["hybrid_vs_dense"] == "EQUAL")
    worse_count = sum(1 for r in scored if r["hybrid_vs_dense"] == "WORSE")

    shutil.rmtree(temp_data_dir, ignore_errors=True)
    hardware = get_hardware_info()

    return {
        "summary": summary_overall,
        "language_breakdown": {
            "english_30": summary_en,
            "tamil_10": summary_ta,
        },
        "hybrid_vs_dense": {
            "better": better_count,
            "equal": equal_count,
            "worse": worse_count,
        },
        "total_queries": len(queries),
        "scored_queries": len(target_queries),
        "excluded_refusal_queries": len(refusal_queries),
        "csv_path": str(csv_path),
        "hardware": hardware,
        "raw_results": raw_results,
    }


if __name__ == "__main__":
    print("Running retrieval evaluation...")
    out = run_evaluation()
    print("EVAL_SUMMARY_START")
    print(json.dumps(out, indent=2))
    print("EVAL_SUMMARY_END")
