"""Detect intentional breaking-change markers in PR text.

Tom's Implementation Audit uses this to avoid false positives from ordinary
words like \"destroy\" (window lifecycle) or \"delete\" (remove a preference).

Markers listed inside markdown inline/fenced code (e.g. documenting the
detector) are ignored — only plain-text markers count.
"""

from __future__ import annotations

import re

# Explicit conventional / ops markers only — not substrings of normal prose.
_BREAKING_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Require the conventional phrase or colon form — bare "BREAKING" is prose.
    re.compile(r"\bBREAKING\s+CHANGE\b", re.IGNORECASE),
    re.compile(r"\bBREAKING:", re.IGNORECASE),
    re.compile(r"\bMAJOR\s+VERSION\b", re.IGNORECASE),
    re.compile(r"\bAPI\s+BREAK(?:ING)?\b", re.IGNORECASE),
    # Intentional ops flags only (colon form), not verbs like destroy/delete.
    re.compile(r"\bDESTROY:", re.IGNORECASE),
    re.compile(r"\bDELETE:", re.IGNORECASE),
)

# Fenced blocks first, then inline `code` — so docs can list markers safely.
_MARKDOWN_CODE_RE = re.compile(
    r"```[\s\S]*?```|`[^`]+`",
    re.MULTILINE,
)


def _plain_text(text: str) -> str:
    """Return PR text with markdown code spans/blocks removed."""
    return _MARKDOWN_CODE_RE.sub(" ", text or "")


def has_breaking_change_marker(text: str) -> bool:
    """Return True when PR title/body plain text has an intentional breaking marker."""
    body = _plain_text(text)
    return any(pat.search(body) for pat in _BREAKING_PATTERNS)


__all__ = ["has_breaking_change_marker"]
