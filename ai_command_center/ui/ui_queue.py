"""Batched main-thread UI updates (ARM64-tuned, event-driven, thread-safe enqueue)."""

from __future__ import annotations

import logging
import queue
from collections.abc import Callable

logger = logging.getLogger(__name__)

_VIRTUAL_EVENT = "<<UIQueueItem>>"
_FALLBACK_INTERVAL_MS = 200

# Streaming interval for UI updates (verified by Phase 2 gate)
UI_STREAM_INTERVAL_MS = 50


class UIQueue:
    """
    Coalesce callbacks onto the Tk main loop using a virtual-event wake-up.

    ``enqueue`` posts ``<<UIQueueItem>>`` so the main thread only wakes when
    there is actual work.  A lightweight fallback poll at 200 ms catches any
    items that arrive before the binding is active (e.g. during startup).
    """

    def __init__(self, root, interval_ms: int = _FALLBACK_INTERVAL_MS) -> None:
        self._root = root
        self._interval = interval_ms
        self._inbound: queue.SimpleQueue[Callable[[], None]] = queue.SimpleQueue()
        self._root.bind(_VIRTUAL_EVENT, self._on_virtual_event, add="+")
        self._root.after(self._interval, self._fallback_poll)

    def enqueue(self, callback: Callable[[], None]) -> None:
        self._inbound.put(callback)
        try:
            self._root.event_generate(_VIRTUAL_EVENT, when="tail")
        except Exception:
            pass

    def _drain(self) -> None:
        batch: list[Callable[[], None]] = []
        for _ in range(64):
            try:
                batch.append(self._inbound.get_nowait())
            except queue.Empty:
                break
        for fn in batch:
            try:
                fn()
            except Exception:
                logger.exception("UIQueue callback failed")

    def _on_virtual_event(self, _event=None) -> None:
        self._drain()

    def _fallback_poll(self) -> None:
        if not self._inbound.empty():
            self._drain()
        self._root.after(self._interval, self._fallback_poll)
