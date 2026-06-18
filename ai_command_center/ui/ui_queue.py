"""Batched main-thread UI updates (ARM64-tuned, thread-safe enqueue)."""

from __future__ import annotations

import queue
from collections.abc import Callable

UI_STREAM_INTERVAL_MS = 50


class UIQueue:
    """Coalesce callbacks onto the Tk main loop at a fixed interval."""

    def __init__(self, root, interval_ms: int = UI_STREAM_INTERVAL_MS) -> None:
        self._root = root
        self._interval = interval_ms
        self._inbound: queue.SimpleQueue[Callable[[], None]] = queue.SimpleQueue()
        self._root.after(self._interval, self._poll)

    def enqueue(self, callback: Callable[[], None]) -> None:
        self._inbound.put(callback)

    def _poll(self) -> None:
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
                continue
        self._root.after(self._interval, self._poll)
