"""Phase 5 — AsyncDispatchQueue multi-pool workers and shutdown."""

from __future__ import annotations

import threading
import time

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.async_dispatch_queue import (
    AsyncDispatchQueue,
    PoolConfig,
)
from ai_command_center.core.events.topics import (
    CHAT_CHUNK,
    TOOL_INVOKE,
    UI_COMMAND,
    WORKFLOW_STARTED,
)


def test_async_dispatch_queue_invokes_on_worker() -> None:
    publish_tid = threading.get_ident()
    handler_tid: list[int] = []
    done = threading.Event()

    def invoke(event, handler) -> None:
        handler_tid.append(threading.get_ident())
        if handler is not None:
            handler(event)
        done.set()

    q = AsyncDispatchQueue(
        invoke=invoke,
        pools=(PoolConfig(name="tool_execution", workers=1, queue_size=10),),
    )
    event = Event(topic=TOOL_INVOKE, payload={}, source="test")
    assert q.enqueue("tool_execution", event, lambda _e: None)
    assert done.wait(timeout=2.0)
    assert handler_tid and handler_tid[0] != publish_tid
    q.shutdown()


def test_worker_pool_shutdown_drains() -> None:
    invoked = threading.Event()

    def invoke(event, handler) -> None:
        if handler:
            handler(event)
        invoked.set()

    q = AsyncDispatchQueue(
        invoke=invoke,
        pools=(PoolConfig(name="workflow", workers=2, queue_size=10),),
    )
    q.enqueue(
        "workflow",
        Event(topic=WORKFLOW_STARTED, payload={}, source="test"),
        lambda _e: None,
    )
    assert invoked.wait(timeout=2.0)
    q.shutdown(timeout=2.0)
    assert q.depth == 0


def test_tiered_eventbus_routes_pools_off_publish_thread() -> None:
    bus = EventBus(tiered_dispatch=True)
    publish_tid = threading.get_ident()
    seen: dict[str, int] = {}
    done = threading.Event()

    def make_handler(name: str):
        def _handler(_event) -> None:
            seen[name] = threading.get_ident()
            if len(seen) >= 2:
                done.set()

        return _handler

    bus.subscribe(TOOL_INVOKE, make_handler("tool"))
    bus.subscribe(CHAT_CHUNK, make_handler("chat"))
    bus.publish(TOOL_INVOKE, {}, source="test")
    bus.publish(CHAT_CHUNK, {"seq": 1}, source="test")
    assert done.wait(timeout=3.0)
    assert seen["tool"] != publish_tid
    assert seen["chat"] != publish_tid
    bus.shutdown()


def test_tiered_sync_critical_stays_on_publish_thread() -> None:
    bus = EventBus(tiered_dispatch=True)
    publish_tid = threading.get_ident()
    handler_tid: list[int] = []

    bus.subscribe(UI_COMMAND, lambda _e: handler_tid.append(threading.get_ident()))
    bus.publish(UI_COMMAND, {"text": "x"}, source="test")
    assert handler_tid == [publish_tid]
    bus.shutdown()


def test_model_queue_isolation_from_blocked_tool_pool() -> None:
    """R4d model pool must progress while R4b tool worker is blocked."""
    bus = EventBus(
        tiered_dispatch=True,
        pool_configs=(
            PoolConfig(name="tool_execution", workers=1, queue_size=10),
            PoolConfig(name="workflow", workers=1, queue_size=10),
            PoolConfig(name="model", workers=1, queue_size=10),
        ),
    )
    tool_started = threading.Event()
    tool_release = threading.Event()
    model_done = threading.Event()

    def block_tool(_event) -> None:
        tool_started.set()
        tool_release.wait(timeout=3.0)

    bus.subscribe(TOOL_INVOKE, block_tool)
    bus.subscribe(CHAT_CHUNK, lambda _e: model_done.set())

    bus.publish(TOOL_INVOKE, {}, source="test")
    assert tool_started.wait(timeout=2.0)
    bus.publish(CHAT_CHUNK, {"seq": 1}, source="test")
    assert model_done.wait(timeout=2.0), "model pool blocked by tool pool"
    tool_release.set()
    # Drain tool handler
    deadline = time.monotonic() + 2.0
    while bus.dispatch_queue_depth > 0 and time.monotonic() < deadline:
        time.sleep(0.02)
    bus.shutdown()


def test_r4a_dispatch_latency_p95_under_50ms() -> None:
    """Phase 5 exit 5.4 — R4a (sync-critical) publish→handler p95 < 50ms."""
    bus = EventBus(tiered_dispatch=True)
    samples: list[float] = []

    def handler(_event) -> None:
        pass

    bus.subscribe(UI_COMMAND, handler)
    for _ in range(200):
        start = time.perf_counter()
        bus.publish(UI_COMMAND, {"text": "x"}, source="test")
        samples.append((time.perf_counter() - start) * 1000.0)

    samples.sort()
    p95 = samples[int(len(samples) * 0.95)]
    assert p95 < 50.0, f"R4a p95={p95:.3f}ms exceeds 50ms"
    bus.shutdown()


def test_default_eventbus_remains_sync() -> None:
    bus = EventBus()
    assert bus.tiered_dispatch is False
    assert bus.async_dispatch is False
    seen: list[str] = []
    bus.subscribe(CHAT_CHUNK, lambda _e: seen.append("ok"))
    bus.publish(CHAT_CHUNK, {"seq": 0}, source="test")
    assert seen == ["ok"]
