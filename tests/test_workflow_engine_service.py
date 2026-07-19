"""Workflow engine service tests (W1 — definition provider; Authority owns execution)."""

from __future__ import annotations

import sqlite3

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    TOOL_INVOKE,
    WORKFLOW_COMPLETED,
    WORKFLOW_START,
    WORKFLOW_STARTED,
)
from ai_command_center.core.permission.permission_service import PermissionService
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.services.tool_registry_service import ToolRegistryService
from ai_command_center.services.workflow_engine_service import WorkflowEngineService
from ai_command_center.tools.tool_registry import ToolRegistry


def _echo_tool(args: dict) -> ToolResult:
    return ToolResult(success=True, output=str(args.get("command", "ok")))


def _wire_workflow_stack(bus: EventBus) -> None:
    permission = PermissionService(bus)
    permission.wire_bus_handlers()
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="shell", description="test shell", handler=_echo_tool)
    )
    ToolRegistryService(bus, registry=registry).start()
    ToolExecutorService(bus, registry, permission_service=permission).start()
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    SingleGoalScheduler(bus, GoalRepository(conn)).start()
    ExecutionOrchestratorService(bus).start()
    ExecutionAuthorityService(bus).start()
    WorkflowEngineService(bus).start()


def test_two_step_tool_workflow_completes() -> None:
    bus = EventBus()
    _wire_workflow_stack(bus)

    completed: list[dict] = []
    bus.subscribe(WORKFLOW_COMPLETED, lambda e: completed.append(dict(e.payload)))

    invokes: list[dict] = []
    bus.subscribe(
        TOOL_INVOKE,
        lambda e: invokes.append(dict(e.payload) | {"_source": e.source}),
    )

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
    assert all(inv["_source"] == "execution_orchestrator" for inv in invokes)
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


def test_workflow_engine_does_not_publish_tool_invoke() -> None:
    bus = EventBus()
    invokes: list[dict] = []
    bus.subscribe(TOOL_INVOKE, lambda e: invokes.append(dict(e.payload) | {"_source": e.source}))
    WorkflowEngineService(bus).start()
    bus.publish(
        WORKFLOW_START,
        {
            "run_id": "run-no-exec",
            "workspace_context": {"workspace_id": "ws"},
            "steps": [{"id": "a", "type": "tool", "tool": "shell", "args": {"command": "x"}}],
        },
        source="test",
    )
    assert invokes == []
