"""Query expansion and fuzzy matching utility for colloquial terms and typos.

Maps citizen queries ("free bus", "widow pension", "மகளிர் உரிமை") to official
scheme names and provides "Did you mean?" suggestions for fuzzy matches.
"""

from __future__ import annotations

import re
import difflib
from typing import Sequence

# ── Colloquial Query & Synonym Dictionary ────────────────────
SYNONYM_MAP: dict[str, str] = {
    # English Colloquial -> Official Term Expansion
    "free bus": "Free Bus Travel for Women Vidiyal Payanam Scheme ordinary town buses",
    "women free bus": "Free Bus Travel for Women Vidiyal Payanam Scheme",
    "widow pension": "Destitute Widow Pension DWP Social Security Pension Schemes",
    "old age pension": "Indira Gandhi National Old Age Pension IGNOAPS OAP Social Security",
    "oap": "Indira Gandhi National Old Age Pension IGNOAPS OAP Social Security",
    "girl education": "Moovalur Ramamirtham Ammiyar Higher Education Assurance Scheme Pudhumai Penn",
    "pudhumai penn": "Moovalur Ramamirtham Ammiyar Higher Education Assurance Scheme Pudhumai Penn",
    "pudhumai pen": "Moovalur Ramamirtham Ammiyar Higher Education Assurance Scheme Pudhumai Penn",
    "higher education girl": "Pudhumai Penn Scheme Higher Education Assurance",
    "magalir urimai": "Kalaignar Magalir Urimai Thogai Scheme KMUT 1000 rupees",
    "kmut": "Kalaignar Magalir Urimai Thogai Scheme KMUT",
    "breakfast scheme": "Chief Minister's Breakfast Scheme school children",
    "school breakfast": "Chief Minister's Breakfast Scheme primary school",
    "doorstep health": "Makkalai Thedi Maruthuvam Doorstep Healthcare Scheme",
    "health insurance": "Chief Minister's Comprehensive Health Insurance Scheme CMCHIS",
    "cmchis": "Chief Minister's Comprehensive Health Insurance Scheme CMCHIS",
    "marriage assistance": "Assistance for Marriage Marriage Assistance Schemes",
    "marriage money": "Assistance for Marriage Marriage Assistance Schemes",
    "pregnant assistance": "Assistance for Delivery Miscarriage of Pregnancy",
    "delivery assistance": "Assistance for Delivery Miscarriage of Pregnancy",
    "unemployment allowance": "Unemployment Allowance to Differently Abled Persons UYEGP",
    
    # Tamil Colloquial -> Official Term Expansion
    "மகளிர் உரிமை": "Kalaignar Magalir Urimai Thogai Scheme KMUT",
    "பெண்கள் இலவச பஸ்": "Free Bus Travel for Women Vidiyal Payanam Scheme",
    "இலவச பஸ்": "Free Bus Travel for Women Vidiyal Payanam Scheme",
    "புதுமைப் பெண்": "Pudhumai Penn Scheme Higher Education Assurance",
    "முதியோர் ஓய்வூதியம்": "Indira Gandhi National Old Age Pension IGNOAPS OAP",
    "விதவை ஓய்வூதியம்": "Destitute Widow Pension DWP",
    "முதலமைச்சர் காலை உணவு": "Chief Minister's Breakfast Scheme",
    "மக்களைத் தேடி மருத்துவம்": "Makkalai Thedi Maruthuvam Doorstep Healthcare Scheme",
    "விவசாயி உதவி": "Social Security Schemes Under Tamil Nadu Welfare Board",
}

# ── List of All Ingested Scheme Names for Suggestions ─────────
KNOWN_SCHEMES: list[str] = [
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
    "Establishing Aavin Parlour for Differently Abled Persons",
    "Ensuring Employment Opportunities",
    "Financial Assistance to Differently Abled Persons to Appear Main Examination (UPSC / TNPSC)",
    "Fitter Training to Hearing Impaired Persons",
    "Multimedia Training",
    "Skill Training",
]


def expand_query(query: str) -> str:
    """Expand user query if it contains known colloquial terms or Tamil shortcuts.

    Args:
        query: Raw input query.

    Returns:
        Expanded query string incorporating official keywords.
    """
    clean_query = query.strip().lower()

    # Direct match or substring lookup
    expansions: list[str] = []
    for key, value in SYNONYM_MAP.items():
        if key.lower() in clean_query:
            expansions.append(value)

    if expansions:
        # Append expansions to original query for hybrid retrieval context
        expanded = f"{query} {' '.join(expansions)}"
        return expanded.strip()

    return query


def suggest_did_you_mean(query: str, cutoff: float = 0.4, limit: int = 3) -> list[str]:
    """Find fuzzy matching scheme suggestions for typos or partial names.

    Args:
        query: User input text.
        cutoff: Minimum similarity threshold (0.0 to 1.0).
        limit: Max number of suggestions.

    Returns:
        List of matching official scheme names.
    """
    clean_query = query.strip().lower()

    # Get close matches using SequenceMatcher / difflib
    matches = difflib.get_close_matches(
        clean_query,
        [s.lower() for s in KNOWN_SCHEMES],
        n=limit,
        cutoff=cutoff,
    )

    # Map back to original case
    suggestions: list[str] = []
    for match in matches:
        for original in KNOWN_SCHEMES:
            if original.lower() == match and original not in suggestions:
                suggestions.append(original)

    return suggestions
