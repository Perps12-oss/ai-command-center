"""PERF-002 — inspector fingerprint / AppState fan-out contracts (headless)."""

from __future__ import annotations

import inspect

from ai_command_center.core.app_state import (
    AppState,
    ExecutionRunItem,
    RuntimeProviderItem,
    WorkspaceOsEntity,
    WorkspaceOsSnapshot,
)
from ai_command_center.core.perf.metrics import PerfMetrics, get_perf_metrics
from ai_command_center.domain.orchestration_run_snapshot import OrchestrationRunSnapshot
from ai_command_center.domain.provider_health_snapshot import ProviderHealthSnapshot
from ai_command_center.ui.inspector_refresh import record_inspector_refresh
from ai_command_center.ui.orchestration_inspector import OrchestrationInspector
from ai_command_center.ui.performance_inspector import PerformanceInspector
from ai_command_center.ui.runtime_inspector import RuntimeInspector
from ai_command_center.ui.workspace_os_inspector import WorkspaceOsInspector


def test_performance_inspector_does_not_subscribe_to_appstate() -> None:
    """PERF-002 delete: metrics are not AppState — no fan-out subscription."""
    src = inspect.getsource(PerformanceInspector.__init__)
    assert "subscribe" not in src
    assert "after(1000" in src or "after(1000," in src


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


def test_performance_fingerprint_stable_for_identical_dump() -> None:
    bus = {
        "queue_depth": 0,
        "dropped_events": 0,
        "handler_invocations": 10,
        "handler_duration_avg_ms": 0.5,
    }
    timings = {"appstate.notify": {"avg_ms": 0.1, "max_ms": 0.2, "last_ms": 0.1, "n": 3}}
    counters = {"appstate.notify.count": 3}
    topics = [("chat.chunk", 5)]
    a = PerformanceInspector._fingerprint(
        uptime_s=1.0,
        bus_metrics=bus,
        navigate_dropped=0,
        timings=timings,
        counters=counters,
        top_topics=topics,
    )
    b = PerformanceInspector._fingerprint(
        uptime_s=1.0,
        bus_metrics=dict(bus),
        navigate_dropped=0,
        timings=dict(timings),
        counters=dict(counters),
        top_topics=list(topics),
    )
    assert a == b
    c = PerformanceInspector._fingerprint(
        uptime_s=2.0,
        bus_metrics=bus,
        navigate_dropped=0,
        timings=timings,
        counters=counters,
        top_topics=topics,
    )
    assert a != c


def test_record_inspector_refresh_skipped_counter() -> None:
    metrics = get_perf_metrics()
    before = dict(metrics.snapshot().get("counters") or {})
    record_inspector_refresh("runtime", 0.0, skipped=True)
    after = metrics.snapshot()["counters"]
    key = "inspector.refresh.runtime.skipped"
    assert int(after.get(key, 0)) == int(before.get(key, 0)) + 1


def test_record_inspector_refresh_timing_sample() -> None:
    # Use isolated metrics instance API via process singleton (observation only).
    assert isinstance(get_perf_metrics(), PerfMetrics)
    record_inspector_refresh("performance", 1.25, skipped=False)
    timings = get_perf_metrics().snapshot()["timings"]
    assert "inspector.refresh.performance" in timings
