"""Receipt validation helpers for provider certification."""

from __future__ import annotations

from typing import Any


def receipt_is_complete(payload: dict[str, Any]) -> bool:
    required = ("receipt_id", "request_id", "intent", "provider_id", "success")
    return all(key in payload and payload[key] is not None for key in required)
