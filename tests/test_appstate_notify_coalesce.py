"""PERF-001 Phase 3: coalesce chat.chunk AppState notifies."""

from __future__ import annotations

import time

from ai_command_center.core.app_state import AppStateStore, notify_coalesce_ms_from_env
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import APP_PHASE, CHAT_CHUNK
from ai_command_center.core.perf import metrics as metrics_mod
from ai_command_center.core.perf.metrics import PerfMetrics, get_perf_metrics


def _fresh_metrics() -> PerfMetrics:
    metrics_mod._METRICS = PerfMetrics(maxlen=2048)
    return get_perf_metrics()


def test_notify_coalesce_ms_env(monkeypatch) -> None:
    monkeypatch.delenv("APPSTATE_NOTIFY_COALESCE_MS", raising=False)
    assert notify_coalesce_ms_from_env() == 40.0
    monkeypatch.setenv("APPSTATE_NOTIFY_COALESCE_MS", "0")
    assert notify_coalesce_ms_from_env() == 0.0
    monkeypatch.setenv("APPSTATE_NOTIFY_COALESCE_MS", "25")
    assert notify_coalesce_ms_from_env() == 25.0


def test_chat_chunk_notifies_are_coalesced(monkeypatch) -> None:
    monkeypatch.setenv("APPSTATE_NOTIFY_COALESCE_MS", "30")
    _fresh_metrics()
    bus = EventBus()
    store = AppStateStore(bus)
    seen = {"n": 0}
    try:
        store.subscribe(lambda _s: seen.__setitem__("n", seen["n"] + 1))
        # Establish streaming request so chunks append.
        bus.publish(
            "chat.started",
            {"request_id": "r1", "text": "hi"},
            source="test",
        )
        for i in range(50):
            bus.publish(
                CHAT_CHUNK,
                {"request_id": "r1", "text": "x", "index": i},
                source="test",
            )
        # Before flush window elapses, at most zero stream notifies delivered
        # (chat.started may have notified once immediately).
        immediate = seen["n"]
        time.sleep(0.05)
        after = seen["n"]
        snap = get_perf_metrics().snapshot()
        assert snap["counters"].get("appstate.notify.coalesced", 0) >= 50
        assert snap["counters"].get("appstate.notify.flush", 0) >= 1
        assert after >= immediate
        # 50 chunks must not produce 50 listener notifies.
        assert after - immediate <= 3
        assert snap["counters"].get(f"appstate.notify.topic.{CHAT_CHUNK}", 0) <= 3
    finally:
        store.close()


def test_non_stream_topics_still_notify_immediately(monkeypatch) -> None:
    monkeypatch.setenv("APPSTATE_NOTIFY_COALESCE_MS", "200")
    _fresh_metrics()
    bus = EventBus()
    store = AppStateStore(bus)
    seen: list[str] = []
    try:
        store.subscribe(lambda s: seen.append(s.phase))
        bus.publish(APP_PHASE, {"phase": "overlay"}, source="test")
        assert seen == ["overlay"]
    finally:
        store.close()


def test_coalesce_disabled_when_ms_zero(monkeypatch) -> None:
    monkeypatch.setenv("APPSTATE_NOTIFY_COALESCE_MS", "0")
    _fresh_metrics()
    bus = EventBus()
    store = AppStateStore(bus)
    seen = {"n": 0}
    try:
        store.subscribe(lambda _s: seen.__setitem__("n", seen["n"] + 1))
        bus.publish(
            "chat.started",
            {"request_id": "r1", "text": "hi"},
            source="test",
        )
        base = seen["n"]
        for i in range(10):
            bus.publish(
                CHAT_CHUNK,
                {"request_id": "r1", "text": "x", "index": i},
                source="test",
            )
        assert seen["n"] - base == 10
        assert get_perf_metrics().snapshot()["counters"].get(
            "appstate.notify.coalesced", 0
        ) == 0
    finally:
        store.close()
