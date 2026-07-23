"""UIQueue main-thread dispatch."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

from ai_command_center.ui.ui_queue import UIQueue


def test_ui_queue_drains_enqueued_callback() -> None:
    root = MagicMock()
    queue = UIQueue(root, interval_ms=60_000)
    seen: list[int] = []
    queue.enqueue(lambda: seen.append(1))
    queue._drain()
    assert seen == [1]


def test_ui_queue_batches_multiple_callbacks() -> None:
    root = MagicMock()
    queue = UIQueue(root, interval_ms=60_000)
    seen: list[int] = []
    queue.enqueue(lambda: seen.append(1))
    queue.enqueue(lambda: seen.append(2))
    queue._drain()
    assert seen == [1, 2]


def test_ui_queue_virtual_event_handler_drains() -> None:
    root = MagicMock()
    queue = UIQueue(root, interval_ms=60_000)
    seen: list[int] = []
    queue.enqueue(lambda: seen.append(1))
    queue._on_virtual_event()
    assert seen == [1]


def test_ui_queue_same_thread_enqueue_wakes_via_virtual_event() -> None:
    root = MagicMock()
    queue = UIQueue(root, interval_ms=60_000)
    root.event_generate.reset_mock()
    queue.enqueue(lambda: None)
    root.event_generate.assert_called()


def test_ui_queue_background_enqueue_does_not_touch_tk() -> None:
    """Regression: event_generate from worker threads blocked EventBus handlers."""
    root = MagicMock()
    queue = UIQueue(root, interval_ms=60_000)
    root.event_generate.reset_mock()
    seen: list[int] = []
    done = threading.Event()

    def worker() -> None:
        queue.enqueue(lambda: seen.append(1))
        done.set()

    thread = threading.Thread(target=worker, name="ui-queue-worker")
    thread.start()
    assert done.wait(timeout=2.0)
    thread.join(timeout=2.0)
    root.event_generate.assert_not_called()
    assert queue._wake_pending is True
    queue._fallback_poll()
    assert seen == [1]
