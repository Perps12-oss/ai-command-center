"""Track 7 A4 — sequential agent pipeline via ExecutionAuthority."""

from __future__ import annotations

import sqlite3

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    AGENT_PIPELINE_COMPLETE,
    AGENT_PIPELINE_PLANNED,
    AGENT_PIPELINE_STAGE,
    AGENT_SPAWN_REQUEST,
    AGENT_TERMINATED,
    PERMISSION_CHECK_REQUEST,
    PERMISSION_CHECK_RESULT,
    UI_COMMAND,
)
from ai_command_center.core.permission.permission_service import PermissionService
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.services.agent_runtime_service import AgentRuntimeService
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.services.tool_registry_service import ToolRegistryService
from ai_command_center.tools.tool_registry import ToolRegistry


def _demo_shell_tool(args: dict) -> ToolResult:
    return ToolResult(success=True, output=str(args.get("command", "ok")))


def _wire_stack(bus: EventBus) -> AppStateStore:
    permission = PermissionService(bus)
    permission.wire_bus_handlers()

    def approve(event) -> None:
        if not event.payload.get("interactive"):
            return
        bus.publish(
            PERMISSION_CHECK_RESULT,
            {
                "check_id": event.payload["check_id"],
                "granted": True,
                "permissions": list(event.payload.get("permissions") or []),
                "actor_type": event.payload.get("actor_type", "agent"),
                "actor_id": event.payload.get("actor_id"),
            },
            source="ui",
        )

    bus.subscribe(PERMISSION_CHECK_REQUEST, approve)

    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="shell", description="demo shell", handler=_demo_shell_tool)
    )
    ToolRegistryService(bus, registry=registry).start()
    ToolExecutorService(bus, registry, permission_service=permission).start()
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    SingleGoalScheduler(bus, GoalRepository(conn)).start()
    ExecutionOrchestratorService(bus).start()
    agent = AgentRuntimeService(bus)
    agent.start()
    ExecutionAuthorityService(bus, agent_runtime=agent).start()
    return AppStateStore(bus)


def test_pipeline_demo_runs_research_then_review() -> None:
    bus = EventBus()
    store = _wire_stack(bus)

    stages: list[str] = []
    planned: list[list[str]] = []
    spawn_requests: list[dict] = []
    terminated: list[dict] = []
    completed: list[dict] = []

    bus.subscribe(
        AGENT_PIPELINE_STAGE,
        lambda e: stages.append(str(e.payload.get("stage", ""))),
    )
    bus.subscribe(
        AGENT_PIPELINE_PLANNED,
        lambda e: planned.append(list(e.payload.get("planned_tools") or [])),
    )
    bus.subscribe(
        AGENT_SPAWN_REQUEST,
        lambda e: spawn_requests.append(dict(e.payload)),
    )
    bus.subscribe(AGENT_TERMINATED, lambda e: terminated.append(dict(e.payload)))
    bus.subscribe(AGENT_PIPELINE_COMPLETE, lambda e: completed.append(dict(e.payload)))

    bus.publish(
        UI_COMMAND,
        {"text": "agents: pipeline demo", "workspace_id": "ws-pipe"},
        source="ui",
    )

    assert len(completed) == 1
    assert len(spawn_requests) == 2
    roles = {str(p.get("spawn_role")) for p in spawn_requests}
    assert roles == {"research", "review"}
    assert all(p.get("pipeline_id") for p in spawn_requests)
    assert len(terminated) == 2
    assert not any(t.get("error") for t in terminated)
    assert stages[0] == "research"
    assert stages[-1] == "review"
    assert len(planned) >= 2
    assert planned[0][0].startswith("shell:")

    snap = store.snapshot
    assert snap.agent_pipeline_stage == "complete"
    assert snap.active_agent_pipeline_id == ""
    assert len(snap.agent_runs) == 2
    assert {r.spawn_role for r in snap.agent_runs} == {"research", "review"}


def test_pipeline_permission_check_per_stage() -> None:
    """Authority-owned pipeline spawns skip interactive permission (execute_tools=False)."""
    bus = EventBus()
    store = _wire_stack(bus)
    checks: list[dict] = []

    bus.subscribe(PERMISSION_CHECK_REQUEST, lambda e: checks.append(dict(e.payload)))

    bus.publish(UI_COMMAND, {"text": "agents: pipeline demo", "workspace_id": "ws-pipe"}, source="ui")

    assert checks == []
    assert store.snapshot.agent_pipeline_stage == "complete"
