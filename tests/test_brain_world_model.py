"""Brain World Model repository, runtime, scheduler, observer, and kernel tests."""

from __future__ import annotations

import sqlite3
from types import SimpleNamespace

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.service_factory import _observer_roots_from_settings
from ai_command_center.core.events.topics import (
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    GOAL_COMPLETED,
    GOAL_FAILED,
    GOAL_SUBMITTED,
    GOAL_SUBMIT_REQUEST,
    KERNEL_STATE_CHANGED,
    KERNEL_TRANSITION_REJECTED,
    PLAN_GENERATED,
    PLAN_REQUEST,
    RUNTIME_ACTION_COMPLETED,
    RUNTIME_ACTION_DENIED,
    RUNTIME_ACTION_REQUEST,
    RUNTIME_ACTION_STARTED,
    RUNTIME_APPROVAL_DECIDED,
    RUNTIME_APPROVAL_REQUESTED,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.core.world_model.world_model import WorldModel
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.goal import Goal
from ai_command_center.domain.kernel_state import KernelState
from ai_command_center.domain.runtime_safety import SecurityTier
from ai_command_center.domain.world_model import Mutation, MutationType, Node
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.repositories.world_model_repository import SQLiteWorldModelRepository
from ai_command_center.services.brain_kernel_service import BrainKernelService
from ai_command_center.services.brain_runtime_service import BrainRuntimeService
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
from ai_command_center.services.observer_service import ObserverService
from ai_command_center.services.planner_service import parse_structured_plan_response
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_world_model_repository_replays_last_five_mutations() -> None:
    conn = _conn()
    repo = SQLiteWorldModelRepository(conn)
    correlation = CorrelationContext.new(goal_id="goal-1")

    for index in range(7):
        node = Node(id=f"node-{index}", type="resource", attributes={"index": index})
        mutation = Mutation(
            id=f"mutation-{index}",
            correlation=correlation.with_action(f"action-{index}"),
            type=MutationType.CREATE_NODE,
            payload={"node": node.to_payload()},
        )
        repo.apply_mutation(mutation)

    replay = repo.replay_mutations(limit=5)

    assert [item.id for item in replay] == [f"mutation-{index}" for index in range(2, 7)]
    assert all(item.type == MutationType.CREATE_NODE for item in replay)
    assert replay[-1].correlation.goal_id == "goal-1"
    assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 7
    assert (
        conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='world_nodes'"
        ).fetchone()
        is None
    )


def test_runtime_applies_world_model_mutation_and_requires_destroy_approval() -> None:
    bus = EventBus()
    repo = SQLiteWorldModelRepository(_conn())
    runtime = BrainRuntimeService(bus, WorldModel(repo))
    runtime.start()

    completed: list[dict] = []
    denied: list[dict] = []
    bus.subscribe(RUNTIME_ACTION_COMPLETED, lambda e: completed.append(dict(e.payload)))
    bus.subscribe(RUNTIME_ACTION_DENIED, lambda e: denied.append(dict(e.payload)))
    bus.subscribe(
        RUNTIME_APPROVAL_REQUESTED,
        lambda e: bus.publish(
            RUNTIME_APPROVAL_DECIDED,
            {
                "approval_id": e.payload["id"],
                "approved": False,
                "reason": "test deny",
            },
            source="test",
        ),
    )
    correlation = CorrelationContext.new(goal_id="goal-1", action_id="action-1")
    mutation = Mutation(
        id="mutation-1",
        correlation=correlation,
        type=MutationType.UPDATE_NODE,
        payload={"node": Node(id="n1", type="resource").to_payload()},
    )

    bus.publish(
        RUNTIME_ACTION_REQUEST,
        {
            "action_id": "action-1",
            "tier": SecurityTier.READ.value,
            "mutation": mutation.to_payload(),
            "correlation": correlation.to_payload(),
        },
        source="test",
    )
    bus.publish(
        RUNTIME_ACTION_REQUEST,
        {
            "action_id": "delete-1",
            "tier": SecurityTier.WRITE_DESTROY.value,
            "correlation": correlation.with_action("delete-1").to_payload(),
        },
        source="test",
    )

    assert repo.get_node("n1") is not None
    assert completed[0]["correlation"]["goal_id"] == "goal-1"
    assert denied[0]["status"] == "denied"


def test_runtime_does_not_auto_approve_destructive_actions() -> None:
    bus = EventBus()
    runtime = BrainRuntimeService(bus, WorldModel(SQLiteWorldModelRepository(_conn())))
    runtime.start()
    approvals: list[dict] = []
    completed: list[dict] = []
    bus.subscribe(RUNTIME_APPROVAL_REQUESTED, lambda e: approvals.append(dict(e.payload)))
    bus.subscribe(RUNTIME_ACTION_COMPLETED, lambda e: completed.append(dict(e.payload)))

    bus.publish(
        RUNTIME_ACTION_REQUEST,
        {
            "action_id": "destroy-1",
            "tier": SecurityTier.WRITE_DESTROY.value,
            "auto_approve": True,
        },
        source="test",
    )

    assert approvals
    assert not completed


