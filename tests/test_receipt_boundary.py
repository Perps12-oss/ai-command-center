"""G1 receipt boundary — COMPLETE cannot precede ExecutionReceipt evidence.

Invariant:
  NO RECEIPT → NO EXECUTION_RUN_COMPLETE → NO GoalStatus.COMPLETE
             → terminal EXECUTION_RUN_FAILED only
"""

from __future__ import annotations

import threading
import webbrowser
from pathlib import Path
from unittest.mock import patch

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    EXECUTION_RUN_REQUEST,
    ORCHESTRATION_RECEIPT,
    ORCHESTRATION_TRUTH_VALIDATED,
)
from ai_command_center.core.events.topics import UI_LAUNCH_RESOURCE
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.db.connection import connect, init_database
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.goal import Goal, GoalStatus, Priority
from ai_command_center.domain.planner_plan import ExecutionPlan, PlanStep
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
from ai_command_center.services.orchestration_service import OrchestrationService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry


def _ok_tool(_args: object) -> ToolResult:
    return ToolResult(success=True, output="done")


def _wire_tools(bus: EventBus) -> None:
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="shell", description="shell", handler=_ok_tool)
    )
    ToolExecutorService(bus, registry).start()


def _run_plan(bus: EventBus, *, run_id: str = "run-g1", request_id: str = "req-g1") -> None:
    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": run_id,
            "request_id": request_id,
            "auto_approve": True,
            "plan": {
                "goal": "do the thing",
                "steps": [
                    {
                        "step_id": "step-1",
                        "capability": "shell",
                        "args": {"command": "echo hi"},
                        "require_approval": False,
                    }
                ],
            },
        },
        source="test",
    )


def test_run_with_receipt_observer_succeeds_and_is_receipted() -> None:
    """T1/T4/T6: canonical path → COMPLETE, receipt, truth; no boundary FAILED."""
    bus = EventBus()
    _wire_tools(bus)
    ExecutionOrchestratorService(bus).start()
    OrchestrationService(bus).start()

    completed: list[dict] = []
    failed: list[dict] = []
    receipts: list[dict] = []
    truths: list[dict] = []
    bus.subscribe(EXECUTION_RUN_COMPLETE, lambda e: completed.append(dict(e.payload)))
    bus.subscribe(EXECUTION_RUN_FAILED, lambda e: failed.append(dict(e.payload)))
    bus.subscribe(ORCHESTRATION_RECEIPT, lambda e: receipts.append(dict(e.payload)))
    bus.subscribe(
        ORCHESTRATION_TRUTH_VALIDATED, lambda e: truths.append(dict(e.payload))
    )

    _run_plan(bus)

    assert completed, "expected the run to complete"
    assert receipts, "expected an ExecutionReceipt"
    assert truths, "expected TruthBoundary validation"
    assert not [f for f in failed if f.get("receipt_boundary_violation")], (
        "receipted run must not be flagged as a boundary violation"
    )
    assert receipts[0]["request_id"] == "req-g1"
    # Success receipt is emitted once (EOS gate); COMPLETE fanout must not duplicate.
    assert len([r for r in receipts if r.get("success") is True]) == 1


def test_no_complete_when_receipt_emit_returns_none() -> None:
    """T2: if receipt emit fails → FAILED only; never COMPLETE."""
    bus = EventBus()
    _wire_tools(bus)
    orch = ExecutionOrchestratorService(bus)
    orch.start()

    completed: list[dict] = []
    failed: list[dict] = []
    bus.subscribe(EXECUTION_RUN_COMPLETE, lambda e: completed.append(dict(e.payload)))
    bus.subscribe(EXECUTION_RUN_FAILED, lambda e: failed.append(dict(e.payload)))

    plan = ExecutionPlan(
        goal="probe",
        steps=(PlanStep(step_id="s1", capability="shell", args={"command": "echo"}),),
    )
    orch._runs["run-x"] = {
        "request_id": "req-x",
        "correlation": {},
        "plan": plan,
        "step_outputs": [{"capability": "shell", "success": True}],
        "observations": [],
        "workspace_context": {},
        "index": 1,
    }

    with patch(
        "ai_command_center.orchestration.receipts.boundary_emit.emit_execution_receipt",
        return_value=None,
    ):
        orch._complete_run("run-x")

    assert completed == []
    assert failed and failed[0].get("receipt_boundary_violation") is True


def test_goal_never_completes_without_receipt() -> None:
    """T3/T5: GoalStatus never COMPLETE; active goal not success-cleared."""
    db = init_database(connect(Path(":memory:")))
    bus = EventBus()
    repo = GoalRepository(db)
    sched = SingleGoalScheduler(bus, repo)
    sched.start()
    orch = ExecutionOrchestratorService(bus)
    orch.start()

    corr = CorrelationContext(correlation_id="corr-g", goal_id="goal-g")
    goal = Goal(
        id="goal-g",
        title="probe",
        status=GoalStatus.ACTIVE,
        priority=Priority.NORMAL,
        correlation=corr,
    )
    repo.save_goal(goal)
    sched._active_goal = goal
    sched._active_task_id = "run-g"

    completed: list[dict] = []
    failed: list[dict] = []
    bus.subscribe(EXECUTION_RUN_COMPLETE, lambda e: completed.append(dict(e.payload)))
    bus.subscribe(EXECUTION_RUN_FAILED, lambda e: failed.append(dict(e.payload)))

    plan = ExecutionPlan(
        goal="probe",
        steps=(PlanStep(step_id="s1", capability="navigate", args={"view": "home"}),),
    )
    orch._runs["run-g"] = {
        "request_id": "corr-g",
        "correlation": corr.to_payload(),
        "plan": plan,
        "step_outputs": [{"capability": "navigate", "success": True}],
        "observations": [],
        "workspace_context": {},
        "index": 1,
    }

    with patch(
        "ai_command_center.orchestration.receipts.boundary_emit.emit_execution_receipt",
        return_value=None,
    ):
        orch._complete_run("run-g")

    assert completed == []
    assert failed and failed[0].get("receipt_boundary_violation") is True
    stored = repo.get_goal("goal-g")
    assert stored is not None
    assert stored.status != GoalStatus.COMPLETE
    # Active goal may be cleared via the failure path — never via success COMPLETE.
    assert stored.status == GoalStatus.FAILED or sched._active_goal is not None


