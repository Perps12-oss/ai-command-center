"""R4b — EventBus optional central dispatch queue."""

from __future__ import annotations

import threading

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import CHAT_CHUNK, UI_COMMAND


def test_async_eligible_topics_enqueue_and_preserve_order() -> None:
    bus = EventBus(async_dispatch=True)
    order: list[int] = []
    gate = threading.Event()

    bus.subscribe(CHAT_CHUNK, lambda _e: (order.append(1), gate.set()))
    bus.publish(CHAT_CHUNK, {"seq": 1}, source="test")
    assert gate.wait(timeout=2.0)
    assert order == [1]
    bus.shutdown()


def test_sync_critical_topics_bypass_queue() -> None:
    bus = EventBus(async_dispatch=True)
    seen: list[str] = []
    bus.subscribe(UI_COMMAND, lambda _e: seen.append("handled"))
    bus.publish(UI_COMMAND, {"text": "hello"}, source="test")
    assert seen == ["handled"]
    bus.shutdown()


def test_dispatch_queue_fifo_ordering() -> None:
    bus = EventBus(async_dispatch=True)
    received: list[int] = []
    done = threading.Event()

    def handler(event) -> None:
        received.append(int(event.payload["seq"]))
        if len(received) == 3:
            done.set()

    bus.subscribe(CHAT_CHUNK, handler)
    for seq in (1, 2, 3):
        bus.publish(CHAT_CHUNK, {"seq": seq}, source="test")

    assert done.wait(timeout=3.0)
    assert received == [1, 2, 3]
    bus.shutdown()


def test_default_mode_stays_synchronous_for_async_eligible() -> None:
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe(CHAT_CHUNK, lambda _e: seen.append("ok"))
    bus.publish(CHAT_CHUNK, {"seq": 0}, source="test")
    assert seen == ["ok"]
    assert bus.async_dispatch is False


def test_dispatch_reentry_respects_tiers() -> None:
    bus = EventBus(async_dispatch=True)
    seen: list[str] = []
    ready = threading.Event()
    bus.subscribe(CHAT_CHUNK, lambda _e: (seen.append("async"), ready.set()))
    bus.dispatch(Event(topic=CHAT_CHUNK, payload={"seq": 0}, source="test"))
    assert ready.wait(timeout=2.0)
    assert seen == ["async"]
    bus.shutdown()