def test_runtime_approval_decision_after_timeout_is_ignored_safely() -> None:
    bus = EventBus()
    runtime = BrainRuntimeService(bus, WorldModel(SQLiteWorldModelRepository(_conn())))
    runtime.start()
    approvals: list[dict] = []
    denied: list[dict] = []
    bus.subscribe(RUNTIME_APPROVAL_REQUESTED, lambda e: approvals.append(dict(e.payload)))
    bus.subscribe(RUNTIME_ACTION_DENIED, lambda e: denied.append(dict(e.payload)))

    bus.publish(
        RUNTIME_ACTION_REQUEST,
        {
            "action_id": "destroy-2",
            "tier": SecurityTier.WRITE_DESTROY.value,
            "timeout_seconds": 60,
        },
        source="test",
    )
    approval_id = approvals[0]["id"]
    runtime._deny_approval(approval_id, "approval timeout")
    bus.publish(
        RUNTIME_APPROVAL_DECIDED,
        {"approval_id": approval_id, "approved": True},
        source="test",
    )

    assert denied[0]["status"] == "timed_out"


def test_app_state_projects_brain_events() -> None:
    bus = EventBus()
    state_store = AppStateStore(bus)

    bus.publish(
        KERNEL_STATE_CHANGED,
        {"from": "boot", "to": "idle"},
        source="test",
    )
    bus.publish(
        GOAL_SUBMITTED,
        {"goal": {"id": "goal-1", "title": "Organize Downloads"}},
        source="test",
    )
    bus.publish(
        RUNTIME_ACTION_STARTED,
        {"action_id": "action-1", "status": "started"},
        source="test",
    )

    snapshot = state_store.snapshot
    assert snapshot.brain_kernel_state == "idle"
    assert snapshot.brain_recent_goals[0]["id"] == "goal-1"
    assert snapshot.brain_recent_goals[0]["goal_id"] == "goal-1"
    assert snapshot.brain_recent_goals[0]["status"] == "submitted"
    assert snapshot.brain_recent_runtime_actions[0]["action_id"] == "action-1"


def test_structured_planner_response_parses_llm_manifest() -> None:
    plan = parse_structured_plan_response(
        """
        {
          "goal": "Organize Downloads",
          "confidence": 0.9,
          "steps": [
            {
              "step_id": "s1",
              "capability": "create_task",
              "args": {"title": "Organize Downloads"},
              "require_approval": false
            }
          ]
        }
        """
    )

    assert plan.goal == "Organize Downloads"
    assert plan.steps[0].capability == "create_task"


def test_structured_planner_response_strips_non_json_fence_language() -> None:
    plan = parse_structured_plan_response(
        """```typescript
        {
          "goal": "Organize Downloads",
          "confidence": 0.9,
          "steps": [{"step_id": "s1", "capability": "create_task"}]
        }
        ```"""
    )

    assert plan.steps[0].step_id == "s1"


def test_observer_startup_sync_emits_file_observation_into_world_model(tmp_path) -> None:
    watched = tmp_path / "downloads"
    watched.mkdir()
    file_path = watched / "example.txt"
    file_path.write_text("hello", encoding="utf-8")

    bus = EventBus()
    repo = SQLiteWorldModelRepository(_conn())
    runtime = BrainRuntimeService(bus, WorldModel(repo))
    observer = ObserverService(bus, filesystem_roots=[watched])
    runtime.start()
    observer.start()

    node = repo.get_node(f"file:{file_path}")

    assert node is not None
    assert node.attributes["path"] == str(file_path)


def test_observer_roots_resolve_from_environment_and_settings(tmp_path, monkeypatch) -> None:
    env_root = tmp_path / "env-root"
    settings_root = tmp_path / "settings-root"
    monkeypatch.setenv("ACC_OBSERVER_ROOTS", str(env_root))

    roots = _observer_roots_from_settings(
        SimpleNamespace(vault_path=str(settings_root), obsidian_vault_path="")
    )

    assert roots == [env_root, settings_root]


