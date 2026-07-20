"""Governance surfaces — UI mutations must enter Execution Authority."""

from __future__ import annotations

import ast
import inspect
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.command_classify import classify_command
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_MEMORY_REMEMBER, INTENT_NAVIGATE
from ai_command_center.core.events.topics import MEMORY_REMEMBER, UI_COMMAND
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.ui.controller import UIController

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "ai_command_center" / "ui"


class GovernanceSurfaceTests(unittest.TestCase):
    def test_publish_memory_remember_emits_ui_command_not_memory_remember(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        commands: list[dict] = []
        remembers: list[dict] = []
        bus.subscribe(UI_COMMAND, lambda e: commands.append(dict(e.payload)))
        bus.subscribe(MEMORY_REMEMBER, lambda e: remembers.append(dict(e.payload)))
        controller = UIController(bus, store, MagicMock())

        controller.publish_memory_remember("editor", "VS Code", workspace_scope={"workspace_id": "ws-1"})

        self.assertEqual(1, len(commands))
        self.assertEqual(0, len(remembers))
        self.assertIn("remember:", commands[0]["text"])
        self.assertEqual("ws-1", commands[0].get("workspace_id"))

    def test_ui_controller_memory_source_enters_authority_decision(self) -> None:
        bus = EventBus()
        decisions: list[dict] = []
        from ai_command_center.core.events.topics import EXECUTION_AUTHORITY_DECISION

        bus.subscribe(EXECUTION_AUTHORITY_DECISION, lambda e: decisions.append(dict(e.payload)))
        authority = ExecutionAuthorityService(bus)
        authority.load()
        store = AppStateStore(bus)
        controller = UIController(bus, store, MagicMock())
        try:
            controller.publish_memory_remember(
                "color",
                "blue",
                workspace_scope={"workspace_id": "ws-gov"},
            )
        finally:
            authority.unload()
        self.assertEqual(1, len(decisions))
        self.assertEqual("memory.store", decisions[0].get("capability"))

    def test_ui_publish_memory_remember_source_code_uses_ui_command(self) -> None:
        src = inspect.getsource(UIController.publish_memory_remember)
        self.assertIn("UI_COMMAND", src)
        self.assertIn("self._bus.publish(UI_COMMAND", src)
        self.assertNotIn("publish(\n            MEMORY_REMEMBER", src)
        self.assertNotIn("publish(MEMORY_REMEMBER", src)

    def test_ui_layer_has_no_direct_memory_repository_writes(self) -> None:
        violations: list[str] = []
        for path in UI_ROOT.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if "memory_repository" in node.module or node.module.endswith(".db.memory_repository"):
                        violations.append(str(path.relative_to(PROJECT_ROOT)))
        self.assertEqual([], violations)

    def test_nl_remember_and_navigate_classify(self) -> None:
        intent, args = classify_command("remember my preferred editor is VS Code")
        self.assertEqual(INTENT_MEMORY_REMEMBER, intent)
        self.assertIn("preferred editor", args.get("body", "").lower())

        intent, args = classify_command("navigate dashboard")
        self.assertEqual(INTENT_NAVIGATE, intent)
        self.assertEqual("home", args.get("view"))

        intent, args = classify_command("go settings")
        self.assertEqual(INTENT_NAVIGATE, intent)
        self.assertEqual("settings", args.get("view"))


if __name__ == "__main__":
    unittest.main()
