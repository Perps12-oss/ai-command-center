"""Workflow engine service tests (W1 skeleton)."""

from __future__ import annotations

from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    TOOL_INVOKE,
    TOOL_RESULT,
    WORKFLOW_COMPLETED,
    WORKFLOW_START,
    WORKFLOW_STARTED,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.services.tool_registry_service import ToolRegistryService
from ai_command_center.services.workflow_engine_service import WorkflowEngineService
from ai_command_center.tools.tool_registry import ToolRegistry


def _echo_tool(args: dict) -> ToolResult:
    return ToolResult(success=True, output=str(args.get("command", "ok")))


def test_two_step_tool_workflow_completes() -> None:
    bus = EventBus()
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="shell", description="test shell", handler=_echo_tool)
    )
    ToolRegistryService(bus, registry=registry).start()
    ToolExecutorService(bus, registry).start()
    WorkflowEngineService(bus).start()

    completed: list[dict] = []
    bus.subscribe(WORKFLOW_COMPLETED, lambda e: completed.append(dict(e.payload)))

    invokes: list[dict] = []

    def on_invoke(event) -> None:
        payload = dict(event.payload)
        invokes.append(payload)
        bus.publish(
            TOOL_RESULT,
            {
                "contract_version": TOOL_CONTRACT_VERSION,
                "invoke_id": payload.get("invoke_id", ""),
                "run_id": payload.get("run_id"),
                "step_id": payload.get("step_id"),
                "tool": payload.get("tool"),
                "success": True,
                "output": "ok",
            },
            source="test",
        )

    bus.subscribe(TOOL_INVOKE, on_invoke)

    bus.publish(
        WORKFLOW_START,
        {
            "run_id": "run-1",
            "workspace_context": {"workspace_id": "ws-test"},
            "steps": [
                {"id": "a", "type": "tool", "tool": "shell", "args": {"command": "echo 1"}},
                {"id": "b", "type": "tool", "tool": "shell", "args": {"command": "echo 2"}},
            ],
        },
        source="test",
    )

    assert len(invokes) == 2
    assert all(inv.get("workspace_context") == {"workspace_id": "ws-test"} for inv in invokes)
    assert all(inv.get("actor_type") == "workflow" for inv in invokes)
    assert completed
    assert completed[0]["run_id"] == "run-1"


def test_workflow_start_publishes_started() -> None:
    bus = EventBus()
    started: list[dict] = []
    bus.subscribe(WORKFLOW_STARTED, lambda e: started.append(dict(e.payload)))
    WorkflowEngineService(bus).start()

    bus.publish(
        WORKFLOW_START,
        {
            "run_id": "run-started",
            "workflow_id": "demo",
            "steps": [{"id": "a", "type": "tool", "tool": "shell"}],
        },
        source="test",
    )

    assert started
    assert started[0]["run_id"] == "run-started"
    assert started[0]["total_steps"] == 1
