"""ADR-025 F3/F4 — orchestrator run cancel, creation lock, bounded LRU cache."""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_RUN_CANCEL,
    EXECUTION_RUN_FAILED,
    EXECUTION_RUN_REQUEST,
    EXECUTION_RUN_STARTED,
    EXECUTION_STEP_AWAITING_APPROVAL,
    TOOL_INVOKE,
)
from ai_command_center.services import execution_orchestrator_service as orch_mod
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)


def _hitl_plan(step_id: str = "s1") -> dict:
    return {
        "goal": "gated",
        "steps": [
            {
                "step_id": step_id,
                "capability": "notes.create",
                "args": {"title": "x"},
                "require_approval": True,
            }
        ],
    }


def test_max_active_runs_bound_is_positive_named_constant() -> None:
    assert orch_mod._MAX_ACTIVE_RUNS > 0
    assert orch_mod._MAX_RECEIPTED_IDS > 0


def test_creation_lock_refuses_duplicate_run_id() -> None:
    bus = EventBus(async_dispatch=False)
    orch = ExecutionOrchestratorService(bus)
    orch.start()
    failed: list[dict] = []
    bus.subscribe(EXECUTION_RUN_FAILED, lambda e: failed.append(dict(e.payload)))

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {"run_id": "run-dup", "plan": _hitl_plan("a"), "request_id": "r1"},
        source="test",
    )
    assert "run-dup" in orch._runs

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {"run_id": "run-dup", "plan": _hitl_plan("b"), "request_id": "r2"},
        source="test",
    )

    assert any(p.get("error") == "run already active" for p in failed)
    assert orch._runs["run-dup"]["plan"].steps[0].step_id == "a"
    orch.stop()


def test_run_cancel_stops_in_flight_run() -> None:
    bus = EventBus(async_dispatch=False)
    orch = ExecutionOrchestratorService(bus)
    orch.start()
    failed: list[dict] = []
    invokes: list[dict] = []
    bus.subscribe(EXECUTION_RUN_FAILED, lambda e: failed.append(dict(e.payload)))
    bus.subscribe(TOOL_INVOKE, lambda e: invokes.append(dict(e.payload)))

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {"run_id": "run-cancel", "plan": _hitl_plan(), "request_id": "rc"},
        source="test",
    )
    assert "run-cancel" in orch._runs

    bus.publish(
        EXECUTION_RUN_CANCEL,
        {"run_id": "run-cancel", "reason": "cancelled"},
        source="test",
    )

    assert "run-cancel" not in orch._runs
    assert any(p.get("error") == "cancelled" for p in failed)
    # HITL path awaits approval — cancel must not leave a live run for later invoke.
    assert not any(p.get("run_id") == "run-cancel" for p in invokes)
    orch.stop()


def test_active_run_cache_evicts_oldest_when_over_bound(monkeypatch) -> None:
    monkeypatch.setattr(orch_mod, "_MAX_ACTIVE_RUNS", 2)
    bus = EventBus(async_dispatch=False)
    orch = ExecutionOrchestratorService(bus)
    orch.start()
    failed: list[dict] = []
    started: list[str] = []
    bus.subscribe(EXECUTION_RUN_FAILED, lambda e: failed.append(dict(e.payload)))
    bus.subscribe(EXECUTION_RUN_STARTED, lambda e: started.append(str(e.payload.get("run_id"))))

    for i in range(3):
        bus.publish(
            EXECUTION_RUN_REQUEST,
            {
                "run_id": f"run-{i}",
                "plan": _hitl_plan(f"s{i}"),
                "request_id": f"req-{i}",
            },
            source="test",
        )

    assert len(orch._runs) == 2
    assert "run-0" not in orch._runs
    assert "run-1" in orch._runs and "run-2" in orch._runs
    assert any(
        p.get("run_id") == "run-0"
        and "evicted: active run cache bound exceeded" in str(p.get("error", ""))
        for p in failed
    )
    orch.stop()


def test_cancel_after_awaiting_approval_clears_run() -> None:
    bus = EventBus(async_dispatch=False)
    orch = ExecutionOrchestratorService(bus)
    orch.start()
    awaiting: list[dict] = []
    bus.subscribe(
        EXECUTION_STEP_AWAITING_APPROVAL, lambda e: awaiting.append(dict(e.payload))
    )

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {"run_id": "run-await", "plan": _hitl_plan(), "request_id": "ra"},
        source="test",
    )
    assert awaiting
    assert "run-await" in orch._runs

    bus.publish(EXECUTION_RUN_CANCEL, {"run_id": "run-await"}, source="test")
    assert "run-await" not in orch._runs
    orch.stop()
