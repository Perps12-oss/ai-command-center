"""PERF-002 — inspector fingerprint / AppState fan-out contracts (headless)."""

from __future__ import annotations

import pytest

try:
    import customtkinter as ctk
    _root = ctk.CTk()
    _root.destroy()
except Exception as exc:  # noqa: BLE001 — display / tk init probe
    pytest.skip(f"tkinter display unavailable: {exc}", allow_module_level=True)

from ai_command_center.core.app_state import (
    AppState,
    AppStateStore,
    ExecutionRunItem,
    RuntimeProviderItem,
    WorkspaceOsEntity,
    WorkspaceOsSnapshot,
)
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.perf.metrics import PerfMetrics, get_perf_metrics
from ai_command_center.domain.orchestration_run_snapshot import OrchestrationRunSnapshot
from ai_command_center.domain.provider_health_snapshot import ProviderHealthSnapshot
from ai_command_center.ui.inspector_refresh import record_inspector_refresh
from ai_command_center.ui.orchestration_inspector import OrchestrationInspector
from ai_command_center.ui.performance_inspector import PerformanceInspector
from ai_command_center.ui.runtime_inspector import RuntimeInspector
from ai_command_center.ui.ui_queue import UIQueue
from ai_command_center.ui.workspace_os_inspector import WorkspaceOsInspector


def _perf_fp_kwargs(**overrides):
    base = {
        "bus_metrics": {
            "queue_depth": 0,
            "dropped_events": 0,
            "handler_invocations": 10,
            "handler_duration_avg_ms": 0.5,
        },
        "navigate_dropped": 0,
        "timings": {
            "appstate.notify": {"avg_ms": 0.1, "max_ms": 0.2, "last_ms": 0.1, "n": 3}
        },
        "counters": {"appstate.notify.count": 3},
        "top_topics": [("chat.chunk", 5)],
    }
    base.update(overrides)
    return base


def test_performance_inspector_does_not_register_appstate_listener() -> None:
    """D5: behavioral probe — construction must not grow AppState listeners."""
    bus = EventBus()
    store = AppStateStore(bus)
    root = ctk.CTk()
    queue = UIQueue(root, interval_ms=60_000)
    try:
        before = len(store._listeners)
        inspector = PerformanceInspector(root, bus, store, ui_queue=queue)
        assert len(store._listeners) == before
        inspector.destroy()
    finally:
        store.close()
        root.destroy()


def test_performance_fingerprint_excludes_uptime_parameter() -> None:
    """S1/D3: equality fingerprint must not take monotonic uptime_s."""
    import inspect

    params = inspect.signature(PerformanceInspector._fingerprint).parameters
    assert "uptime_s" not in params


def test_performance_fingerprint_ignores_uptime_only_delta() -> None:
    """S1/D3: identical non-uptime metrics → equal fingerprint (skip path).

    Live uptime advances on the 1 Hz tick via ``_uptime_label`` only; it must
    not participate in equality, so two ticks with stable metrics share a fp.
    """
    kwargs = _perf_fp_kwargs()
    a = PerformanceInspector._fingerprint(**kwargs)
    b = PerformanceInspector._fingerprint(**kwargs)
    assert a == b


def test_performance_fingerprint_skip_vs_rebuild_contract() -> None:
    """S1: same non-uptime identity → equal; non-uptime field change → unequal."""
    a = PerformanceInspector._fingerprint(**_perf_fp_kwargs())
    b = PerformanceInspector._fingerprint(**_perf_fp_kwargs())
    assert a == b  # would skip rebuild

    c = PerformanceInspector._fingerprint(
        **_perf_fp_kwargs(
            bus_metrics={
                "queue_depth": 1,
                "dropped_events": 0,
                "handler_invocations": 10,
                "handler_duration_avg_ms": 0.5,
            }
        )
    )
    assert a != c  # must rebuild

    d = PerformanceInspector._fingerprint(
        **_perf_fp_kwargs(counters={"appstate.notify.count": 99})
    )
    assert a != d


