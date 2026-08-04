"""Batched main-thread UI updates (ARM64-tuned, event-driven, thread-safe enqueue)."""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)

_VIRTUAL_EVENT = "<<UIQueueItem>>"
_FALLBACK_INTERVAL_MS = 50
_IDLE_FALLBACK_INTERVAL_MS = 200

# Streaming interval for UI updates (verified by Phase 2 gate)
UI_STREAM_INTERVAL_MS = 50

# Drain budget: keep Tk responsive (~60fps). Cap items as a safety valve.
_DRAIN_BUDGET_S = 0.016
_DRAIN_MAX_ITEMS = 64


class UIQueue:
    """
    Coalesce callbacks onto the Tk main loop.

    ``enqueue`` is safe from any thread: callbacks are always placed on a
    ``SimpleQueue``. Tk wake-up (``event_generate``) runs **only** on the UI
    thread that constructed the queue. Background publishers rely on the
    fallback ``after`` poll (≤50 ms when work is pending) so they never block
    the EventBus waiting on the Tcl interpreter lock.

    ``_drain`` executes callbacks interleaved with a wall-clock budget so a
    burst of expensive work cannot starve the Tk event loop for an entire
    fixed-size batch.
    """

    def __init__(self, root, interval_ms: int = _FALLBACK_INTERVAL_MS) -> None:
        self._root = root
        self._interval = interval_ms
        self._idle_interval = max(interval_ms, _IDLE_FALLBACK_INTERVAL_MS)
        self._inbound: queue.SimpleQueue[Callable[[], None]] = queue.SimpleQueue()
        self._ui_thread = threading.current_thread()
        self._wake_pending = False
        self._root.bind(_VIRTUAL_EVENT, self._on_virtual_event, add="+")
        self._root.after(self._interval, self._fallback_poll)

    def enqueue(self, callback: Callable[[], None]) -> None:
        self._inbound.put(callback)
        if threading.current_thread() is not self._ui_thread:
            # Never call into Tk from a worker/asyncio thread — that can block
            # the EventBus for seconds while the main loop holds the Tcl lock.
            self._wake_pending = True
            return
        try:
            self._root.event_generate(_VIRTUAL_EVENT, when="tail")
        except Exception:
            self._wake_pending = True

    def _drain(self) -> None:
        """Execute queued callbacks until empty, max items, or time budget."""
        start = time.perf_counter()
        count = 0
        while count < _DRAIN_MAX_ITEMS:
            # Always run at least one callback when work exists; then respect budget.
            if count > 0 and (time.perf_counter() - start) >= _DRAIN_BUDGET_S:
                break
            try:
                fn = self._inbound.get_nowait()
            except queue.Empty:
                break
            count += 1
            try:
                fn()
            except Exception:
                logger.exception("UIQueue callback failed")

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if elapsed_ms > _DRAIN_BUDGET_S * 1000.0:
            logger.warning(
                "UIQueue drain took %.1fms (over %.0fms budget), callbacks=%s",
                elapsed_ms,
                _DRAIN_BUDGET_S * 1000.0,
                count,
            )
        # Leftover work: ensure the fallback poll stays in the fast path.
        if not self._inbound.empty():
            self._wake_pending = True

    def _on_virtual_event(self, _event=None) -> None:
        self._wake_pending = False
        self._drain()

    def _fallback_poll(self) -> None:
        has_work = self._wake_pending or not self._inbound.empty()
        if has_work:
            self._wake_pending = False
            self._drain()
        # Poll faster while work is flowing; back off when idle.
        delay = self._interval if has_work or not self._inbound.empty() else self._idle_interval
        self._root.after(delay, self._fallback_poll)