def test_single_goal_scheduler_runs_goal_to_completion() -> None:
    bus = EventBus()
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(
            name="create_task",
            description="Create task",
            handler=lambda _args: ToolResult(success=True, output="ok"),
        )
    )
    ToolExecutorService(bus, registry).start()
    ExecutionOrchestratorService(bus).start()
    scheduler = SingleGoalScheduler(bus, GoalRepository(_conn()))
    scheduler.start()

    def complete_plan(event: Event) -> None:
        bus.publish(
            PLAN_GENERATED,
            {
                "request_id": event.payload["request_id"],
                "goal_id": event.payload["goal_id"],
                "plan": {
                    "goal": event.payload["goal"],
                    "steps": [
                        {
                            "step_id": "step-1",
                            "capability": "create_task",
                            "args": {"title": "Organize Downloads"},
                            "require_approval": False,
                        }
                    ],
                },
                "correlation": event.payload["correlation"],
            },
            source="test",
        )

    completed_runs: list[dict] = []
    completed_goals: list[dict] = []
    bus.subscribe(PLAN_REQUEST, complete_plan)
    bus.subscribe(EXECUTION_RUN_COMPLETE, lambda e: completed_runs.append(dict(e.payload)))
    bus.subscribe(GOAL_COMPLETED, lambda e: completed_goals.append(dict(e.payload)))

    bus.publish(
        GOAL_SUBMIT_REQUEST,
        {"goal_id": "goal-1", "goal": "Organize Downloads", "priority": "high"},
        source="test",
    )

    assert completed_runs
    assert completed_goals[0]["goal_id"] == "goal-1"


def test_scheduler_ignores_unrelated_execution_events() -> None:
    bus = EventBus()
    scheduler = SingleGoalScheduler(bus, GoalRepository(_conn()))
    scheduler.start()

    def complete_plan(event: Event) -> None:
        bus.publish(
            PLAN_GENERATED,
            {
                "request_id": event.payload["request_id"],
                "goal_id": event.payload["goal_id"],
                "plan": {
                    "goal": event.payload["goal"],
                    "steps": [
                        {
                            "step_id": "step-1",
                            "capability": "create_task",
                            "args": {},
                            "require_approval": False,
                        }
                    ],
                },
                "correlation": event.payload["correlation"],
            },
            source="test",
        )

    completed_goals: list[dict] = []
    failed_goals: list[dict] = []
    bus.subscribe(PLAN_REQUEST, complete_plan)
    bus.subscribe(GOAL_COMPLETED, lambda e: completed_goals.append(dict(e.payload)))
    bus.subscribe(GOAL_FAILED, lambda e: failed_goals.append(dict(e.payload)))

    bus.publish(
        GOAL_SUBMIT_REQUEST,
        {"goal_id": "goal-1", "goal": "Organize Downloads"},
        source="test",
    )
    bus.publish(
        EXECUTION_RUN_COMPLETE,
        {
            "run_id": "unrelated-run",
            "request_id": "other-request",
            "correlation": {"correlation_id": "other", "goal_id": "other-goal"},
        },
        source="test",
    )
    bus.publish(
        EXECUTION_RUN_FAILED,
        {
            "run_id": "unrelated-run",
            "request_id": "other-request",
            "error": "boom",
            "correlation": {"correlation_id": "other", "goal_id": "other-goal"},
        },
        source="test",
    )

    assert not completed_goals
    assert not failed_goals


def test_scheduler_cancel_queued_goal_does_not_resume_paused_active_goal() -> None:
    bus = EventBus()
    scheduler = SingleGoalScheduler(bus, GoalRepository(_conn()))
    scheduler.start()
    correlation = CorrelationContext.new(goal_id="goal-1")

    scheduler.submit_goal(
        Goal(
            id="goal-1",
            title="Active",
            correlation=correlation,
        )
    )
    scheduler.submit_goal(
        Goal(
            id="goal-2",
            title="Queued",
            correlation=CorrelationContext.new(goal_id="goal-2"),
        )
    )
    scheduler.pause_goal("goal-1", correlation)
    scheduler.cancel_goal("goal-2", CorrelationContext.new(goal_id="goal-2"))

    assert scheduler.get_next_task(correlation) is None


def test_kernel_recovers_and_rejects_invalid_transition() -> None:
    bus = EventBus()
    repo = SQLiteWorldModelRepository(_conn())
    kernel = BrainKernelService(bus, WorldModel(repo))
    transitions: list[dict] = []
    rejected: list[dict] = []
    bus.subscribe(KERNEL_STATE_CHANGED, lambda e: transitions.append(dict(e.payload)))
    bus.subscribe(KERNEL_TRANSITION_REJECTED, lambda e: rejected.append(dict(e.payload)))

    kernel.start()
    bus.publish(
        PLAN_GENERATED,
        {"request_id": "req-1", "plan": {"goal": "x", "steps": []}},
        source="test",
    )

    assert transitions[-1]["to"] == KernelState.IDLE.value
    assert rejected[-1]["from"] == KernelState.IDLE.value
    assert rejected[-1]["to"] == KernelState.EXECUTING.value
