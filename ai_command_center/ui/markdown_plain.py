"""Plain-text markdown display helpers for ChatView."""

from __future__ import annotations

import re

_FENCE = re.compile(r"```(\w*)\r?\n(.*?)```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"\*(.+?)\*")
_HEADER = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
_BULLET = re.compile(r"^[\*\-]\s+(.+)$", re.MULTILINE)
_NUMBERED = re.compile(r"^\d+\.\s+(.+)$", re.MULTILINE)
_HR = re.compile(r"^[-*_]{3,}\s*$", re.MULTILINE)


def format_assistant_markdown(text: str) -> str:
    """Render markdown as readable plain-text blocks for CTkTextbox."""
    result = text

    def _fence_block(match: re.Match[str]) -> str:
        lang = match.group(1).strip()
        code = match.group(2).rstrip()
        label = lang if lang else "code"
        lines = "\n".join(f"  {line}" for line in code.split("\n"))
        return f"\n┌─ {label} ─────────────────────\n{lines}\n└──────────────────────────────\n"

    result = _FENCE.sub(_fence_block, result)
    result = _HEADER.sub(lambda m: "\n" + "─" * (4 - len(m.group(1))) * 4 + " " + m.group(2).upper() + "\n", result)
    result = _HR.sub("─" * 48, result)
    result = _BULLET.sub(lambda m: "  • " + m.group(1), result)
    result = _NUMBERED.sub(lambda m: "  " + m.group(0), result)
    result = _BOLD.sub(lambda m: m.group(1).upper(), result)
    result = _ITALIC.sub(lambda m: "_" + m.group(1) + "_", result)
    result = _INLINE_CODE.sub(lambda m: "«" + m.group(1) + "»", result)

    return result


def extract_segments(text: str) -> list[tuple[str, str]]:
    """
    Split formatted text into (kind, content) segments.
    kind: 'text' | 'code'
    Used by ChatView to apply different tag styles to code blocks.
    """
    segments: list[tuple[str, str]] = []
    last = 0
    for match in _FENCE.finditer(text):
        if match.start() > last:
            segments.append(("text", text[last : match.start()]))
        lang = match.group(1).strip() or "code"
        code = match.group(2).rstrip()
        lines = "\n".join(f"  {line}" for line in code.split("\n"))
        block = f"\n┌─ {lang} ─────────────────────\n{lines}\n└──────────────────────────────\n"
        segments.append(("code", block))
        last = match.end()
    if last < len(text):
        segments.append(("text", text[last:]))
    return segments
