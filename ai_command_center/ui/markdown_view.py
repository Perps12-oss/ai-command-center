"""Markdown-to-textbox segment parser for ChatView.

Splits assistant markdown into (text, tag_kind) segments that can be inserted
into a CustomTkinter CTkTextbox with named tags. Does not support nested
inline styles; it covers the most common formatting seen in LLM output.
"""

from __future__ import annotations

import re
from typing import Iterable


def _split_inline(text: str) -> Iterable[tuple[str, str | None]]:
    """Yield segments for bold, italic, code, and plain text."""
    # Inline code first so it wins over * markers inside backticks.
    parts = re.split(r"(`[^`]+`)", text)
    for part in parts:
        if part.startswith("`") and part.endswith("`"):
            yield part[1:-1], "code"
            continue
        for sub in re.split(r"(\*\*[^*]+\*\*|__[^_]+__)", part):
            if sub.startswith("**") and sub.endswith("**"):
                yield sub[2:-2], "bold"
            elif sub.startswith("__") and sub.endswith("__"):
                yield sub[2:-2], "bold"
            else:
                for s in re.split(r"(\*[^*]+\*|_[^_]+_)", sub):
                    if s.startswith("*") and s.endswith("*"):
                        yield s[1:-1], "italic"
                    elif s.startswith("_") and s.endswith("_"):
                        yield s[1:-1], "italic"
                    else:
                        yield s, None


def parse_markdown(text: str) -> list[tuple[str, str | None]]:
    """Parse markdown into (segment, tag_kind) tuples.

    Supported:
      - fenced code blocks (```...```) -> tag 'code_block'
      - indented code blocks (4 spaces) -> tag 'code_block'
      - headers (#, ##, ###) -> tag 'header'
      - bullet/numbered lists -> tag 'list'
      - inline bold, italic, code -> tags 'bold', 'italic', 'code'
      - plain text -> tag None
    """
    out: list[tuple[str, str | None]] = []
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()

        # Fenced code block
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].lstrip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            header = f"── {lang if lang else 'code'} ──\n" if lang else ""
            out.append((header + "".join(code_lines) + "── end ──\n", "code_block"))
            continue

        # Header
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            level = min(level, 3)
            content = stripped.lstrip("#").strip()
            out.append((content + "\n", "header"))
            i += 1
            continue

        # Indented code block
        if line.startswith("    ") or line.startswith("\t"):
            code_lines = [line]
            i += 1
            while i < len(lines) and (lines[i].startswith("    ") or lines[i].startswith("\t") or lines[i] == "\n"):
                code_lines.append(lines[i])
                i += 1
            out.append(("── code ──\n" + "".join(code_lines) + "── end ──\n", "code_block"))
            continue

        # List item
        if re.match(r"^(\s*)([-*+]|\d+\.)\s+", line):
            marker = re.match(r"^(\s*)([-*+]|\d+\.)\s+", line).group(2)
            content = re.sub(r"^(\s*)([-*+]|\d+\.)\s+", "", line)
            prefix = "• " if marker in "-*+" else f"{marker} "
            out.append((prefix, "list"))
            for seg, tag in _split_inline(content):
                out.append((seg, tag or "list"))
            i += 1
            continue

        # Plain line with possible inline styles
        if line.strip() == "":
            out.append(("\n", None))
            i += 1
            continue

        for seg, tag in _split_inline(line):
            out.append((seg, tag))
        i += 1

    return out
