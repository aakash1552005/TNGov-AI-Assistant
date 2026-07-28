"""Text cleaning pipeline for extracted PDF content.

Provides a configurable sequence of cleaning steps that normalize
whitespace, fix encoding, remove repeated headers/footers, and
preserve meaningful document structure. Each step is a standalone
function for testability.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter


# ── Individual Cleaning Steps ─────────────────────────────────


def normalize_unicode(text: str) -> str:
    """Apply NFKC Unicode normalization.

    Critical for Tamil text where visually identical characters
    may use different Unicode representations.
    """
    return unicodedata.normalize("NFKC", text)


def strip_control_characters(text: str) -> str:
    """Remove control characters except newlines and tabs."""
    return "".join(
        ch for ch in text if ch in ("\n", "\t") or not unicodedata.category(ch).startswith("C")
    )


def collapse_whitespace(text: str) -> str:
    """Collapse runs of spaces/tabs into single spaces (preserve newlines)."""
    # Collapse horizontal whitespace (spaces and tabs) but keep newlines
    text = re.sub(r"[^\S\n]+", " ", text)
    # Collapse 3+ consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_page_numbers(text: str) -> str:
    """Remove standalone page number lines (e.g., '- 3 -', 'Page 5', '12')."""
    # Matches lines that are only a page number pattern
    patterns = [
        r"^\s*-?\s*\d{1,4}\s*-?\s*$",       # "- 3 -" or "3"
        r"^\s*page\s+\d{1,4}\s*$",            # "Page 5"
        r"^\s*\d{1,4}\s*/\s*\d{1,4}\s*$",     # "3/10"
    ]
    combined = "|".join(f"(?:{p})" for p in patterns)
    return re.sub(combined, "", text, flags=re.MULTILINE | re.IGNORECASE)


# ── Repeated Header/Footer Detection ─────────────────────────


def detect_repeated_lines(
    page_texts: list[str],
    *,
    min_occurrences_ratio: float = 0.5,
    max_line_length: int = 200,
    n_lines_to_check: int = 3,
) -> set[str]:
    """Detect lines that repeat across pages as likely headers/footers.

    Examines the first and last ``n_lines_to_check`` lines of each page.
    Lines that appear in more than ``min_occurrences_ratio`` of pages
    (and are short enough to be headers/footers) are flagged for removal.

    Args:
        page_texts: List of raw text strings, one per page.
        min_occurrences_ratio: Fraction of pages a line must appear in
            to be considered a repeated header/footer (default 0.5 = 50%).
        max_line_length: Lines longer than this are assumed to be content,
            not headers/footers.
        n_lines_to_check: Number of lines to examine from the top and
            bottom of each page.

    Returns:
        Set of normalized line strings identified as repeated headers/footers.
    """
    if len(page_texts) < 3:
        # Too few pages to reliably detect repetition
        return set()

    min_occurrences = max(2, int(len(page_texts) * min_occurrences_ratio))
    candidate_counter: Counter[str] = Counter()

    for page_text in page_texts:
        lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
        if not lines:
            continue

        # Check top and bottom lines of each page
        top_lines = lines[:n_lines_to_check]
        bottom_lines = lines[-n_lines_to_check:]
        edge_lines = set(top_lines + bottom_lines)

        for line in edge_lines:
            if len(line) <= max_line_length:
                # Normalize for comparison: lowercase, collapse spaces
                normalized = re.sub(r"\s+", " ", line.lower()).strip()
                # Skip very short lines (likely just numbers)
                if len(normalized) > 3:
                    candidate_counter[normalized] += 1

    repeated = {
        line for line, count in candidate_counter.items() if count >= min_occurrences
    }

    return repeated


def remove_repeated_headers_footers(
    text: str,
    repeated_lines: set[str],
) -> str:
    """Remove lines identified as repeated headers/footers.

    Args:
        text: Page text to clean.
        repeated_lines: Set of normalized line strings to remove.

    Returns:
        Cleaned text with repeated header/footer lines removed.
    """
    if not repeated_lines:
        return text

    cleaned_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            normalized = re.sub(r"\s+", " ", stripped.lower()).strip()
            if normalized in repeated_lines:
                continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


# ── Composed Pipeline ─────────────────────────────────────────


def clean_page(text: str, repeated_lines: set[str] | None = None) -> str:
    """Apply the full cleaning pipeline to a single page of text.

    Args:
        text: Raw text extracted from a PDF page.
        repeated_lines: Optional set of detected repeated header/footer
            lines to remove. Pass the output of ``detect_repeated_lines``.

    Returns:
        Cleaned text ready for chunking.
    """
    text = normalize_unicode(text)
    text = strip_control_characters(text)
    if repeated_lines:
        text = remove_repeated_headers_footers(text, repeated_lines)
    text = remove_page_numbers(text)
    text = collapse_whitespace(text)
    return text


def clean_pages(page_texts: list[str]) -> list[str]:
    """Clean a list of page texts with cross-page header/footer detection.

    This is the primary entry point for cleaning. It first detects
    repeated headers/footers across all pages, then cleans each page
    with that context.

    Args:
        page_texts: List of raw text strings, one per page.

    Returns:
        List of cleaned text strings, same length as input.
    """
    repeated_lines = detect_repeated_lines(page_texts)
    return [clean_page(text, repeated_lines) for text in page_texts]
