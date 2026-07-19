"""Workflow run metadata persistence and AppState replay."""

from __future__ import annotations

import sqlite3

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    TOOL_INVOKE,
    WORKFLOW_COMPLETED,
    WORKFLOW_RUNS_LOADED,
    WORKFLOW_START,
    WORKFLOW_STARTED,
    WORKFLOW_STEP_COMPLETED,
)
from ai_command_center.repositories.database_bootstrap_repository import DatabaseBootstrapRepository
from ai_command_center.repositories.workflow_run_repository import WorkflowRunRepository
from ai_command_center.services.workflow_engine_service import WorkflowEngineService
from ai_command_center.services.workflow_persistence_service import WorkflowPersistenceService


def _memory_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    DatabaseBootstrapRepository().apply(conn)
    return conn


def test_workflow_run_repository_round_trip() -> None:
    conn = _memory_db()
    repo = WorkflowRunRepository(conn)

    repo.upsert_started(run_id="run-1", workflow_id="daily", total_steps=2, steps=[{"id": "a"}])
    repo.update_progress(run_id="run-1", current_step_index=1)
    stored = repo.finalize(run_id="run-1", state="completed", current_step_index=2)
    assert stored is not None
    assert stored.state == "completed"
    assert stored.workflow_id == "daily"
    assert stored.current_step_index == 2

    recent = repo.list_recent()
    assert len(recent) == 1
    assert recent[0].run_id == "run-1"


def test_workflow_persistence_replays_into_app_state() -> None:
    conn = _memory_db()
    repo = WorkflowRunRepository(conn)
    bus = EventBus()
    store = AppStateStore(bus)
    persistence = WorkflowPersistenceService(bus, repo=repo)
    persistence.start()

    bus.publish(
        WORKFLOW_STARTED,
        {
            "run_id": "run-persist",
            "workflow_id": "sync",
            "total_steps": 1,
            "steps": [{"id": "a", "type": "tool", "tool": "shell"}],
        },
        source="test",
    )
    bus.publish(
        WORKFLOW_STEP_COMPLETED,
        {"run_id": "run-persist", "step_id": "a", "index": 0, "success": True},
        source="test",
    )
    bus.publish(
        WORKFLOW_COMPLETED,
        {"run_id": "run-persist", "workflow_id": "sync", "steps": 1},
        source="test",
    )

    assert repo.get("run-persist") is not None
    assert repo.get("run-persist").state == "completed"
    assert store.snapshot.workflow_runs[0].run_id == "run-persist"

    fresh_store = AppStateStore(bus)
    bus.publish(
        WORKFLOW_RUNS_LOADED,
        {
            "runs": [
                {
                    "run_id": "run-persist",
                    "workflow_id": "sync",
                    "state": "completed",
                    "total_steps": 1,
                    "current_step_index": 1,
                    "error": "",
                }
            ]
        },
        source="test",
    )
    assert fresh_store.snapshot.workflow_runs[0].workflow_id == "sync"
    assert fresh_store.snapshot.workflow_runs[0].state == "completed"


def test_engine_and_persistence_vertical_slice() -> None:
    conn = _memory_db()
    repo = WorkflowRunRepository(conn)
    bus = EventBus()
    AppStateStore(bus)

    from ai_command_center.core.permission.permission_service import PermissionService
    from ai_command_center.core.tools import ToolResult, ToolSpec
    from ai_command_center.repositories.goal_repository import GoalRepository
    from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
    from ai_command_center.services.execution_orchestrator_service import (
        ExecutionOrchestratorService,
    )
    from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
    from ai_command_center.services.tool_executor_service import ToolExecutorService
    from ai_command_center.tools.tool_registry import ToolRegistry

    permission = PermissionService(bus)
    permission.wire_bus_handlers()
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(
            name="shell",
            description="shell",
            handler=lambda args: ToolResult(success=True, output="ok"),
        )
    )
    ToolExecutorService(bus, registry, permission_service=permission).start()
    goal_conn = sqlite3.connect(":memory:")
    goal_conn.row_factory = sqlite3.Row
    SingleGoalScheduler(bus, GoalRepository(goal_conn)).start()
    ExecutionOrchestratorService(bus).start()
    ExecutionAuthorityService(bus).start()
    WorkflowEngineService(bus).start()
    WorkflowPersistenceService(bus, repo=repo).start()

    invokes: list[dict] = []
    bus.subscribe(
        TOOL_INVOKE,
        lambda e: invokes.append(dict(e.payload) | {"_source": e.source}),
    )

    bus.publish(
        WORKFLOW_START,
        {
            "run_id": "run-engine",
            "workflow_id": "demo",
            "workspace_context": {"workspace_id": "ws-engine"},
            "steps": [{"id": "a", "type": "tool", "tool": "shell", "args": {"command": "echo"}}],
        },
        source="test",
    )

    stored = repo.get("run-engine")
    assert stored is not None
    assert stored.state == "completed"
    assert len(invokes) == 1
    assert invokes[0]["_source"] == "execution_orchestrator"
