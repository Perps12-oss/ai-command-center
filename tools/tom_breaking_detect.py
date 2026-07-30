"""Detect intentional breaking-change markers in PR text.

Tom's Implementation Audit uses this to avoid false positives from ordinary
words like \"destroy\" (window lifecycle) or \"delete\" (remove a preference).
"""

from __future__ import annotations

import re

# Explicit conventional / ops markers only — not substrings of normal prose.
_BREAKING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bBREAKING(?:\s+CHANGE)?\b", re.IGNORECASE),
    re.compile(r"\bBREAKING:", re.IGNORECASE),
    re.compile(r"\bMAJOR\s+VERSION\b", re.IGNORECASE),
    re.compile(r"\bAPI\s+BREAK(?:ING)?\b", re.IGNORECASE),
    # Intentional ops flags only (colon / bang form), not verbs like destroy/delete.
    re.compile(r"\bDESTROY:", re.IGNORECASE),
    re.compile(r"\bDELETE:", re.IGNORECASE),
)


def has_breaking_change_marker(text: str) -> bool:
    """Return True when PR title/body contains an intentional breaking marker."""
    body = text or ""
    return any(pat.search(body) for pat in _BREAKING_PATTERNS)


__all__ = ["has_breaking_change_marker"]
