"""Tracks chat request IDs delegated to external capability providers."""

from __future__ import annotations

from threading import Lock

_lock = Lock()
_external_request_ids: set[str] = set()


def mark_external_request(request_id: str) -> None:
    with _lock:
        _external_request_ids.add(request_id)


def is_externally_handled(request_id: str) -> bool:
    with _lock:
        return request_id in _external_request_ids


def clear_external_request(request_id: str) -> None:
    with _lock:
        _external_request_ids.discard(request_id)
