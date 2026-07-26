"""Phase 2 instrumentation: AppState notify PerfMetrics (observation only)."""

from __future__ import annotations

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import APP_PHASE, SYSTEM_SNAPSHOT
from ai_command_center.core.perf import metrics as metrics_mod
from ai_command_center.core.perf.metrics import PerfMetrics, get_perf_metrics


def _fresh_metrics() -> PerfMetrics:
    metrics_mod._METRICS = PerfMetrics(maxlen=512)
    return get_perf_metrics()


def test_notify_metrics_record_listener_fanout() -> None:
    _fresh_metrics()
    bus = EventBus()
    store = AppStateStore(bus)
    seen: list[str] = []
    try:
        store.subscribe(lambda s: seen.append(s.phase))
        bus.publish(APP_PHASE, {"phase": "overlay"}, source="test")
        snap = get_perf_metrics().snapshot()
        assert snap["counters"].get("appstate.notify", 0) >= 1
        assert snap["counters"].get("appstate.notify.listener_invocations", 0) >= 1
        assert snap["counters"].get(f"appstate.notify.topic.{APP_PHASE}", 0) >= 1
        assert "appstate.notify" in snap["timings"]
        assert seen == ["overlay"]
    finally:
        store.close()


def test_notify_skipped_no_listeners_counter() -> None:
    _fresh_metrics()
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        bus.publish(APP_PHASE, {"phase": "idle"}, source="test")
        snap = get_perf_metrics().snapshot()
        assert snap["counters"].get("appstate.notify.skipped.no_listeners", 0) >= 1
        assert snap["counters"].get("appstate.notify", 0) == 0
        assert "appstate.notify" not in snap["timings"]
    finally:
        store.close()


def test_notify_skipped_metrics_only_system_snapshot() -> None:
    _fresh_metrics()
    bus = EventBus()
    store = AppStateStore(bus)
    notifies = {"n": 0}
    try:
        store.subscribe(lambda _s: notifies.__setitem__("n", notifies["n"] + 1))
        # Structural first publish (establishes baseline snapshot fields).
        bus.publish(
            SYSTEM_SNAPSHOT,
            {
                "cpu_percent": 1.0,
                "ram_percent": 40.0,
                "ollama_online": False,
                "extra": {"openai_online": False},
            },
            source="test",
        )
        before_skip = get_perf_metrics().snapshot()["counters"].get(
            "appstate.notify.skipped.metrics_only", 0
        )
        notifies_after_first = notifies["n"]
        assert notifies_after_first >= 1
        # Metrics-only delta: cpu change only → dirty reduce, no listener notify.
        bus.publish(
            SYSTEM_SNAPSHOT,
            {
                "cpu_percent": 9.0,
                "ram_percent": 40.0,
                "ollama_online": False,
                "extra": {"openai_online": False},
            },
            source="test",
        )
        snap = get_perf_metrics().snapshot()
        assert (
            snap["counters"].get("appstate.notify.skipped.metrics_only", 0)
            > before_skip
        )
        assert notifies["n"] == notifies_after_first
    finally:
        store.close()
