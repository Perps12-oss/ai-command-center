"""Phase 12 — State Intelligence unit/integration coverage."""

from __future__ import annotations

import sqlite3
import unittest
from typing import Any

from ai_command_center.capabilities.registry import CapabilityRegistry
from ai_command_center.capabilities.selector import CapabilitySelector
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_AUTHORITY_DECISION,
    EXECUTION_RUN_REQUEST,
    EXECUTION_RUN_STARTED,
    GOAL_SUBMIT_REQUEST,
    PLAN_GENERATED,
    PLAN_REQUEST,
    RUNTIME_ACTION_REQUEST,
    STATE_CONTEXT_BUILT,
    UI_COMMAND,
)
from ai_command_center.core.world_model.world_model import WorldModel, mutation_for_node
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.execution_result_type import ExecutionResultType
from ai_command_center.domain.state_context import StateContext
from ai_command_center.domain.world_model import MutationType, Node
from ai_command_center.repositories.world_model_repository import SQLiteWorldModelRepository
from ai_command_center.core.state_intelligence.context_projection_service import ContextProjectionService
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.core.state_intelligence.execution_intent_registry import ExecutionIntentRegistry
from ai_command_center.core.state_intelligence.idempotency_service import IdempotencyService
from ai_command_center.services.planner_service import (
    PlannerService,
    build_deterministic_plan,
)
from ai_command_center.core.state_intelligence.projection_budget_manager import ProjectionBudgetManager
from ai_command_center.services.state_authority_service import StateAuthorityService
from ai_command_center.core.state_intelligence.state_delta_engine import StateDeltaEngine
from ai_command_center.core.state_intelligence.world_model_query_service import WorldModelQueryService
from ai_command_center.core.context_manager import ContextManager


def _wm() -> tuple[sqlite3.Connection, WorldModel]:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    repo = SQLiteWorldModelRepository(conn)
    return conn, WorldModel(repo)


class CapabilityRegistryTests(unittest.TestCase):
    def test_selector_never_empty_and_filters_domains(self) -> None:
        registry = CapabilityRegistry()
        selector = CapabilitySelector(registry)
        caps = selector.select(goal="prepare for tomorrow's meeting")
        ids = {c.id for c in caps}
        self.assertIn("llm.chat", ids)
        self.assertTrue(caps)
        # Calendar/goals hinted; calendar stubs are not planner_visible.
        eng = selector.select(goal="create a note about alpha")
        eng_ids = {c.id for c in eng}
        self.assertIn("notes.create", eng_ids)

    def test_deterministic_plan_uses_llm_fallback(self) -> None:
        specs = [
            {"name": "llm.chat", "requires_approval": False},
            {"name": "notes.search", "requires_approval": False},
        ]
        plan = build_deterministic_plan("prepare for the demo", specs)
        self.assertTrue(plan.steps)
        self.assertIn(plan.steps[0].capability, {"llm.chat", "goals.plan", "notes.search", "reasoning.plan"})


class IntentAndQueryTests(unittest.TestCase):
    def test_intent_registry_surfaces_in_flight(self) -> None:
        bus = EventBus()
        registry = ExecutionIntentRegistry(bus)
        registry.load()
        bus.publish(
            GOAL_SUBMIT_REQUEST,
            {"request_id": "r1", "text": "Create Project Alpha", "workspace_id": "ws"},
            source="tests",
        )
        bus.publish(
            EXECUTION_RUN_STARTED,
            {"request_id": "r1", "run_id": "r1"},
            source="tests",
        )
        active = registry.list_active(workspace_id="ws")
        self.assertEqual(1, len(active))
        match = registry.has_matching_intent("Create Project Alpha", workspace_id="ws")
        self.assertIsNotNone(match)
        registry.unload()

    def test_query_includes_intent_entities(self) -> None:
        conn, wm = _wm()
        try:
            bus = EventBus()
            intents = ExecutionIntentRegistry(bus)
            intents.load()
            bus.publish(
                EXECUTION_RUN_REQUEST,
                {"request_id": "run-9", "goal": "Create Project Alpha", "workspace_id": "ws"},
                source="tests",
            )
            query = WorldModelQueryService(bus, wm, intent_registry=intents)
            ctx = query.project_state(text="Create Project Alpha", workspace_id="ws")
            types = {e["type"] for e in ctx.entities}
            self.assertIn("execution_intent", types)
            intents.unload()
        finally:
            conn.close()


