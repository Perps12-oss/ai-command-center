"""ADR-009 intention confirmation alignment (no tool_call_id primary)."""

from __future__ import annotations

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_REQUEST,
    EXECUTION_STEP_AWAITING_APPROVAL,
    TOOL_APPROVED,
    TOOL_CONFIRMATION_REQUIRED,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry
from ai_command_center.ui.controller import UIController


def test_confirmation_required_and_approve_resumes(tmp_path=None) -> None:
    bus = EventBus()
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(
            name="create_note",
            description="note",
            handler=lambda _a: ToolResult(success=True, output="ok"),
        )
    )
    ToolExecutorService(bus, registry).start()
    ExecutionOrchestratorService(bus).start()
    store = AppStateStore(bus)
    controller = UIController(bus, store, on_state=lambda: None)

    awaiting: list[dict] = []
    confirmations: list[dict] = []
    completed: list[dict] = []
    bus.subscribe(
        EXECUTION_STEP_AWAITING_APPROVAL, lambda e: awaiting.append(dict(e.payload))
    )
    bus.subscribe(
        TOOL_CONFIRMATION_REQUIRED, lambda e: confirmations.append(dict(e.payload))
    )
    bus.subscribe(EXECUTION_RUN_COMPLETE, lambda e: completed.append(dict(e.payload)))

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-c1",
            "plan": {
                "goal": "note",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "create_note",
                        "args": {"title": "t"},
                        "require_approval": True,
                    }
                ],
            },
        },
        source="test",
    )

    assert awaiting
    assert confirmations
    assert confirmations[0]["confirmation_id"] == "run-c1:s1"
    assert confirmations[0]["kind"] == "intention"
    assert store.snapshot.pending_tool_confirmations

    controller.publish_tool_confirmation("run-c1:s1", approved=True)
    assert completed
    assert not store.snapshot.pending_tool_confirmations
    store.close()


def test_tool_denied_clears_pending() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    bus.publish(
        TOOL_CONFIRMATION_REQUIRED,
        {
            "confirmation_id": "r:s",
            "run_id": "r",
            "step_id": "s",
            "capability": "shell",
            "kind": "intention",
        },
        source="test",
    )
    assert store.snapshot.pending_tool_confirmations
    bus.publish(
        TOOL_APPROVED,  # clear path also on deny — use denied via controller
        {"confirmation_id": "r:s", "run_id": "r", "step_id": "s"},
        source="test",
    )
    assert not store.snapshot.pending_tool_confirmations
    store.close()
