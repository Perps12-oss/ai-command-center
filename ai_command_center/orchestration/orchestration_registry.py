"""Tracks chat request IDs handled by truth-bound orchestration."""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock

_MAX_TRACKED_REQUESTS = 512
_lock = Lock()
_orchestration_request_ids: OrderedDict[str, None] = OrderedDict()


def mark_orchestration_request(request_id: str) -> None:
    normalized = str(request_id).strip()
    if not normalized:
        return
    with _lock:
        if normalized in _orchestration_request_ids:
            _orchestration_request_ids.move_to_end(normalized)
        else:
            _orchestration_request_ids[normalized] = None
        while len(_orchestration_request_ids) > _MAX_TRACKED_REQUESTS:
            _orchestration_request_ids.popitem(last=False)


def is_orchestration_handled(request_id: str) -> bool:
    normalized = str(request_id).strip()
    if not normalized:
        return False
    with _lock:
        return normalized in _orchestration_request_ids


def clear_orchestration_request(request_id: str) -> None:
    normalized = str(request_id).strip()
    if not normalized:
        return
    with _lock:
        _orchestration_request_ids.pop(normalized, None)
