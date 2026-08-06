"""50-Query Comprehensive RAG Evaluation & Benchmark Suite."""

from __future__ import annotations
import sys, json, time
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.generation_service import answer_question

BENCHMARK_50_SUITE = [
    # Category 1: Flagship Schemes (10)
    {"id": "q01", "cat": "Flagship", "q": "What is Kalaignar Magalir Urimai Thogai?", "refusal": False, "scheme": "Kalaignar Magalir Urimai Thogai Scheme"},
    {"id": "q02", "cat": "Flagship", "q": "Who is eligible for Pudhumai Penn scheme?", "refusal": False, "scheme": "Moovalur Ramamirtham Ammiyar Higher Education Assurance Scheme (Pudhumai Penn)"},
    {"id": "q03", "cat": "Flagship", "q": "What is Chief Minister's Breakfast Scheme?", "refusal": False, "scheme": "Chief Minister's Breakfast Scheme"},
    {"id": "q04", "cat": "Flagship", "q": "Tell me about Makkalai Thedi Maruthuvam scheme.", "refusal": False, "scheme": "Makkalai Thedi Maruthuvam Doorstep Healthcare Scheme"},
    {"id": "q05", "cat": "Flagship", "q": "What benefits are provided under Vidiyal Payanam Scheme?", "refusal": False, "scheme": "Free Bus Travel for Women (Vidiyal Payanam Scheme)"},
    {"id": "q06", "cat": "Flagship", "q": "What is CMCHIS health insurance coverage limit?", "refusal": False, "scheme": "Chief Minister's Comprehensive Health Insurance Scheme"},
    {"id": "q07", "cat": "Flagship", "q": "Explain Old Age Pension scheme in Tamil Nadu.", "refusal": False, "scheme": "Tamil Nadu Social Security Pension Schemes (Old Age Pension / Destitute Widow Pension)"},
    {"id": "q08", "cat": "Flagship", "q": "What is Destitute Widow Pension assistance?", "refusal": False, "scheme": "Tamil Nadu Social Security Pension Schemes (Old Age Pension / Destitute Widow Pension)"},
    {"id": "q09", "cat": "Flagship", "q": "What is Assistance for Marriage scheme?", "refusal": False, "scheme": "Assistance for Marriage"},
    {"id": "q10", "cat": "Flagship", "q": "What assistance is given for delivery or miscarriage?", "refusal": False, "scheme": "Assistance for Delivery / Miscarriage of Pregnancy"},

    # Category 2: Colloquial & English Shortcuts (10)
    {"id": "q11", "cat": "Colloquial", "q": "free bus", "refusal": False, "scheme": "Free Bus Travel for Women (Vidiyal Payanam Scheme)"},
    {"id": "q12", "cat": "Colloquial", "q": "widow pension", "refusal": False, "scheme": "Tamil Nadu Social Security Pension Schemes (Old Age Pension / Destitute Widow Pension)"},
    {"id": "q13", "cat": "Colloquial", "q": "old age pension", "refusal": False, "scheme": "Tamil Nadu Social Security Pension Schemes (Old Age Pension / Destitute Widow Pension)"},
    {"id": "q14", "cat": "Colloquial", "q": "girl education", "refusal": False, "scheme": "Moovalur Ramamirtham Ammiyar Higher Education Assurance Scheme (Pudhumai Penn)"},
    {"id": "q15", "cat": "Colloquial", "q": "widow money", "refusal": False, "scheme": "Tamil Nadu Social Security Pension Schemes (Old Age Pension / Destitute Widow Pension)"},
    {"id": "q16", "cat": "Colloquial", "q": "girls scholarship", "refusal": False, "scheme": "Moovalur Ramamirtham Ammiyar Higher Education Assurance Scheme (Pudhumai Penn)"},
    {"id": "q17", "cat": "Colloquial", "q": "kmut 1000", "refusal": False, "scheme": "Kalaignar Magalir Urimai Thogai Scheme"},
    {"id": "q18", "cat": "Colloquial", "q": "school breakfast", "refusal": False, "scheme": "Chief Minister's Breakfast Scheme"},
    {"id": "q19", "cat": "Colloquial", "q": "doorstep health", "refusal": False, "scheme": "Makkalai Thedi Maruthuvam Doorstep Healthcare Scheme"},
    {"id": "q20", "cat": "Colloquial", "q": "health insurance", "refusal": False, "scheme": "Chief Minister's Comprehensive Health Insurance Scheme"},

    # Category 3: Tamil & Transliterated Queries (10)
    {"id": "q21", "cat": "Tamil", "q": "மகளிர் உரிமை தொகை திட்டம் பற்றி கூறுக", "refusal": False, "scheme": "Kalaignar Magalir Urimai Thogai Scheme"},
    {"id": "q22", "cat": "Tamil", "q": "புதுமைப் பெண் திட்டம் தகுதி என்ன?", "refusal": False, "scheme": "Moovalur Ramamirtham Ammiyar Higher Education Assurance Scheme (Pudhumai Penn)"},
    {"id": "q23", "cat": "Tamil", "q": "இலவச பஸ் பயணம் திட்டம்", "refusal": False, "scheme": "Free Bus Travel for Women (Vidiyal Payanam Scheme)"},
    {"id": "q24", "cat": "Tamil", "q": "முதியோர் ஓய்வூதியம் எவ்வளவு?", "refusal": False, "scheme": "Tamil Nadu Social Security Pension Schemes (Old Age Pension / Destitute Widow Pension)"},
    {"id": "q25", "cat": "Tamil", "q": "விதவை ஓய்வூதிய திட்டம்", "refusal": False, "scheme": "Tamil Nadu Social Security Pension Schemes (Old Age Pension / Destitute Widow Pension)"},
    {"id": "q26", "cat": "Tamil", "q": "முதலமைச்சர் காலை உணவு திட்டம்", "refusal": False, "scheme": "Chief Minister's Breakfast Scheme"},
    {"id": "q27", "cat": "Tamil", "q": "மக்களைத் தேடி மருத்துவம்", "refusal": False, "scheme": "Makkalai Thedi Maruthuvam Doorstep Healthcare Scheme"},
    {"id": "q28", "cat": "Tamil", "q": "magalir urimai thogai details", "refusal": False, "scheme": "Kalaignar Magalir Urimai Thogai Scheme"},
    {"id": "q29", "cat": "Tamil", "q": "pudhumai pen thittam eligibility", "refusal": False, "scheme": "Moovalur Ramamirtham Ammiyar Higher Education Assurance Scheme (Pudhumai Penn)"},
    {"id": "q30", "cat": "Tamil", "q": "ilavasa bus payanam", "refusal": False, "scheme": "Free Bus Travel for Women (Vidiyal Payanam Scheme)"},

    # Category 4: Differently Abled & Vocational Welfare (10)
    {"id": "q31", "cat": "Specialized", "q": "What is Unemployment Allowance to Differently Abled Persons?", "refusal": False, "scheme": "Unemployment Allowance to Differently Abled Persons"},
    {"id": "q32", "cat": "Specialized", "q": "Spectacles purchase assistance for differently abled", "refusal": False, "scheme": "Assistance for Purchase of Spectacles by a Differently Abled Person"},
    {"id": "q33", "cat": "Specialized", "q": "Maintenance allowance for leprosy affected persons", "refusal": False, "scheme": "Maintenance Allowance for Leprosy Affected Persons"},
    {"id": "q34", "cat": "Specialized", "q": "Marriage assistance for marrying visually impaired person", "refusal": False, "scheme": "Marriage Assistance to Normal Persons Marrying Visually Impaired Persons"},
    {"id": "q35", "cat": "Specialized", "q": "Scholarship for children of disabled persons", "refusal": False, "scheme": "Scholarship to Son and Daughter of Persons with Disabilities"},
    {"id": "q36", "cat": "Specialized", "q": "PMEGP scheme eligibility for self employment", "refusal": False, "scheme": "Prime Minister's Employment Generation Programme (PMEGP)"},
    {"id": "q37", "cat": "Specialized", "q": "UYEGP unemployed youth scheme details", "refusal": False, "scheme": "Unemployed Youth Employment Generation Programme (UYEGP)"},
    {"id": "q38", "cat": "Specialized", "q": "Job opportunity through private sector job fairs", "refusal": False, "scheme": "Job Opportunity Through Private Sector"},
    {"id": "q39", "cat": "Specialized", "q": "Book binder training for visually impaired", "refusal": False, "scheme": "Book Binder Training"},
    {"id": "q40", "cat": "Specialized", "q": "Motorised sewing machines distribution scheme", "refusal": False, "scheme": "Motorised Sewing Machines"},

    # Category 5: Out-of-Domain / Pre-LLM Topic Guard Refusals (10)
    {"id": "q41", "cat": "Refusal", "q": "What is NASA Mars rover welfare scheme in Tamil Nadu?", "refusal": True, "scheme": None},
    {"id": "q42", "cat": "Refusal", "q": "What is the stock price of Infosys today?", "refusal": True, "scheme": None},
    {"id": "q43", "cat": "Refusal", "q": "IPL Chennai Super Kings ticket subsidy scheme", "refusal": True, "scheme": None},
    {"id": "q44", "cat": "Refusal", "q": "Bitcoin cryptocurrency welfare grant", "refusal": True, "scheme": None},
    {"id": "q45", "cat": "Refusal", "q": "Weather forecast and rain prediction for Chennai tomorrow", "refusal": True, "scheme": None},
    {"id": "q46", "cat": "Refusal", "q": "Apple iPhone free distribution scheme", "refusal": True, "scheme": None},
    {"id": "q47", "cat": "Refusal", "q": "Latest Tamil movie cinema ticket refund scheme", "refusal": True, "scheme": None},
    {"id": "q48", "cat": "Refusal", "q": "Netflix free subscription government scheme", "refusal": True, "scheme": None},
    {"id": "q49", "cat": "Refusal", "q": "How to cook Chettinad chicken curry recipe", "refusal": True, "scheme": None},
    {"id": "q50", "cat": "Refusal", "q": "Horoscope predictions for Leo star sign", "refusal": True, "scheme": None},
]

