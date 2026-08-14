"""R4c — EventBus per-handler async adapters and bounded queue."""

from __future__ import annotations

import threading
import time

from ai_command_center.core.event_bus import EVENT_OBSERVABILITY_METRIC, EventBus
from ai_command_center.core.events.handler_dispatch import HandlerDispatchMode
from ai_command_center.core.events.topics import CHAT_CHUNK, TELEMETRY_EVENT, UI_COMMAND


def test_async_queue_handler_runs_off_publish_thread() -> None:
    bus = EventBus(async_adapters=True)
    publish_tid: int | None = None
    handler_tid: int | None = None
    done = threading.Event()

    def handler(_event) -> None:
        nonlocal handler_tid
        handler_tid = threading.get_ident()
        done.set()

    bus.subscribe(CHAT_CHUNK, handler, dispatch_mode=HandlerDispatchMode.ASYNC_QUEUE)
    publish_tid = threading.get_ident()
    bus.publish(CHAT_CHUNK, {"seq": 1}, source="test")
    assert done.wait(timeout=2.0)
    assert handler_tid is not None
    assert handler_tid != publish_tid
    bus.shutdown()


def test_sync_critical_handler_stays_inline_even_with_async_queue_mode() -> None:
    bus = EventBus(async_adapters=True)
    publish_tid = threading.get_ident()
    handler_tid: int | None = None

    def handler(_event) -> None:
        nonlocal handler_tid
        handler_tid = threading.get_ident()

    bus.subscribe(UI_COMMAND, handler, dispatch_mode=HandlerDispatchMode.ASYNC_QUEUE)
    bus.publish(UI_COMMAND, {"text": "hello"}, source="test")
    assert handler_tid == publish_tid
    bus.shutdown()


def test_bounded_queue_drops_telemetry_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("EVENTBUS_QUEUE_DROP_TELEMETRY", "1")
    bus = EventBus(async_dispatch=True, queue_max_depth=1)
    started = threading.Event()
    release = threading.Event()

    def block(_event) -> None:
        started.set()
        release.wait(timeout=2.0)

    bus.subscribe(TELEMETRY_EVENT, block)
    first = bus.publish(TELEMETRY_EVENT, {"name": "first"}, source="test")
    assert first.delivery == "queued"
    assert started.wait(timeout=2.0)
    overflow = bus.publish(TELEMETRY_EVENT, {"name": "overflow"}, source="test")
    time.sleep(0.05)
    assert bus.dropped_events >= 1
    assert overflow.delivery == "dropped"
    release.set()
    bus.shutdown()


def test_publish_delivery_field_observable_on_sync_path() -> None:
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe(CHAT_CHUNK, lambda e: seen.append(e.topic))
    event = bus.publish(CHAT_CHUNK, {"seq": 1}, source="test")
    assert event.delivery == "delivered"
    assert seen == [CHAT_CHUNK]
    bus.shutdown()


def test_shutdown_drains_queued_async_events() -> None:
    """Queued work must run after shutdown is signalled (drain-on-shutdown)."""
    bus = EventBus(async_dispatch=True)
    started = threading.Event()
    release = threading.Event()
    processed: list[str] = []
    lock = threading.Lock()

    def slow_first(_event) -> None:
        started.set()
        release.wait(timeout=2.0)
        with lock:
            processed.append("first")

    def record(event) -> None:
        with lock:
            processed.append(str(event.payload.get("name", "")))

    bus.subscribe(CHAT_CHUNK, slow_first)
    bus.publish(CHAT_CHUNK, {"name": "first"}, source="test")
    assert started.wait(timeout=2.0)
    # Queue additional work while first handler is blocked.
    bus.subscribe(TELEMETRY_EVENT, record)
    # Force telemetry onto async path via async_dispatch + ASYNC_ELIGIBLE.
    for i in range(5):
        bus.publish(TELEMETRY_EVENT, {"name": f"t{i}"}, source="test")
    # Signal shutdown while work remains; then unblock first handler.
    done = threading.Event()

    def _shutdown() -> None:
        bus.shutdown(timeout=3.0)
        done.set()

    threading.Thread(target=_shutdown, name="bus-shutdown", daemon=True).start()
    time.sleep(0.05)
    release.set()
    assert done.wait(timeout=5.0)
    with lock:
        # first + all telemetry must have been processed (drained).
        assert "first" in processed
        for i in range(5):
            assert f"t{i}" in processed


def test_handler_duration_metrics_accumulate() -> None:
    bus = EventBus(debug_mode=True)

    bus.subscribe(CHAT_CHUNK, lambda _e: time.sleep(0.01))
    bus.publish(CHAT_CHUNK, {"seq": 0}, source="test")

    metrics = bus.get_handler_metrics()
    assert metrics["handler_invocations"] >= 1
    assert metrics["handler_duration_avg_ms"] > 0


def test_default_mode_ignores_async_queue_dispatch_mode() -> None:
    bus = EventBus()
    seen: list[str] = []

    bus.subscribe(
        CHAT_CHUNK,
        lambda _e: seen.append("ok"),
        dispatch_mode=HandlerDispatchMode.ASYNC_QUEUE,
    )
    bus.publish(CHAT_CHUNK, {"seq": 0}, source="test")
    assert seen == ["ok"]
    assert bus.async_adapters is False


def test_observability_metric_skipped_on_budget_exceed(monkeypatch) -> None:
    """Budget storms must not nest-publish observability.metric (freeze amplifier)."""
    monkeypatch.setenv("EVENTBUS_ASYNC_ADAPTERS", "0")
    bus = EventBus(debug_mode=True)
    metrics: list[dict] = []
    bus.subscribe(
        EVENT_OBSERVABILITY_METRIC,
        lambda e: metrics.append(dict(e.payload)),
    )

    def slow(_event) -> None:
        time.sleep(0.02)

    # UI_COMMAND sync-critical budget is 5ms — this exceeds it.
    from ai_command_center.core.events.topics import UI_COMMAND

    bus.subscribe(UI_COMMAND, slow)
    bus.publish(UI_COMMAND, {"text": "x"}, source="test")
    assert not any(
        m.get("metric_type") == "eventbus.handler.duration_ms" for m in metrics
    )
    bus.shutdown()


def test_observability_metric_on_fast_handler_in_debug(monkeypatch) -> None:
    monkeypatch.setenv("EVENTBUS_ASYNC_ADAPTERS", "0")
    bus = EventBus(debug_mode=True)
    metrics: list[dict] = []
    bus.subscribe(
        EVENT_OBSERVABILITY_METRIC,
        lambda e: metrics.append(dict(e.payload)),
    )
    bus.subscribe(CHAT_CHUNK, lambda _e: None)
    bus.publish(CHAT_CHUNK, {"seq": 0}, source="test")
    assert any(m.get("metric_type") == "eventbus.handler.duration_ms" for m in metrics)
    bus.shutdown()
