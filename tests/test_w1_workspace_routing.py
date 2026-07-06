"""Program 3 W1 — workspace entry routing tests."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT, INTENT_NAVIGATE
from ai_command_center.core.events.topics import (
    COMMAND_ROUTED,
    LLM_REQUEST,
    MEMORY_REMEMBER,
    MODEL_RESOLVE_REQUEST,
    MODEL_RESOLVE_RESULT,
    SESSION_HISTORY_REQUEST,
    SESSION_HISTORY_RESULT,
    UI_COMMAND,
    UI_OPEN_CHAT,
    WORKSPACE_ACTIVE,
)
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.command_router_service import CommandRouterService
from ai_command_center.ui.controller import UIController


class W1CommandRouterScopeTests(unittest.TestCase):
    def test_navigate_intent_inherits_workspace_scope_on_payload(self) -> None:
        bus = EventBus()
        router = CommandRouterService(bus)
        router.load()
        routed: list[dict] = []

        def capture(event) -> None:
            if event.topic == COMMAND_ROUTED and event.source == "command_router":
                routed.append(dict(event.payload))

        bus.subscribe(COMMAND_ROUTED, capture)
        bus.publish(
            UI_COMMAND,
            {
                "text": "go notes",
                "workspace_entity_id": "card-1",
                "workspace_entity_type": "card",
                "workspace_entity_title": "Roadmap",
            },
            source="tests",
        )
        router.unload()
        self.assertEqual(1, len(routed))
        payload = routed[0]
        self.assertEqual(INTENT_NAVIGATE, payload.get("intent"))
        self.assertEqual("card-1", payload.get("workspace_entity_id"))
        self.assertEqual("card", payload.get("workspace_entity_type"))
        self.assertEqual("Roadmap", payload.get("workspace_entity_title"))
        args = payload.get("args") or {}
        self.assertEqual("card-1", args.get("workspace_entity_id"))

    def test_chat_intent_scope_on_payload_and_args(self) -> None:
        bus = EventBus()
        router = CommandRouterService(bus)
        router.load()
        routed: list[dict] = []

        def capture(event) -> None:
            if event.topic == COMMAND_ROUTED and event.source == "command_router":
                routed.append(dict(event.payload))

        bus.subscribe(COMMAND_ROUTED, capture)
        bus.publish(
            UI_COMMAND,
            {
                "text": "Summarize",
                "workspace_entity_id": "res-2",
                "workspace_entity_type": "resource",
                "workspace_entity_title": "Docs",
                "workspace_entity_description": "API guide",
            },
            source="tests",
        )
        router.unload()
        payload = routed[0]
        self.assertEqual(INTENT_CHAT, payload.get("intent"))
        self.assertEqual("res-2", payload.get("workspace_entity_id"))
        args = payload.get("args") or {}
        self.assertEqual("API guide", args.get("workspace_entity_description"))


class W1ChatHandlerEntityTests(unittest.TestCase):
    def test_chat_handler_reads_workspace_entity_from_routed_payload(self) -> None:
        bus = EventBus()
        llm_payloads: list[dict] = []

        def on_session_history(event) -> None:
            if event.topic == SESSION_HISTORY_REQUEST:
                bus.publish(
                    SESSION_HISTORY_RESULT,
                    {"request_id": event.payload["request_id"], "history": []},
                    source="tests",
                )

        def on_model_resolve(event) -> None:
            if event.topic == MODEL_RESOLVE_REQUEST:
                bus.publish(
                    MODEL_RESOLVE_RESULT,
                    {
                        "request_id": event.payload["request_id"],
                        "model": "llama3.2:3b",
                        "provider": "ollama",
                    },
                    source="tests",
                )

        bus.subscribe(SESSION_HISTORY_REQUEST, on_session_history)
        bus.subscribe(MODEL_RESOLVE_REQUEST, on_model_resolve)
        bus.subscribe(
            LLM_REQUEST,
            lambda event: llm_payloads.append(dict(event.payload)),
        )

        handler = ChatHandlerService(bus, ContextManager(max_context_tokens=4096))
        handler.load()
        bus.publish(
            COMMAND_ROUTED,
            {
                "intent": INTENT_CHAT,
                "args": {"prompt": "What is this card about?"},
                "workspace_entity_id": "card-42",
                "workspace_entity_type": "card",
                "workspace_entity_title": "Sprint Plan",
                "workspace_entity_description": "Q3 goals",
            },
            source="command_router",
        )
        handler.unload()
        self.assertEqual(1, len(llm_payloads))
        bundle = llm_payloads[0].get("bundle")
        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertIn("Sprint Plan", bundle.prompt)
        self.assertIn("card-42", bundle.prompt)
        self.assertIn("Q3 goals", bundle.prompt)


class W1UIControllerScopeTests(unittest.TestCase):
    def test_active_chat_workspace_entity_from_appstate(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        on_state = MagicMock()
        controller = UIController(bus, store, on_state)

        bus.publish(
            UI_OPEN_CHAT,
            {
                "entity_id": "card-7",
                "entity_type": "card",
                "title": "Design",
                "description": "UI notes",
                "url": "https://example.com/design",
            },
            source="tests",
        )
        entity = controller.active_chat_workspace_entity()
        self.assertIsNotNone(entity)
        assert entity is not None
        self.assertEqual("card-7", entity["entity_id"])
        self.assertEqual("card", entity["entity_type"])
        self.assertEqual("Design", entity["entity_title"])
        self.assertEqual("UI notes", entity["description"])
        self.assertEqual("https://example.com/design", entity["url"])

        bus.publish(UI_OPEN_CHAT, {"entity_id": ""}, source="tests")
        self.assertIsNone(controller.active_chat_workspace_entity())

    def test_publish_command_includes_workspace_entity_fields(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        captured: list[dict] = []

        def capture(event) -> None:
            if event.topic == UI_COMMAND:
                captured.append(dict(event.payload))

        bus.subscribe(UI_COMMAND, capture)
        controller = UIController(bus, store, MagicMock())
        controller.publish_command(
            "hello",
            workspace_entity={
                "entity_id": "card-3",
                "entity_type": "card",
                "entity_title": "Alpha",
                "description": "First card",
            },
        )
        self.assertEqual(1, len(captured))
        payload = captured[0]
        self.assertEqual("card-3", payload.get("workspace_entity_id"))
        self.assertEqual("card", payload.get("workspace_entity_type"))
        self.assertEqual("Alpha", payload.get("workspace_entity_title"))
        self.assertEqual("First card", payload.get("workspace_entity_description"))

    def test_memory_remember_inherits_active_workspace_scope(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        captured: list[dict] = []
        bus.subscribe(MEMORY_REMEMBER, lambda e: captured.append(dict(e.payload)))
        controller = UIController(bus, store, MagicMock())

        bus.publish(
            UI_OPEN_CHAT,
            {"entity_id": "ws-7", "entity_type": "workspace", "title": "Workspace 7"},
            source="tests",
        )
        controller.publish_memory_remember(
            "decision",
            "Use workspace scope",
            workspace_scope=controller.current_workspace_scope(),
        )

        self.assertEqual(1, len(captured))
        self.assertEqual("ws-7", captured[0].get("workspace_id"))
        self.assertEqual("ws-7", captured[0].get("workspace_entity_id"))

    def test_active_workspace_scope_without_open_chat_entity(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        captured: list[dict] = []
        bus.subscribe(UI_COMMAND, lambda e: captured.append(dict(e.payload)))
        controller = UIController(bus, store, MagicMock())

        bus.publish(
            WORKSPACE_ACTIVE,
            {"workspace_id": "ws-active", "title": "Active WS"},
            source="tests",
        )
        controller.publish_command("hello")

        self.assertEqual(1, len(captured))
        self.assertEqual("ws-active", captured[0].get("workspace_id"))


if __name__ == "__main__":
    unittest.main()
