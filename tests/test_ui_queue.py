"""UIQueue main-thread dispatch."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

from ai_command_center.ui import ui_queue as ui_queue_mod
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


def test_ui_queue_drain_respects_time_budget(monkeypatch) -> None:
    """Expensive callbacks must not run unbounded within one drain."""
    monkeypatch.setattr(ui_queue_mod, "_DRAIN_BUDGET_S", 0.005)
    root = MagicMock()
    queue = UIQueue(root, interval_ms=60_000)
    ran: list[int] = []

    def slow() -> None:
        ran.append(1)
        time.sleep(0.003)

    for _ in range(20):
        queue.enqueue(slow)

    start = time.perf_counter()
    queue._drain()
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    assert 1 <= len(ran) < 20
    assert not queue._inbound.empty()
    assert queue._wake_pending is True
    # Soft ceiling: budget + a little slack for scheduling noise.
    assert elapsed_ms < 40.0


def test_ui_queue_drain_always_runs_at_least_one() -> None:
    root = MagicMock()
    queue = UIQueue(root, interval_ms=60_000)
    seen: list[int] = []
    queue.enqueue(lambda: seen.append(1))
    queue._drain()
    assert seen == [1]
    assert queue._inbound.empty()
