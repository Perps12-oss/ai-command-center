"""Detect when a command explicitly asks to use the system clipboard."""

from __future__ import annotations

import re

_CLIPBOARD_WORD = re.compile(
    r"\b(?:clipboard|pasteboard|clipboad|clip\s*boad|clip\s*board)\b",
    re.IGNORECASE,
)
_CLIP_COMMAND = re.compile(
    r"\b(?:summarize|summary|explain|translate|rewrite|shorten|expand)\b",
    re.IGNORECASE,
)
_THIS_CLIP = re.compile(r"\b(?:this|the|my)\s+clip\b", re.IGNORECASE)


def wants_clipboard(text: str) -> bool:
    """True when the user clearly expects clipboard content in the reply."""
    stripped = text.strip()
    if not stripped:
        return False
    if _CLIPBOARD_WORD.search(stripped):
        return True
    if _CLIP_COMMAND.search(stripped) and _THIS_CLIP.search(stripped):
        return True
    return False


def empty_clipboard_message() -> str:
    return (
        "Clipboard is empty. Copy text first, then try: Summarize this clipboard"
    )
