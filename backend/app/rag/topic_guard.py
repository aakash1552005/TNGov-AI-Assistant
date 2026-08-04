"""Pre-LLM topic guard — model-independent out-of-domain rejection.

This module is intentionally kept free of any LLM, ChromaDB, or network calls.
It is the FIRST gate in the pipeline: if a query is clearly not about Tamil Nadu
Government schemes it is rejected *before* the LLM is invoked, regardless of
which fallback model is currently active.

Trigger logic (either condition triggers rejection):
1. Hard-coded out-of-domain keyword match (NASA, stock, IPL, etc.)
2. Retrieval returned zero chunks whose scheme_name appears in KNOWN_SCHEMES
   *and* the top RRF score is below the strict domain-relevance threshold.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.rag.retrieval_models import RetrievedChunk

# ---------------------------------------------------------------------------
# Out-of-domain keyword blocklist
# These terms are universally unrelated to Indian/TN government welfare schemes.
# Matching is case-insensitive and word-boundary-aware.
# ---------------------------------------------------------------------------
_OOD_PATTERNS: list[str] = [
    # Space / technology
    r"\bnasa\b", r"\bmars\s+rover\b", r"\brocket\b", r"\bspacex\b",
    # Finance / market
    r"\bstock\s+price\b", r"\bshare\s+price\b", r"\bbitcoin\b",
    r"\bcryptocurrency\b", r"\bcrypto\b", r"\bnifty\b", r"\bsensex\b",
    r"\binfosys\s+stock\b", r"\breliance\s+stock\b",
    # Sports / entertainment
    r"\bipl\b", r"\bcricket\s+(team|player|match|score)\b",
    r"\bworld\s+cup\b(?!.*scheme)", r"\bchennai\s+super\s+kings\b",
    r"\bmovie\b", r"\bfilm\b", r"\bactor\b", r"\bactress\b",
    r"\bnetflix\b", r"\bamazon\s+prime\b", r"\bhotstar\b",
    # Weather
    r"\bweather\b", r"\brain\s+forecast\b", r"\bcyclone\s+track\b",
    # General / Consumer Tech
    r"\biphone\b", r"\bapple\s+iphone\b", r"\bipad\b", r"\bmacbook\b",
    r"\brecipe\b", r"\bcooking\b", r"\bfashion\b", r"\btravel\s+guide\b",
    r"\bhoroscope\b", r"\bzodiac\b",
]

_OOD_COMPILED: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE) for p in _OOD_PATTERNS
]

# ---------------------------------------------------------------------------
# Known scheme names (same list used in query_expander.KNOWN_SCHEMES).
# A retrieved chunk is considered "on-topic" if its scheme_name appears here.
# ---------------------------------------------------------------------------
KNOWN_SCHEME_NAMES: frozenset[str] = frozenset({
    "Kalaignar Magalir Urimai Thogai Scheme",
    "Moovalur Ramamirtham Ammiyar Higher Education Assurance Scheme (Pudhumai Penn)",
    "Chief Minister's Breakfast Scheme",
    "Tamil Nadu Social Security Pension Schemes (Old Age Pension / Destitute Widow Pension)",
    "Makkalai Thedi Maruthuvam Doorstep Healthcare Scheme",
    "Free Bus Travel for Women (Vidiyal Payanam Scheme)",
    "Chief Minister's Comprehensive Health Insurance Scheme",
    "Assistance for Marriage",
    "Assistance for Delivery / Miscarriage of Pregnancy",
    "Assistance for Purchase of Spectacles by a Differently Abled Person",
    "Financial Assistance on the Natural Death of a Differently Abled Person",
    "Financial Assistance to Meet the Funeral Expenses of a Differently Abled Person",
    "Maintenance Allowance for Leprosy Affected Persons",
    "Maintenance Allowance for Persons Affected with Spinal Cord / Parkinson's",
    "Maintenance Allowance to Severely Affected Differently Abled Persons",
    "Marriage Assistance to Differently Abled Persons",
    "Marriage Assistance to Normal Persons Marrying Visually Impaired Persons",
    "Marriage Assistance to Normal Persons Marrying Speech and Hearing Impaired Persons",
    "Marriage Assistance to Normal Persons Marrying Locomotor Disabled Persons",
    "National Trust Act",
    "Scholarship to Son and Daughter of Persons with Disabilities",
    "Social Security Schemes Under Tamil Nadu Welfare Board",
    "Travel Concession to Differently Abled Persons in Government Buses",
    "Unemployment Allowance to Differently Abled Persons",
    "Prime Minister's Employment Generation Programme (PMEGP)",
    "Unemployed Youth Employment Generation Programme (UYEGP)",
    "Job Opportunity Through Private Sector",
    "Loan Assistance from National Handicapped Finance & Development Corporation (NHFDC)",
    "Micro Enterprises and Bunk Stalls",
    "Motorised Sewing Machines",
    "Book Binder Training",
})

# Strict RRF threshold for domain relevance when no known scheme appears
_DOMAIN_RRF_THRESHOLD: float = 0.015


def is_out_of_domain(query: str) -> bool:
    """Return True if the query matches a hard-coded out-of-domain keyword.

    This check is O(n*k) where n = number of patterns, k = query length.
    It runs in microseconds and has zero external dependencies.

    Args:
        query: Raw user query string.

    Returns:
        True if the query is clearly not about TN government schemes.
    """
    for pattern in _OOD_COMPILED:
        if pattern.search(query):
            return True
    return False


def retrieval_has_known_scheme(chunks: list[RetrievedChunk]) -> bool:
    """Return True if at least one retrieved chunk belongs to a known scheme.

    Used as a secondary check after retrieval to confirm topical relevance
    even when query keywords do not trigger the OOD blocklist.

    Args:
        chunks: Chunks returned by the hybrid retrieval pipeline.

    Returns:
        True if any chunk's scheme_name is in KNOWN_SCHEME_NAMES.
    """
    for chunk in chunks:
        scheme = str(chunk.metadata.get("scheme_name", "")).strip()
        if scheme and scheme in KNOWN_SCHEME_NAMES:
            return True
    return False


def should_refuse(
    query: str,
    chunks: list[RetrievedChunk],
    top_rrf_score: float | None,
    retrieval_min_score: float = _DOMAIN_RRF_THRESHOLD,
) -> bool:
    """Determine if the query should be refused BEFORE calling the LLM.

    Refusal is triggered if EITHER:
    1. Hard OOD keyword detected in the query (most reliable signal), OR
    2. No retrieved chunk maps to a known TN government scheme AND the top
       RRF score is below the minimum relevance threshold.

    This function is model-independent: it produces the same decision
    regardless of which LLM/fallback is currently active.

    Args:
        query: Sanitized user query.
        chunks: Chunks returned by hybrid retrieval.
        top_rrf_score: RRF score of the highest-ranked chunk (None if empty).
        retrieval_min_score: Minimum RRF score to consider retrieval relevant.

    Returns:
        True → refuse (do not call LLM).
        False → proceed to LLM generation.
    """
    # Gate 1: Hard keyword blocklist
    if is_out_of_domain(query):
        return True

    # Gate 2: No relevant retrieved chunk at all
    if not chunks or top_rrf_score is None or top_rrf_score < retrieval_min_score:
        return True

    # Gate 3: Retrieved chunks exist but none belong to a known scheme
    # (happens when retrieval is confused by very short/ambiguous queries)
    if not retrieval_has_known_scheme(chunks):
        # Only refuse if score is marginal; otherwise give LLM a chance
        if top_rrf_score < retrieval_min_score * 2:
            return True

    return False
