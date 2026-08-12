"""EventBus shutdown / drain lifecycle (R4b single-queue)."""

from __future__ import annotations

import threading
import time

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import CHAT_CHUNK, UI_COMMAND


def test_shutdown_drains_accepted_async_events_before_returning() -> None:
    bus = EventBus(async_dispatch=True)
    received: list[int] = []

    def handler(event) -> None:
        received.append(int(event.payload["seq"]))

    bus.subscribe(CHAT_CHUNK, handler)
    for seq in (1, 2, 3):
        bus.publish(CHAT_CHUNK, {"seq": seq}, source="test")

    bus.shutdown()
    assert received == [1, 2, 3]
    assert bus.dispatch_queue_depth == 0


def test_shutdown_rejects_new_async_work() -> None:
    bus = EventBus(async_dispatch=True)
    seen: list[str] = []

    bus.subscribe(CHAT_CHUNK, lambda _e: seen.append("async"))
    bus.shutdown()

    event = bus.publish(CHAT_CHUNK, {"seq": 0}, source="test")
    assert event.delivery == "dropped"
    assert seen == []


def test_shutdown_worker_terminates_deterministically() -> None:
    bus = EventBus(async_dispatch=True)
    bus.shutdown()
    assert bus._dispatch_thread is None
    assert bus._dispatch_queue is None


def test_shutdown_does_not_deadlock_with_slow_handlers() -> None:
    bus = EventBus(async_dispatch=True)
    started = threading.Event()
    release = threading.Event()

    def slow_handler(_event) -> None:
        started.set()
        assert release.wait(timeout=2.0)

    bus.subscribe(CHAT_CHUNK, slow_handler)
    bus.publish(CHAT_CHUNK, {"seq": 1}, source="test")
    assert started.wait(timeout=2.0)

    done = threading.Event()

    def shutdown_in_thread() -> None:
        bus.shutdown(timeout=3.0)
        done.set()

    threading.Thread(target=shutdown_in_thread, daemon=True).start()
    time.sleep(0.05)
    release.set()
    assert done.wait(timeout=3.0)


def test_shutdown_preserves_sync_critical_inline_behavior() -> None:
    bus = EventBus(async_dispatch=True)
    seen: list[str] = []
    bus.subscribe(UI_COMMAND, lambda _e: seen.append("sync"))
    bus.shutdown()
    event = bus.publish(UI_COMMAND, {"text": "hello"}, source="test")
    assert event.delivery == "delivered"
    assert seen == ["sync"]


def test_fifo_ordering_intact_through_shutdown() -> None:
    bus = EventBus(async_dispatch=True)
    order: list[int] = []

    bus.subscribe(CHAT_CHUNK, lambda e: order.append(int(e.payload["seq"])))
    for seq in (10, 11, 12):
        bus.publish(CHAT_CHUNK, {"seq": seq}, source="test")
    bus.shutdown()
    assert order == [10, 11, 12]