class ProjectionBudgetTests(unittest.TestCase):
    def test_budget_truncates_low_priority(self) -> None:
        mgr = ProjectionBudgetManager(max_tokens=80)
        lines = mgr.allocate_dict(
            {
                "goal": ["[goal] primary objective " + ("x" * 40)],
                "relationships": [f"[rel] edge-{i}" for i in range(40)],
                "memories": [f"[memory] m-{i}" for i in range(40)],
            }
        )
        joined = "\n".join(lines)
        # Relationships should be truncated first under tight budget.
        self.assertLess(joined.count("[rel]"), 40)
        self.assertTrue(any("[goal]" in line for line in lines))


class IdempotencyTests(unittest.TestCase):
    def test_no_op_when_entity_exists(self) -> None:
        conn, wm = _wm()
        try:
            bus = EventBus()
            corr = CorrelationContext.new(goal_id="seed")
            wm.apply(
                mutation_for_node(
                    mutation_id="mut-alpha",
                    node=Node(
                        id="project:alpha",
                        type="project",
                        attributes={"name": "Project Alpha", "status": "ACTIVE"},
                    ),
                    correlation=corr,
                    mutation_type=MutationType.CREATE_NODE,
                )
            )
            query = WorldModelQueryService(bus, wm)
            idem = IdempotencyService(bus, query_service=query)
            ctx = query.project_state(text="Create Project Alpha", workspace_id="")
            decision = idem.check(
                text="Create Project Alpha",
                capability="goals.create",
                state_context=ctx,
            )
            self.assertEqual("no_op", decision["action"])
            self.assertEqual(ExecutionResultType.NO_OP.value, decision["result_type"])
            plan = idem.maybe_no_op_plan(
                text="Create Project Alpha",
                capability="goals.create",
                state_context=ctx,
            )
            self.assertIsNotNone(plan)
            assert plan is not None
            self.assertEqual("system.noop", plan.steps[0].capability)
        finally:
            conn.close()


class StateDeltaTests(unittest.TestCase):
    def test_receipt_emits_typed_deltas(self) -> None:
        bus = EventBus()
        engine = StateDeltaEngine(bus)
        actions: list[dict] = []
        bus.subscribe(RUNTIME_ACTION_REQUEST, lambda e: actions.append(dict(e.payload)))
        count = engine.apply_receipt(
            {
                "success": True,
                "intent": "memory.store",
                "request_id": "req-1",
                "facts": {
                    "memory_id": "m1",
                    "label": "editor",
                    "content": "VS Code",
                },
            }
        )
        self.assertGreaterEqual(count, 1)
        self.assertTrue(actions)
        mut = actions[0]["mutation"]
        self.assertEqual(MutationType.CREATE_NODE.value, mut["type"])
        node = mut["payload"]["node"]
        self.assertEqual("memory", node["type"])
        self.assertIn("confidence", node["attributes"])
        self.assertIn("verified_at", node["attributes"])