def test_completion_without_correlation_id_still_receipts() -> None:
    """Direct COMPLETE (legacy publishers) still synthesizes receipt via observer."""
    bus = EventBus()
    OrchestrationService(bus).start()

    receipts: list[dict] = []
    truths: list[dict] = []
    bus.subscribe(ORCHESTRATION_RECEIPT, lambda e: receipts.append(dict(e.payload)))
    bus.subscribe(
        ORCHESTRATION_TRUTH_VALIDATED, lambda e: truths.append(dict(e.payload))
    )

    bus.publish(
        EXECUTION_RUN_COMPLETE,
        {
            "goal": "untracked side effect",
            "success": True,
            "step_outputs": [{"step_id": "s1", "capability": "shell", "success": True}],
        },
        source="test",
    )

    assert receipts, "completion without a correlation id produced no ExecutionReceipt"
    assert truths, "completion without a correlation id skipped TruthBoundary"
    assert receipts[0]["request_id"], "synthesized receipt must carry a request_id"


def test_stale_receipt_cannot_satisfy_current_run() -> None:
    """T5: cleared stale ledger + failed emit → boundary FAILED."""
    bus = EventBus()
    orch = ExecutionOrchestratorService(bus)
    orch.start()

    orch._receipted_ids.add("req-stale")
    plan = ExecutionPlan(
        goal="probe",
        steps=(PlanStep(step_id="s1", capability="shell", args={"command": "echo"}),),
    )
    orch._runs["run-stale"] = {
        "request_id": "req-stale",
        "correlation": {},
        "plan": plan,
        "step_outputs": [{"capability": "shell", "success": True}],
        "observations": [],
        "workspace_context": {},
        "index": 1,
    }

    completed: list[dict] = []
    failed: list[dict] = []
    bus.subscribe(EXECUTION_RUN_COMPLETE, lambda e: completed.append(dict(e.payload)))
    bus.subscribe(EXECUTION_RUN_FAILED, lambda e: failed.append(dict(e.payload)))

    with patch(
        "ai_command_center.orchestration.receipts.boundary_emit.emit_execution_receipt",
        return_value=None,
    ):
        orch._complete_run("run-stale")

    assert completed == []
    assert failed and failed[0].get("receipt_boundary_violation") is True
    assert "req-stale" not in orch._receipted_ids


def test_eos_emits_receipt_before_complete_without_orchestration_service() -> None:
    """Receipt is structural in EOS (shared emit), not an optional observer."""
    bus = EventBus()
    _wire_tools(bus)
    ExecutionOrchestratorService(bus).start()
    # No OrchestrationService — fanout absent, but receipt+COMPLETE must still work.

    completed: list[dict] = []
    failed: list[dict] = []
    receipts: list[dict] = []
    bus.subscribe(EXECUTION_RUN_COMPLETE, lambda e: completed.append(dict(e.payload)))
    bus.subscribe(EXECUTION_RUN_FAILED, lambda e: failed.append(dict(e.payload)))
    bus.subscribe(ORCHESTRATION_RECEIPT, lambda e: receipts.append(dict(e.payload)))

    _run_plan(bus)

    assert receipts, "EOS must emit receipt before COMPLETE"
    assert completed, "receipted run must publish COMPLETE"
    assert not [f for f in failed if f.get("receipt_boundary_violation")]
    assert completed[0].get("receipt_already_emitted") is True


class _NoOpBrowser:
    def __init__(self) -> None:
        self.last_url: str | None = None

    def open(self, url: str, new: int = 0, autoraise: bool = True) -> bool:  # noqa: ARG002
        self.last_url = url
        return True


def test_workspace_os_launch_is_receipted() -> None:
    """G2: UI_LAUNCH_RESOURCE must run inside the boundary and produce a receipt."""
    from ai_command_center.application import create_application

    webbrowser.register("noop-receipt", None, _NoOpBrowser())
    webbrowser.get("noop-receipt")

    db = init_database(connect(Path(":memory:")))
    app = create_application(debug_mode=False, workspace_os_enabled=True, db=db)
    try:
        app.startup()

        receipts: list[dict] = []
        got_receipt = threading.Event()

        def _record(event: object) -> None:
            receipts.append(dict(event.payload))  # type: ignore[attr-defined]
            got_receipt.set()

        app.bus.subscribe(ORCHESTRATION_RECEIPT, _record)

        app.bus.publish(
            UI_LAUNCH_RESOURCE,
            {
                "resource_type": "url",
                "value": "https://example.com/receipted-launch",
                # Real entity ids are UUIDs; non-UUID values fail timeline parse
                # but must not block the G2 execution/receipt path.
                "resource_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            },
            source="test",
        )

        assert got_receipt.wait(timeout=10), (
            "workspace OS launch produced no ExecutionReceipt — G2 bypass still open"
        )
        assert receipts, "expected at least one ExecutionReceipt for the launch"
    finally:
        app.shutdown()
