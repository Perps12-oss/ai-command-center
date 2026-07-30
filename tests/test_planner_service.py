"""PlannerService — Phase C bus round-trip tests."""

from __future__ import annotations

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CAPABILITY_CATALOG_REQUEST,
    PLAN_FAILED,
    PLAN_GENERATED,
    PLAN_REQUEST,
    WORKSPACE_CONTEXT_REQUEST,
    WORKSPACE_CONTEXT_RESULT,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.domain.planner_plan import ExecutionPlan
from ai_command_center.services.capability_prompt_catalog_service import (
    CapabilityPromptCatalogService,
)
from ai_command_center.services.planner_service import (
    PlannerService,
    build_deterministic_plan,
)
from ai_command_center.tools.tool_registry import ToolRegistry


def _noop_tool(_args: object) -> ToolResult:
    return ToolResult(success=True, output="ok")


def test_build_deterministic_plan_create_note() -> None:
    specs = [
        {
            "name": "create_note",
            "description": "Creates a note",
            "requires_approval": True,
            "risk": "medium",
            "parameters": {},
        }
    ]
    plan = build_deterministic_plan("Create a new note called Groceries", specs)
    assert len(plan.steps) == 1
    assert plan.steps[0].capability == "create_note"
    assert plan.steps[0].require_approval is True
    assert "Groceries" in str(plan.steps[0].args.get("title", ""))


def test_planner_service_bus_round_trip() -> None:
    bus = EventBus()
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="create_note", description="Creates a note", handler=_noop_tool)
    )

    catalog = CapabilityPromptCatalogService(bus, tool_registry=registry)
    planner = PlannerService(bus, context_manager=ContextManager())
    catalog.start()
    planner.start()

    bus.subscribe(
        WORKSPACE_CONTEXT_REQUEST,
        lambda e: bus.publish(
            WORKSPACE_CONTEXT_RESULT,
            {
                "request_id": e.payload["request_id"],
                "snippets": ["[WORKSPACE] Home (id=ws-1)"],
            },
            source="test",
        ),
    )

    generated: list[dict] = []
    bus.subscribe(PLAN_GENERATED, lambda e: generated.append(dict(e.payload)))

    app_state = AppStateStore(bus)

    bus.publish(
        PLAN_REQUEST,
        {
            "request_id": "plan-1",
            "goal": "Add a new note for milk",
            "workspace_id": "ws-1",
            "entity_types": ["note"],
        },
        source="test",
    )

    assert generated
    payload = generated[0]
    assert payload["request_id"] == "plan-1"
    assert payload["planner_mode"] == "deterministic"
    assert "state_context" in payload
    plan = ExecutionPlan.from_dict(payload["plan"])
    assert plan.steps
    assert plan.steps[0].capability == "create_note"

    assert app_state.snapshot.planner_last_plan.get("goal") == "Add a new note for milk"


def test_planner_requires_state_projection_via_state_authority() -> None:
    """Contract R2: PLAN_REQUEST without state_context queries State Authority."""
    from ai_command_center.core.world_model.world_model import WorldModel, mutation_for_node
    from ai_command_center.domain.correlation import CorrelationContext
    from ai_command_center.domain.world_model import MutationType, Node
    from ai_command_center.repositories.world_model_repository import (
        SQLiteWorldModelRepository,
    )
    from ai_command_center.services.state_authority_service import StateAuthorityService
    import sqlite3

    bus = EventBus()
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    wm = WorldModel(SQLiteWorldModelRepository(conn))
    wm.apply(
        mutation_for_node(
            mutation_id="mut-1",
            node=Node("note:milk", "note", {"title": "Milk list"}),
            correlation=CorrelationContext.new(goal_id="seed"),
            mutation_type=MutationType.CREATE_NODE,
        )
    )
    sa = StateAuthorityService(bus, wm)
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="create_note", description="Creates a note", handler=_noop_tool)
    )
    catalog = CapabilityPromptCatalogService(bus, tool_registry=registry)
    planner = PlannerService(
        bus, context_manager=ContextManager(), state_authority=sa
    )
    sa.start()
    catalog.start()
    planner.start()

    generated: list[dict] = []
    bus.subscribe(PLAN_GENERATED, lambda e: generated.append(dict(e.payload)))

    bus.publish(
        PLAN_REQUEST,
        {
            "request_id": "plan-state",
            "goal": "Add a new note for milk",
            "workspace_id": "ws-1",
            "entity_types": ["note"],
        },
        source="test",
    )

    assert generated
    ctx = generated[0]["state_context"]
    assert any(e.get("id") == "note:milk" for e in ctx.get("entities", []))
    assert "state_aware" in generated[0]["planner_mode"]


def test_planner_service_fails_without_goal() -> None:
    bus = EventBus()
    planner = PlannerService(bus, context_manager=ContextManager())
    planner.start()

    failures: list[dict] = []
    bus.subscribe(PLAN_FAILED, lambda e: failures.append(dict(e.payload)))

    bus.publish(PLAN_REQUEST, {"request_id": "plan-empty"}, source="test")

    assert failures
    assert failures[0]["error"] == "goal is required"


def test_planner_fetches_capability_catalog_via_bus() -> None:
    bus = EventBus()
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="search_files", description="Search files", handler=_noop_tool)
    )
    catalog = CapabilityPromptCatalogService(bus, tool_registry=registry)
    planner = PlannerService(bus, context_manager=ContextManager())
    catalog.start()
    planner.start()

    catalog_requests: list[dict] = []
    bus.subscribe(
        CAPABILITY_CATALOG_REQUEST,
        lambda e: catalog_requests.append(dict(e.payload)),
    )

    generated: list[dict] = []
    bus.subscribe(PLAN_GENERATED, lambda e: generated.append(dict(e.payload)))

    bus.publish(
        PLAN_REQUEST,
        {"request_id": "plan-2", "goal": "find project docs", "entity_types": []},
        source="test",
    )

    assert catalog_requests
    assert catalog_requests[0]["request_id"] == "plan-2"
    assert generated
    assert generated[0]["plan"]["steps"][0]["capability"] == "search_files"