class StateAuthorityIntegrationTests(unittest.TestCase):
    def test_authority_projects_before_decision(self) -> None:
        conn, wm = _wm()
        try:
            bus = EventBus()
            intents = ExecutionIntentRegistry(bus)
            intents.load()
            query = WorldModelQueryService(bus, wm, intent_registry=intents)
            projection = ContextProjectionService(bus, query)
            sa = StateAuthorityService(
                bus,
                wm,
                query_service=query,
                projection_service=projection,
            )
            sa.load()
            built: list[dict] = []
            bus.subscribe(STATE_CONTEXT_BUILT, lambda e: built.append(dict(e.payload)))
            ea = ExecutionAuthorityService(bus, state_authority=sa)
            ea.load()
            bus.publish(
                UI_COMMAND,
                {"text": "navigate home", "workspace_id": "ws-1"},
                source="tests",
            )
            self.assertTrue(built)
            decisions: list[dict] = []
            # Decision already published; re-run analyze path via second command.
            bus.subscribe(
                EXECUTION_AUTHORITY_DECISION,
                lambda e: decisions.append(dict(e.payload)),
            )
            bus.publish(
                UI_COMMAND,
                {"text": "remember my preferred editor is VS Code", "workspace_id": "ws-1"},
                source="tests",
            )
            self.assertTrue(decisions)
            self.assertEqual("memory.store", decisions[-1].get("capability"))
            ea.unload()
            sa.unload()
            intents.unload()
        finally:
            conn.close()

    def test_planner_receives_non_empty_catalog_for_prepare_goal(self) -> None:
        bus = EventBus()
        from ai_command_center.services.capability_prompt_catalog_service import (
            CapabilityPromptCatalogService,
        )
        from ai_command_center.tools.tool_registry import ToolRegistry
        from ai_command_center.orchestration.state_capability_tools import (
            bind_state_capability_tools,
        )

        registry = ToolRegistry()
        bind_state_capability_tools(registry, bus=bus)
        catalog = CapabilityPromptCatalogService(bus, tool_registry=registry)
        catalog.load()
        cm = ContextManager()
        selector = CapabilitySelector(CapabilityRegistry())
        planner = PlannerService(bus, context_manager=cm, capability_selector=selector)
        planner.load()
        plans: list[dict] = []
        bus.subscribe(PLAN_GENERATED, lambda e: plans.append(dict(e.payload)))
        bus.publish(
            PLAN_REQUEST,
            {
                "request_id": "p1",
                "goal": "prepare for tomorrow's meeting",
                "state_context": StateContext(
                    workspace_id="ws",
                    summary="active workspace",
                    query_text="prepare for tomorrow's meeting",
                ).to_dict(),
            },
            source="tests",
        )
        self.assertEqual(1, len(plans))
        steps = plans[0]["plan"]["steps"]
        self.assertTrue(steps)
        planner.unload()
        catalog.unload()


class ReconstructionTests(unittest.TestCase):
    def test_world_model_reconstruction_without_chat(self) -> None:
        """Delete conversations mentally: reconstruct context from WM alone."""
        conn, wm = _wm()
        try:
            corr = CorrelationContext.new(goal_id="seed")
            seeds = [
                Node(
                    id="workspace:eng",
                    type="workspace",
                    attributes={"name": "Engineering", "status": "ACTIVE", "confidence": 1.0},
                ),
                Node(
                    id="goal:migration",
                    type="goal",
                    attributes={"title": "State Authority Migration", "status": "active"},
                ),
                Node(
                    id="note:plan",
                    type="note",
                    attributes={"title": "Migration Plan", "path": "plan.md"},
                ),
                Node(
                    id="memory:editor",
                    type="memory",
                    attributes={"label": "editor", "content": "VS Code"},
                ),
                Node(
                    id="task:audit",
                    type="task",
                    attributes={"title": "Runtime Audit", "status": "open"},
                ),
                Node(
                    id="application:chrome",
                    type="application",
                    attributes={"name": "chrome", "status": "OPEN", "verified_at": "t0"},
                ),
            ]
            for index, node in enumerate(seeds):
                wm.apply(
                    mutation_for_node(
                        mutation_id=f"mut-recon-{index}",
                        node=node,
                        correlation=corr,
                        mutation_type=MutationType.CREATE_NODE,
                    )
                )
            bus = EventBus()
            query = WorldModelQueryService(bus, wm)
            ctx = query.project_state(text="", workspace_id="eng")
            types = {e["type"] for e in ctx.entities}
            for required in ("workspace", "goal", "note", "memory", "task", "application"):
                self.assertIn(required, types)
            # No chat history involved — summary still non-empty from WM.
            self.assertTrue(ctx.summary or ctx.entities)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
