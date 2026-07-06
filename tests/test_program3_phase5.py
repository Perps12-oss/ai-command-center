"""Program 3 Phase 5 — workspace-scoped tool execution and timeline."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION
from ai_command_center.core.entity.entity_bus_handlers import register_entity_bus_handlers
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_SHELL
from ai_command_center.core.events.topics import (
    COMMAND_ROUTED,
    TIMELINE_RECORD_REQUEST,
    TOOL_INVOKE,
    TOOL_RESULT,
    WORKSPACE_ACTIVE,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.services.shell_tool_service import ShellToolService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry


class Phase5ShellToolScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        self.invokes: list[dict] = []
        self.bus.subscribe(TOOL_INVOKE, lambda e: self.invokes.append(dict(e.payload)))
        self.shell = ShellToolService(self.bus)
        self.shell.load()

    def tearDown(self) -> None:
        self.shell.unload()

    def test_shell_invoke_includes_workspace_context_from_active_workspace(self) -> None:
        self.bus.publish(
            WORKSPACE_ACTIVE,
            {"workspace_id": "ws-active", "title": "Active"},
            source="tests",
        )
        self.bus.publish(
            COMMAND_ROUTED,
            {
                "intent": INTENT_SHELL,
                "args": {"command": "echo scoped"},
            },
            source="command_router",
        )
        self.assertEqual(1, len(self.invokes))
        ctx = self.invokes[0].get("workspace_context")
        self.assertIsInstance(ctx, dict)
        self.assertEqual("ws-active", ctx.get("workspace_id"))

    def test_shell_invoke_merges_command_routed_entity_scope(self) -> None:
        self.bus.publish(
            WORKSPACE_ACTIVE,
            {"workspace_id": "ws-active", "title": "Active"},
            source="tests",
        )
        self.bus.publish(
            COMMAND_ROUTED,
            {
                "intent": INTENT_SHELL,
                "args": {"command": "echo entity"},
                "workspace_id": "ws-routed",
                "workspace_entity_id": "card-9",
                "workspace_entity_type": "card",
            },
            source="command_router",
        )
        ctx = self.invokes[0]["workspace_context"]
        self.assertEqual("ws-routed", ctx.get("workspace_id"))
        self.assertEqual("card-9", ctx.get("entity_id"))
        self.assertEqual("card", ctx.get("entity_type"))

    def test_shell_invoke_always_carries_workspace_context_key(self) -> None:
        self.bus.publish(
            COMMAND_ROUTED,
            {
                "intent": INTENT_SHELL,
                "args": {"command": "echo bare"},
            },
            source="command_router",
        )
        self.assertIn("workspace_context", self.invokes[0])
        self.assertIsInstance(self.invokes[0]["workspace_context"], dict)


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
