"""Brain World Model repository, runtime, scheduler, observer, and kernel tests."""

from __future__ import annotations

import sqlite3

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_RUN_COMPLETE,
    GOAL_COMPLETED,
    GOAL_SUBMIT_REQUEST,
    KERNEL_STATE_CHANGED,
    KERNEL_TRANSITION_REJECTED,
    PLAN_GENERATED,
    PLAN_REQUEST,
    RUNTIME_ACTION_COMPLETED,
    RUNTIME_ACTION_DENIED,
    RUNTIME_ACTION_REQUEST,
    RUNTIME_APPROVAL_DECIDED,
    RUNTIME_APPROVAL_REQUESTED,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.core.world_model.world_model import WorldModel
from ai_command_center.domain.correlation import CorrelationContext
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
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_world_model_repository_replays_last_five_mutations() -> None:
    repo = SQLiteWorldModelRepository(_conn())
    correlation = CorrelationContext.new(goal_id="goal-1")

    for index in range(7):
        node = Node(id=f"node-{index}", type="resource", attributes={"index": index})
        repo.save_node(node, correlation.with_action(f"action-{index}"))

    replay = repo.replay_mutations(limit=5)

    assert [item.payload["node"]["id"] for item in replay] == [
        "node-2",
        "node-3",
        "node-4",
        "node-5",
        "node-6",
    ]
    assert replay[-1].correlation.goal_id == "goal-1"


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