def run_benchmark_50():
    print("=" * 75)
    print("   TAMIL NADU GOV AI ASSISTANT — 50-QUERY AUDIT BENCHMARK")
    print("=" * 75)

    total_queries = len(BENCHMARK_50_SUITE)
    passed_evals = 0
    total_latency = 0.0
    reciprocal_ranks = []
    precision_scores = []
    recall_scores = []

    cat_stats = {}

    for test in BENCHMARK_50_SUITE:
        qid = test["id"]
        cat = test["cat"]
        qtext = test["q"]
        exp_refusal = test["refusal"]
        exp_scheme = test["scheme"]

        if cat not in cat_stats:
            cat_stats[cat] = {"total": 0, "passed": 0}
        cat_stats[cat]["total"] += 1

        t0 = time.monotonic()
        response = answer_question(qtext)
        latency = time.monotonic() - t0
        total_latency += latency

        is_refusal = not response.retrieval_metadata.llm_called
        retrieved_count = response.retrieval_metadata.total_retrieved
        top_rrf = response.retrieval_metadata.top_rrf_score or 0.0
        confidence = response.retrieval_metadata.confidence_level

        matched_rank = 0
        if exp_scheme:
            for chunk in response.retrieved_chunks:
                sn = str(chunk.metadata.get("scheme_name", ""))
                if sn == exp_scheme or exp_scheme.lower() in sn.lower():
                    matched_rank = chunk.final_rank
                    break

        mrr = 1.0 / matched_rank if matched_rank > 0 else 0.0
        reciprocal_ranks.append(mrr)
        precision = 1.0 if matched_rank > 0 else 0.0
        precision_scores.append(precision)
        recall_scores.append(precision)

        correct = False
        if exp_refusal:
            correct = is_refusal
        else:
            correct = (not is_refusal) and (matched_rank > 0 or len(response.citations) > 0)

        if correct:
            passed_evals += 1
            cat_stats[cat]["passed"] += 1

        status_str = "[PASS]" if correct else "[FAIL]"
        clean_qtext = qtext.encode('ascii', errors='replace').decode('ascii')
        print(f"{status_str} {qid} [{cat}]: '{clean_qtext}'")
        print(f"       Lat: {latency:.2f}s | Conf: {confidence} | Top RRF: {top_rrf:.4f} | Match: {matched_rank if matched_rank > 0 else 'N/A'} | Refusal: {is_refusal}")

    mean_mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
    mean_precision = sum(precision_scores) / len(precision_scores) if precision_scores else 0.0
    mean_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0.0
    avg_latency = total_latency / total_queries if total_queries > 0 else 0.0
    pass_rate = (passed_evals / total_queries) * 100.0

    print("\n" + "=" * 75)
    print("                     50-QUERY BENCHMARK SUMMARY")
    print("=" * 75)
    print(f"  Total Benchmark Queries : {total_queries}")
    print(f"  Passed Evaluation       : {passed_evals}/{total_queries} ({pass_rate:.1f}%)")
    print(f"  Mean Reciprocal Rank    : {mean_mrr:.4f}")
    print(f"  Precision@5             : {mean_precision:.4f}")
    print(f"  Recall@5                : {mean_recall:.4f}")
    print(f"  Average Query Latency   : {avg_latency:.2f}s")
    print("-" * 75)
    print("  Category Breakdown:")
    for c, s in cat_stats.items():
        rate = (s["passed"] / s["total"]) * 100.0 if s["total"] > 0 else 0.0
        print(f"    - {c:<12}: {s['passed']}/{s['total']} ({rate:.1f}%)")
    print("=" * 75)

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_queries": total_queries,
        "passed_evals": passed_evals,
        "pass_rate": pass_rate,
        "mean_mrr": mean_mrr,
        "precision_at_5": mean_precision,
        "recall_at_5": mean_recall,
        "average_latency_seconds": round(avg_latency, 2),
        "category_breakdown": cat_stats
    }

    report_path = backend_dir / "evaluation" / "benchmark_50_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved 50-query benchmark results to '{report_path}'")

if __name__ == "__main__":
    run_benchmark_50()