def test_runtime_fingerprint_ignores_identical_content() -> None:
    health = ProviderHealthSnapshot(
        provider_id="ollama",
        status="healthy",
        detail="ok",
        source="runtime",
    )
    run_item = ExecutionRunItem(
        run_id="r1",
        request_id="req-1",
        source="chat",
        summary="done",
    )
    provider = RuntimeProviderItem(
        provider_id="ollama",
        name="Ollama",
        version="1",
        capabilities=("chat",),
        permissions=(),
        health_state="healthy",
        health_detail="",
    )
    orch = OrchestrationRunSnapshot(
        request_id="req-1",
        query="hi",
        intent="chat",
        provider_id="ollama",
        receipt_id="rcpt",
        execution_success=True,
        truth_valid=True,
        response_text="hello",
    )
    a = AppState(
        orchestration_run=orch,
        execution_runs=(run_item,),
        provider_health_map=(health,),
        runtime_capability_providers=(provider,),
    )
    b = AppState(
        orchestration_run=orch,
        execution_runs=(run_item,),
        provider_health_map=(health,),
        runtime_capability_providers=(provider,),
    )
    assert RuntimeInspector._fingerprint(a) == RuntimeInspector._fingerprint(b)


def test_runtime_fingerprint_tracks_provider_status_not_just_count() -> None:
    """Length-only fingerprints missed status flips (PERF-002 strengthen)."""
    healthy = ProviderHealthSnapshot(
        provider_id="ollama", status="healthy", detail="ok", source="runtime"
    )
    offline = ProviderHealthSnapshot(
        provider_id="ollama", status="offline", detail="down", source="runtime"
    )
    a = AppState(provider_health_map=(healthy,))
    b = AppState(provider_health_map=(offline,))
    assert RuntimeInspector._fingerprint(a) != RuntimeInspector._fingerprint(b)


def test_runtime_fingerprint_tracks_capability_health() -> None:
    ready = RuntimeProviderItem(
        provider_id="p1",
        name="P",
        version="1",
        health_state="healthy",
        health_detail="",
    )
    degraded = RuntimeProviderItem(
        provider_id="p1",
        name="P",
        version="1",
        health_state="degraded",
        health_detail="slow",
    )
    a = AppState(runtime_capability_providers=(ready,))
    b = AppState(runtime_capability_providers=(degraded,))
    assert RuntimeInspector._fingerprint(a) != RuntimeInspector._fingerprint(b)


def test_orchestration_fingerprint_stable_for_identical_run() -> None:
    run = OrchestrationRunSnapshot(
        intent="chat",
        provider_id="ollama",
        request_id="r1",
        receipt_id="rc1",
        query="q",
        execution_success=True,
        truth_valid=True,
        response_text="ok",
    )
    assert OrchestrationInspector._fingerprint(run) == OrchestrationInspector._fingerprint(run)


def test_workspace_os_fingerprint_tracks_entity_title() -> None:
    e1 = WorkspaceOsEntity(entity_id="1", entity_type="card", title="A")
    e2 = WorkspaceOsEntity(entity_id="1", entity_type="card", title="B")
    a = WorkspaceOsSnapshot(entity_count=1, entities=(e1,))
    b = WorkspaceOsSnapshot(entity_count=1, entities=(e2,))
    assert WorkspaceOsInspector._fingerprint(a) != WorkspaceOsInspector._fingerprint(b)
    assert WorkspaceOsInspector._fingerprint(a) == WorkspaceOsInspector._fingerprint(a)


def test_record_inspector_refresh_skipped_counter() -> None:
    metrics = get_perf_metrics()
    before = dict(metrics.snapshot().get("counters") or {})
    record_inspector_refresh("runtime", 0.0, skipped=True)
    after = metrics.snapshot()["counters"]
    key = "inspector.refresh.runtime.skipped"
    assert int(after.get(key, 0)) == int(before.get(key, 0)) + 1


def test_record_inspector_refresh_timing_sample() -> None:
    assert isinstance(get_perf_metrics(), PerfMetrics)
    record_inspector_refresh("performance", 1.25, skipped=False)
    timings = get_perf_metrics().snapshot()["timings"]
    assert "inspector.refresh.performance" in timings
