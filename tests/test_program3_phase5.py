"""Program 3 Phase 5 — workspace-scoped tool execution and timeline."""

from __future__ import annotations

import sqlite3
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION
from ai_command_center.core.entity.entity_bus_handlers import register_entity_bus_handlers
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    COMMAND_DEFERRED,
    GOAL_SUBMIT_REQUEST,
    TIMELINE_RECORD_REQUEST,
    TOOL_INVOKE,
    TOOL_RESULT,
    UI_COMMAND,
    WORKSPACE_ACTIVE,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry


class Phase5ShellToolScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        self.invokes: list[dict] = []
        self.bus.subscribe(TOOL_INVOKE, lambda e: self.invokes.append(dict(e.payload)))
        self.goals: list[dict] = []
        self.deferred: list[dict] = []
        self.bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: self.goals.append(dict(e.payload)))
        self.bus.subscribe(COMMAND_DEFERRED, lambda e: self.deferred.append(dict(e.payload)))
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.scheduler = SingleGoalScheduler(self.bus, GoalRepository(self.conn))
        self.orchestrator = ExecutionOrchestratorService(self.bus)
        self.authority = ExecutionAuthorityService(self.bus)
        self.scheduler.load()
        self.orchestrator.load()
        self.authority.load()

    def tearDown(self) -> None:
        self.authority.unload()
        self.orchestrator.unload()
        self.scheduler.unload()
        self.conn.close()

    def test_shell_invoke_includes_workspace_context_from_active_workspace(self) -> None:
        self.bus.publish(
            WORKSPACE_ACTIVE,
            {"workspace_id": "ws-active", "title": "Active"},
            source="tests",
        )
        self.bus.publish(
            UI_COMMAND,
            {"text": "> echo scoped"},
            source="tests",
        )
        self.assertEqual(1, len(self.goals))
        self.assertEqual("shell", self.goals[0]["plan"]["steps"][0]["capability"])
        self.assertEqual(1, len(self.invokes))
        ctx = self.invokes[0].get("workspace_context")
        self.assertIsInstance(ctx, dict)
        self.assertEqual("ws-active", ctx.get("workspace_id"))
        self.assertEqual("echo scoped", self.invokes[0]["args"]["command"])

    def test_shell_invoke_merges_ui_command_entity_scope(self) -> None:
        self.bus.publish(
            WORKSPACE_ACTIVE,
            {"workspace_id": "ws-active", "title": "Active"},
            source="tests",
        )
        self.bus.publish(
            UI_COMMAND,
            {
                "text": "> echo entity",
                "workspace_id": "ws-routed",
                "workspace_entity_id": "card-9",
                "workspace_entity_type": "card",
            },
            source="tests",
        )
        ctx = self.invokes[0]["workspace_context"]
        self.assertEqual("ws-routed", ctx.get("workspace_id"))
        self.assertEqual("card-9", ctx.get("entity_id"))
        self.assertEqual("card", ctx.get("entity_type"))

    def test_shell_without_workspace_is_deferred_not_invoked(self) -> None:
        self.bus.publish(
            UI_COMMAND,
            {"text": "> echo bare"},
            source="tests",
        )
        self.assertEqual([], self.invokes)
        self.assertEqual(1, len(self.deferred))
        self.assertEqual("shell", self.deferred[0].get("intent"))


class Phase5ToolTimelineTests(unittest.TestCase):
    def test_tool_result_records_workspace_timeline_when_scope_present(self) -> None:
        bus = EventBus()
        timeline = MagicMock()
        register_entity_bus_handlers(
            bus,
            entity_service=MagicMock(),
            relationship_service=MagicMock(),
            workspace_service=MagicMock(),
            timeline_service=timeline,
            action_registry=MagicMock(),
        )
        workspace_id = str(uuid4())
        entity_id = str(uuid4())
        results: list[dict] = []
        bus.subscribe(TOOL_RESULT, lambda e: results.append(dict(e.payload)))

        registry = ToolRegistry()
        registry.register_tool(
            ToolSpec(
                name="demo",
                description="demo tool",
                handler=lambda _args: ToolResult(success=True, output="ok"),
            )
        )
        executor = ToolExecutorService(bus, registry)
        executor.load()
        try:
            bus.publish(
                TOOL_INVOKE,
                {
                    "contract_version": TOOL_CONTRACT_VERSION,
                    "invoke_id": "invoke-1",
                    "tool": "demo",
                    "args": {},
                    "actor_type": "user",
                    "workspace_context": {
                        "workspace_id": workspace_id,
                        "entity_id": entity_id,
                        "entity_type": "card",
                    },
                },
                source="tests",
            )
        finally:
            executor.unload()

        self.assertEqual(1, len(results))
        self.assertEqual(workspace_id, results[0]["workspace_context"]["workspace_id"])
        timeline.record.assert_called_once()
        call_kwargs = timeline.record.call_args.kwargs
        self.assertEqual("tool.completed", call_kwargs["event_type"])
        self.assertEqual(entity_id, str(call_kwargs["entity_id"]))
        self.assertEqual("card", call_kwargs["entity_type"])
        self.assertEqual(workspace_id, call_kwargs["payload"]["workspace_id"])

    def test_tool_timeline_skipped_without_workspace_id(self) -> None:
        bus = EventBus()
        timeline_requests: list[dict] = []
        bus.subscribe(
            TIMELINE_RECORD_REQUEST,
            lambda e: timeline_requests.append(dict(e.payload)),
        )
        registry = ToolRegistry()
        registry.register_tool(
            ToolSpec(
                name="demo",
                description="demo tool",
                handler=lambda _args: ToolResult(success=True, output="ok"),
            )
        )
        executor = ToolExecutorService(bus, registry)
        executor.load()
        try:
            bus.publish(
                TOOL_INVOKE,
                {
                    "contract_version": TOOL_CONTRACT_VERSION,
                    "invoke_id": "invoke-2",
                    "tool": "demo",
                    "args": {},
                    "actor_type": "user",
                    "workspace_context": {},
                },
                source="tests",
            )
        finally:
            executor.unload()
        self.assertEqual([], timeline_requests)


if __name__ == "__main__":
    unittest.main()
