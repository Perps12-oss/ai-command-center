"""Tracing helpers for provider SDK."""

from __future__ import annotations

from typing import Any


def trace_context_from_payload(payload: dict[str, Any]) -> tuple[str, str]:
    return (
        str(payload.get("trace_id", "")),
        str(payload.get("span_id", "")),
    )
