"""Plain-text markdown display helpers for ChatView."""

from __future__ import annotations

import re

_FENCE = re.compile(r"```(\w*)\r?\n(.*?)```", re.DOTALL)


def format_assistant_markdown(text: str) -> str:
    """Render code fences as readable plain-text blocks (no HTML widget)."""

    def _block(match: re.Match[str]) -> str:
        lang = match.group(1).strip()
        code = match.group(2).rstrip()
        label = lang if lang else "code"
        return f"\n── {label} ──\n{code}\n── end ──\n"

    return _FENCE.sub(_block, text)
