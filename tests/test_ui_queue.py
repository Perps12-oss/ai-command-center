"""UIQueue main-thread dispatch."""

from __future__ import annotations

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
