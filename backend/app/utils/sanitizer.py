"""Lightweight query sanitizer for prompt injection protection.

Detects and strips common prompt injection override phrases without blocking
normal citizen questions about welfare schemes.
"""

from __future__ import annotations

import re

# Phrases commonly used in prompt injection attempts
_INJECTION_PATTERNS = [
    r"(?i)\bignore\s+previous\s+instructions\b",
    r"(?i)\bforget\s+(your\s+)?system\s+prompt\b",
    r"(?i)\bact\s+as\s+(a\s+)?chatgpt\b",
    r"(?i)\breveal\s+(your\s+)?prompt\b",
    r"(?i)\byou\s+are\s+now\b",
    r"(?i)^\s*system\s*:\s*",
    r"(?i)^\s*assistant\s*:\s*",
    r"(?i)^\s*developer\s*:\s*",
]

_COMPILED_PATTERNS = [re.compile(p) for p in _INJECTION_PATTERNS]


def sanitize_query(query: str) -> str:
    """Sanitize user query by stripping prompt injection override phrases.

    Preserves valid government scheme questions while eliminating attempts
    to override the system prompt.

    Args:
        query: The raw user input string.

    Returns:
        Sanitized query string.
    """
    if not query:
        return ""

    sanitized = query
    for pattern in _COMPILED_PATTERNS:
        sanitized = pattern.sub("", sanitized)

    # Collapse any double spaces created by stripping
    return re.sub(r"\s+", " ", sanitized).strip()
