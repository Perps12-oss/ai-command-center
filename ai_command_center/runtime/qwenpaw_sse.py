"""QwenPaw console chat SSE event parser (Agent Runtime Interface Phase 2)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


class QwenPawStreamStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class QwenPawStreamEvent:
    status: QwenPawStreamStatus | None
    assistant_text: str
    delta: str
    error_message: str
    session_id: str


def _assistant_text_from_output(output: Any) -> str:
    if not isinstance(output, list):
        return ""
    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        if str(item.get("role", "")).strip() != "assistant":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if str(block.get("type", "")).strip() != "text":
                continue
            text = str(block.get("text", ""))
            if text:
                parts.append(text)
    return "".join(parts)


def parse_sse_data_line(line: str, *, previous_text: str = "") -> QwenPawStreamEvent | None:
    """Parse one ``data: {...}`` line from ``POST /api/console/chat``."""
    stripped = line.strip()
    if not stripped:
        return None
    if stripped.startswith("data:"):
        stripped = stripped[5:].strip()
    if not stripped or stripped == "[DONE]":
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None

    status_raw = str(payload.get("status", "")).strip().lower()
    status: QwenPawStreamStatus | None = None
    try:
        status = QwenPawStreamStatus(status_raw) if status_raw else None
    except ValueError:
        status = None

    assistant_text = _assistant_text_from_output(payload.get("output"))
    delta = ""
    if assistant_text:
        if assistant_text.startswith(previous_text):
            delta = assistant_text[len(previous_text) :]
        else:
            delta = assistant_text

    error_message = ""
    error = payload.get("error")
    if isinstance(error, dict):
        error_message = str(error.get("message") or error.get("detail") or "").strip()
    elif error:
        error_message = str(error).strip()

    session_id = str(payload.get("session_id", "")).strip()
    return QwenPawStreamEvent(
        status=status,
        assistant_text=assistant_text,
        delta=delta,
        error_message=error_message,
        session_id=session_id,
    )
