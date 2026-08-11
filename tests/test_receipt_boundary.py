"""G1 receipt boundary — execution may not report success without an ExecutionReceipt.

Each test here fails at baseline 59262fe:
  * ``test_run_without_receipt_observer_fails_closed`` — the orchestrator used to
    publish EXECUTION_RUN_COMPLETE(success=True) with no receipt and no failure.
  * ``test_completion_without_correlation_id_still_receipts`` — OrchestrationService
    used to ``return`` early when request_id/run_id were absent, emitting neither
    receipt nor TruthBoundary validation.
"""

from __future__ import annotations

import threading
import webbrowser
from pathlib import Path

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
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
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


def _run_plan(bus: EventBus) -> None:
    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-g1",
            "request_id": "req-g1",
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


def test_run_without_receipt_observer_fails_closed() -> None:
    """No receipt observer composed → the run must NOT stand as a success."""
    bus = EventBus()
    _wire_tools(bus)
    ExecutionOrchestratorService(bus).start()
    # Deliberately no OrchestrationService — this is the G1 bypass.

    failed: list[dict] = []
    bus.subscribe(EXECUTION_RUN_FAILED, lambda e: failed.append(dict(e.payload)))

    _run_plan(bus)

    assert failed, "run completed with no receipt but never failed closed"
    assert failed[0].get("receipt_boundary_violation") is True
    assert failed[0].get("success") is False
    assert "receipt boundary violation" in str(failed[0].get("error", ""))


def test_run_with_receipt_observer_succeeds_and_is_receipted() -> None:
    """Canonical composition → receipt + truth validation, and no violation."""
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


def test_completion_without_correlation_id_still_receipts() -> None:
    """A completion carrying no request_id/run_id must still produce receipt + truth."""
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
            # no request_id, no run_id — the baseline early-return hole
            "goal": "untracked side effect",
            "success": True,
            "step_outputs": [{"step_id": "s1", "capability": "shell", "success": True}],
        },
        source="test",
    )

    assert receipts, "completion without a correlation id produced no ExecutionReceipt"
    assert truths, "completion without a correlation id skipped TruthBoundary"
    assert receipts[0]["request_id"], "synthesized receipt must carry a request_id"


def test_reused_request_id_does_not_inherit_a_stale_receipt() -> None:
    """A receipt from an earlier run must not satisfy a later run's guard.

    Workflow intake propagates a caller-supplied run_id as request_id, so ids can
    repeat. If the guard's ledger were not cleared per run, the second (unreceipted)
    run would pass on the first run's evidence.
    """
    bus = EventBus()
    registry = ToolRegistry()
    outcome = {"ok": False}

    def _toggling_tool(_args: object) -> ToolResult:
        if outcome["ok"]:
            return ToolResult(success=True, output="done")
        return ToolResult(success=False, output="", error="boom")

    registry.register_tool(
        ToolSpec(name="shell", description="shell", handler=_toggling_tool)
    )
    ToolExecutorService(bus, registry).start()
    ExecutionOrchestratorService(bus).start()
    observer = OrchestrationService(bus)
    observer.start()

    # Run 1 fails. The failure is receipted, seeding the guard's ledger with these ids.
    _run_plan(bus)

    # Drop the receipt observer, then succeed with the same ids.
    observer.stop()
    outcome["ok"] = True

    failed: list[dict] = []
    bus.subscribe(EXECUTION_RUN_FAILED, lambda e: failed.append(dict(e.payload)))

    _run_plan(bus)

    assert [f for f in failed if f.get("receipt_boundary_violation")], (
        "second run reused request_id and passed the guard on run 1's stale receipt"
    )


class _NoOpBrowser:
    """Suppress real browser launches while still reporting success."""

    def __init__(self) -> None:
        self.last_url: str | None = None

    def open(self, url: str, new: int = 0, autoraise: bool = True) -> bool:  # noqa: ARG002
        self.last_url = url
        return True


def test_workspace_os_launch_is_receipted() -> None:
    """G2: UI_LAUNCH_RESOURCE must run inside the boundary and produce a receipt.

    At baseline this launch reached ActionRegistry directly: real side effect,
    no ExecutionAuthority decision, no ExecutionReceipt, no TruthBoundary.
    """
    from ai_command_center.application import create_application
    from ai_command_center.db.connection import connect, init_database

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
                "resource_id": "resource-1",
            },
            source="test",
        )

        # TOOL_INVOKE is ASYNC_ELIGIBLE, so the run completes on the dispatch worker.
        assert got_receipt.wait(timeout=10), (
            "workspace OS launch produced no ExecutionReceipt — G2 bypass still open"
        )
        assert receipts, "expected at least one ExecutionReceipt for the launch"
    finally:
        app.shutdown()
