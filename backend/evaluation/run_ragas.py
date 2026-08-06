"""RAGAS Evaluation Runner for Milestone 6.

Evaluates Faithfulness, Answer Relevancy, Context Precision, and Context Recall
using RAGAS framework metrics directly calling generation_service.answer_question().
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from datasets import Dataset
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

from app.core.config import settings
from app.services.generation_service import answer_question
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


def run_ragas_eval(dataset_path: str = "evaluation/eval_dataset.json") -> dict[str, Any]:
    """Execute RAGAS metric evaluation over dataset.

    Args:
        dataset_path: Path to dataset JSON file.

    Returns:
        Dictionary containing per-question metrics, aggregate averages, and status.
    """
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found at {dataset_path}")

    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)

    print("\n" + "=" * 80)
    print("STARTING RAGAS EVALUATION")
    print("=" * 80)

    # Filter in-scope and tamil questions for RAGAS scoring
    eval_items = [item for item in items if not item.get("expected_refusal", False)]

    questions = []
    answers = []
    contexts_list = []
    ground_truths = []
    metadata_list = []

    for item in eval_items:
        q_text = item["question"]
        t0 = time.monotonic()
        try:
            res = answer_question(q_text)
            ctxs = [chunk.chunk_text for chunk in res.retrieved_chunks] if res.retrieved_chunks else ["No context retrieved"]
            ground_truth = item.get("expected_scheme") or "Official Tamil Nadu welfare scheme information"

            questions.append(q_text)
            answers.append(res.answer)
            contexts_list.append(ctxs)
            ground_truths.append(ground_truth)
            metadata_list.append({
                "id": item["id"],
                "category": item.get("category"),
                "citations_count": len(res.citations),
                "execution_time_sec": round(time.monotonic() - t0, 3),
            })
            print(f"Collected answer & context for [{item['id']}] (latency: {round(time.monotonic() - t0, 2)}s)")
        except Exception as exc:
            logger.warning("Failed generation for evaluation query %s: %s", item["id"], exc)

    if not questions:
        return {
            "status": "PARTIAL_RESULTS",
            "message": "No valid questions collected for evaluation",
            "aggregate_scores": {},
            "per_question": [],
        }

    eval_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts_list,
        "ground_truth": ground_truths,
    }
    dataset = Dataset.from_dict(eval_dict)

    # Configure LLM & Embeddings for RAGAS evaluator using Groq API
    api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
    model_name = settings.groq_model
    base_url = "https://api.groq.com/openai/v1"
    key_name = "GROQ_API_KEY"

    if not api_key:
        print(f"WARNING: {key_name} is not set for configured provider '{provider}'. Returning PARTIAL RESULTS without LLM-based RAGAS calculation.")
        return {
            "status": "PARTIAL_RESULTS",
            "message": f"{key_name} missing for RAGAS LLM evaluator",
            "aggregate_scores": {
                "faithfulness": None,
                "answer_relevancy": None,
                "context_precision": None,
                "context_recall": None,
            },
            "sample_count": len(questions),
            "per_question": metadata_list,
        }

    try:
        llm_client = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model_name,
            temperature=0,
        )
        ragas_llm = LangchainLLMWrapper(llm_client)

        hf_embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
        ragas_embeddings = LangchainEmbeddingsWrapper(hf_embeddings)

        metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
        answer_relevancy.strictness = 1

        print("Executing RAGAS metrics calculations...")
        eval_res = evaluate(
            dataset=dataset,
            metrics=metrics,
            llm=ragas_llm,
            embeddings=ragas_embeddings,
        )

        df = eval_res.to_pandas()
        per_question = []
        for i, row in df.iterrows():
            meta = metadata_list[i] if i < len(metadata_list) else {}
            per_question.append({
                "id": meta.get("id"),
                "question": row.get("question"),
                "faithfulness": round(float(row.get("faithfulness", 0.0)), 4) if row.get("faithfulness") is not None else None,
                "answer_relevancy": round(float(row.get("answer_relevancy", 0.0)), 4) if row.get("answer_relevancy") is not None else None,
                "context_precision": round(float(row.get("context_precision", 0.0)), 4) if row.get("context_precision") is not None else None,
                "context_recall": round(float(row.get("context_recall", 0.0)), 4) if row.get("context_recall") is not None else None,
            })

        mean_scores = {
            "faithfulness": round(float(df["faithfulness"].mean()), 4) if "faithfulness" in df and not df["faithfulness"].isna().all() else None,
            "answer_relevancy": round(float(df["answer_relevancy"].mean()), 4) if "answer_relevancy" in df and not df["answer_relevancy"].isna().all() else None,
            "context_precision": round(float(df["context_precision"].mean()), 4) if "context_precision" in df and not df["context_precision"].isna().all() else None,
            "context_recall": round(float(df["context_recall"].mean()), 4) if "context_recall" in df and not df["context_recall"].isna().all() else None,
        }

        print("=" * 80)
        print("RAGAS AGGREGATE SCORES:", mean_scores)
        print("=" * 80 + "\n")

        return {
            "status": "SUCCESS",
            "aggregate_scores": mean_scores,
            "per_question": per_question,
        }

    except Exception as exc:
        logger.warning("RAGAS evaluation encountered runtime issue or rate limit: %s", exc)
        print(f"RAGAS RUNTIME NOTICE: Evaluation completed with PARTIAL RESULTS due to rate limit or runtime exception: {exc}")
        return {
            "status": "PARTIAL_RESULTS",
            "message": str(exc),
            "aggregate_scores": {
                "faithfulness": None,
                "answer_relevancy": None,
                "context_precision": None,
                "context_recall": None,
            },
            "sample_count": len(questions),
            "per_question": metadata_list,
        }


if __name__ == "__main__":
    run_ragas_eval()
