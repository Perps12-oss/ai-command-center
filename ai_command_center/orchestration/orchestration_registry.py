"""Tracks chat request IDs handled by truth-bound orchestration."""

from __future__ import annotations

from threading import Lock

_lock = Lock()
_orchestration_request_ids: set[str] = set()


def mark_orchestration_request(request_id: str) -> None:
    with _lock:
        _orchestration_request_ids.add(request_id)


def is_orchestration_handled(request_id: str) -> bool:
    with _lock:
        return request_id in _orchestration_request_ids


def clear_orchestration_request(request_id: str) -> None:
    with _lock:
        _orchestration_request_ids.discard(request_id)
