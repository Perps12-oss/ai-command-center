"""State-authority migration coverage: no legacy routed command topic."""

from __future__ import annotations

import sqlite3
from typing import Any

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_AUTHORITY_DECISION,
    GOAL_SUBMIT_REQUEST,
    RUNTIME_ACTION_REQUEST,
    STATE_CONTEXT_BUILT,
    TOOL_INVOKE,
    UI_COMMAND,
    UI_NAVIGATE,
)
from ai_command_center.core.world_model.world_model import WorldModel, mutation_for_node
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.world_model import MutationType, Node
from ai_command_center.orchestration.state_capability_tools import bind_state_capability_tools
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.repositories.world_model_repository import SQLiteWorldModelRepository
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
from ai_command_center.services.orchestration_service import OrchestrationService
from ai_command_center.services.state_authority_service import StateAuthorityService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry


class _NotesProvider:
    def __init__(self) -> None:
        self.created: list[str] = []

    def create_note(self, body: str) -> tuple[bool, str, str]:
        self.created.append(body)
        path = f"Inbox/Quick-{len(self.created)}.md"
        return True, f"created note {path}", path

    def search_notes(self, query: str) -> tuple[bool, str, list[dict[str, str]]]:
        return True, "found 1 notes", [{"title": "Result", "snippet": query}]


class _MemoryProvider:
    def __init__(self) -> None:
        self.stored: list[dict[str, Any]] = []

    def store_memory(
        self,
        body: str,
        *,
        workspace_id: str = "",
        entity_id: str = "",
    ) -> tuple[bool, str, dict[str, Any]]:
        item = {
            "id": f"mem-{len(self.stored) + 1}",
            "body": body,
            "workspace_id": workspace_id,
            "entity_id": entity_id,
        }
        self.stored.append(item)
        return True, "stored memory mem", item

    def query_memory(
        self,
        query: str,
        *,
        workspace_id: str = "",
        entity_id: str = "",
    ) -> tuple[bool, str, list[dict[str, Any]]]:
        return True, "found memory", [{"label": "mem", "content": query}]


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def _wire_runtime(bus: EventBus, *, with_state_authority: bool = False) -> dict[str, Any]:
    registry = ToolRegistry()
    notes = _NotesProvider()
    memory = _MemoryProvider()
    bind_state_capability_tools(registry, bus=bus, notes=notes, memory=memory)
    tool_executor = ToolExecutorService(bus, registry)
    tool_executor.start()

    scheduler = SingleGoalScheduler(bus, GoalRepository(_conn()))
    scheduler.start()
    orchestrator = ExecutionOrchestratorService(bus)
    orchestrator.start()
    orchestration = OrchestrationService(bus)
    orchestration.start()

    state_authority = None
    world_model = None
    if with_state_authority:
        world_model = WorldModel(SQLiteWorldModelRepository(_conn()))
        state_authority = StateAuthorityService(bus, world_model)
        state_authority.start()

    authority = ExecutionAuthorityService(bus, state_authority=state_authority)
    authority.start()
    return {
        "authority": authority,
        "state_authority": state_authority,
        "world_model": world_model,
        "notes": notes,
        "memory": memory,
        "registry": registry,
    }


def test_state_authority_projects_before_goal_submit() -> None:
    bus = EventBus()
    wired = _wire_runtime(bus, with_state_authority=True)
    world_model = wired["world_model"]
    assert isinstance(world_model, WorldModel)
    world_model.apply(
        mutation_for_node(
            mutation_id="mut-state-1",
            node=Node("note:roadmap", "note", {"title": "Roadmap"}),
            correlation=CorrelationContext.new(goal_id="seed"),
            mutation_type=MutationType.CREATE_NODE,
        )
    )

    order: list[str] = []
    contexts: list[dict[str, Any]] = []
    goals: list[dict[str, Any]] = []
    bus.subscribe(STATE_CONTEXT_BUILT, lambda e: order.append(e.topic) or contexts.append(dict(e.payload)))
    bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: order.append(e.topic) or goals.append(dict(e.payload)))

    bus.publish(UI_COMMAND, {"text": "go notes"}, source="tests")

    assert order[:2] == [STATE_CONTEXT_BUILT, GOAL_SUBMIT_REQUEST]
    assert contexts and contexts[0]["entities"][0]["id"] == "note:roadmap"
    assert goals and goals[0]["state_context"]["entities"][0]["id"] == "note:roadmap"


def test_note_and_remember_commands_submit_state_capability_goals() -> None:
    bus = EventBus()
    authority = ExecutionAuthorityService(bus)
    authority.start()
    goals: list[dict[str, Any]] = []
    bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: goals.append(dict(e.payload)))

    bus.publish(UI_COMMAND, {"text": "note: daily log", "workspace_id": "ws-1"}, source="tests")
    bus.publish(
        UI_COMMAND,
        {"text": "remember: color | blue", "workspace_id": "ws-1"},
        source="tests",
    )

    assert [g["plan"]["steps"][0]["capability"] for g in goals] == [
        "notes.create",
        "memory.store",
    ]
    assert all(g["authority_decision"]["kind"] == "actionable" for g in goals)


def test_reverse_trace_ui_command_to_tool_invoke_for_state_tools() -> None:
    bus = EventBus()
    _wire_runtime(bus)
    decisions: list[dict[str, Any]] = []
    goals: list[dict[str, Any]] = []
    invokes: list[dict[str, Any]] = []
    navigation: list[dict[str, Any]] = []
    bus.subscribe(EXECUTION_AUTHORITY_DECISION, lambda e: decisions.append(dict(e.payload)))
    bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: goals.append(dict(e.payload)))
    bus.subscribe(TOOL_INVOKE, lambda e: invokes.append(dict(e.payload)))
    bus.subscribe(UI_NAVIGATE, lambda e: navigation.append(dict(e.payload)))

    bus.publish(UI_COMMAND, {"text": "note: ship notes", "workspace_id": "ws-1"}, source="tests")
    bus.publish(
        UI_COMMAND,
        {"text": "remember: launch | checklist", "workspace_id": "ws-1"},
        source="tests",
    )
    bus.publish(UI_COMMAND, {"text": "go settings"}, source="tests")

    assert [d["capability"] for d in decisions] == ["notes.create", "memory.store", "navigate"]
    assert [g["plan"]["steps"][0]["capability"] for g in goals] == [
        "notes.create",
        "memory.store",
        "navigate",
    ]
    assert [i["tool"] for i in invokes] == ["notes.create", "memory.store", "navigate"]
    assert navigation == [{"view": "settings"}]


def test_orchestration_completion_requests_typed_note_and_memory_nodes() -> None:
    bus = EventBus()
    _wire_runtime(bus)
    actions: list[dict[str, Any]] = []
    bus.subscribe(RUNTIME_ACTION_REQUEST, lambda e: actions.append(dict(e.payload)))

    bus.publish(UI_COMMAND, {"text": "note: release notes", "workspace_id": "ws-1"}, source="tests")
    bus.publish(
        UI_COMMAND,
        {"text": "remember: release | publish checklist", "workspace_id": "ws-1"},
        source="tests",
    )

    nodes = [
        action["mutation"]["payload"]["node"]
        for action in actions
        if isinstance(action.get("mutation"), dict)
    ]
    assert any(node["type"] == "note" and node["id"].startswith("note:") for node in nodes)
    assert any(node["type"] == "memory" and node["id"].startswith("memory:") for node in nodes)
