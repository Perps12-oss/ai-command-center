"""Program 3 Phase 6b — workspace-aware orchestration and routing scope."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    CAPABILITY_CLASSIFIED,
    CAPABILITY_DISPATCH,
    COMMAND_ROUTED,
    MODEL_RESOLVE_REQUEST,
    MODEL_RESOLVE_RESULT,
    MODEL_SELECTED,
    ORCHESTRATION_INTENT_CLASSIFIED,
    SETTINGS_SNAPSHOT,
    WORKSPACE_ACTIVE,
)
from ai_command_center.core.entity.entity import ENTITY_TYPE_CARD
from ai_command_center.services.model_router_service import ModelRouterService
from ai_command_center.services.orchestration_service import OrchestrationService
from ai_command_center.services.runtime_capability_router_service import (
    RuntimeCapabilityRouterService,
)


class Phase6bOrchestrationScopeTests(unittest.TestCase):
    def test_orchestration_classified_includes_workspace_scope(self) -> None:
        bus = EventBus()
        service = OrchestrationService(bus)
        service.load()
        classified: list[dict] = []
        bus.subscribe(
            ORCHESTRATION_INTENT_CLASSIFIED,
            lambda e: classified.append(dict(e.payload)),
        )
        try:
            ws_id = uuid4().hex
            bus.publish(
                COMMAND_ROUTED,
                {
                    "intent": INTENT_CHAT,
                    "request_id": "req-orch",
                    "args": {"prompt": "what time is it"},
                    "workspace_id": ws_id,
                    "selected_entity_id": "card-1",
                    "selected_entity_type": ENTITY_TYPE_CARD,
                    "selected_entity_title": "Ops",
                },
                source="command_router",
            )
            self.assertEqual(1, len(classified))
            payload = classified[0]
            self.assertEqual(ws_id, payload.get("workspace_id"))
            self.assertEqual("card-1", payload.get("selected_entity_id"))
            args = payload.get("args") or {}
            self.assertEqual(ws_id, args.get("workspace_id"))
        finally:
            service.unload()


class Phase6bModelRouterScopeTests(unittest.TestCase):
    def test_model_resolve_request_carries_workspace_hints(self) -> None:
        bus = EventBus()
        router = ModelRouterService(bus)
        router.load()
        selected: list[dict] = []
        bus.subscribe(MODEL_SELECTED, lambda e: selected.append(dict(e.payload)))
        try:
            bus.publish(
                SETTINGS_SNAPSHOT,
                {"default_model": "llama3.2:3b", "provider": "ollama"},
                source="tests",
            )
            bus.publish(
                MODEL_RESOLVE_REQUEST,
                {
                    "request_id": "mr-1",
                    "intent": INTENT_CHAT,
                    "query": "implement the auth module",
                    "workspace_id": "ws-9",
                    "selected_entity_type": ENTITY_TYPE_CARD,
                    "selected_entity_id": "card-1",
                },
                source="tests",
            )
            self.assertEqual(1, len(selected))
            payload = selected[0]
            self.assertEqual("ws-9", payload.get("workspace_id"))
            self.assertEqual(ENTITY_TYPE_CARD, payload.get("selected_entity_type"))
            self.assertEqual("workspace_task_hint", payload.get("reason"))
        finally:
            router.unload()

    def test_model_resolve_result_echoes_workspace_scope(self) -> None:
        bus = EventBus()
        router = ModelRouterService(bus)
        router.load()
        results: list[dict] = []
        bus.subscribe(MODEL_RESOLVE_RESULT, lambda e: results.append(dict(e.payload)))
        try:
            bus.publish(
                SETTINGS_SNAPSHOT,
                {"default_model": "llama3.2:3b", "provider": "ollama"},
                source="tests",
            )
            bus.publish(
                MODEL_RESOLVE_REQUEST,
                {
                    "request_id": "mr-2",
                    "intent": INTENT_CHAT,
                    "query": "hello",
                    "workspace_id": "ws-10",
                    "selected_entity_type": ENTITY_TYPE_CARD,
                },
                source="tests",
            )
            self.assertEqual(1, len(results))
            self.assertEqual("ws-10", results[0].get("workspace_id"))
            self.assertEqual(ENTITY_TYPE_CARD, results[0].get("selected_entity_type"))
        finally:
            router.unload()


class Phase6bRuntimeCapabilityScopeTests(unittest.TestCase):
    def test_capability_dispatch_includes_workspace_scope(self) -> None:
        bus = EventBus()
        service = RuntimeCapabilityRouterService(bus, obsidian=MagicMock())
        service.load()
        classified: list[dict] = []
        dispatched: list[dict] = []
        bus.subscribe(CAPABILITY_CLASSIFIED, lambda e: classified.append(dict(e.payload)))
        bus.subscribe(CAPABILITY_DISPATCH, lambda e: dispatched.append(dict(e.payload)))
        try:
            ws_id = uuid4().hex
            bus.publish(
                WORKSPACE_ACTIVE,
                {"workspace_id": ws_id, "title": "Scope"},
                source="tests",
            )
            bus.publish(
                COMMAND_ROUTED,
                {
                    "intent": INTENT_CHAT,
                    "request_id": "cap-1",
                    "args": {"prompt": "hello capability"},
                    "workspace_id": ws_id,
                    "selected_entity_id": "ent-22",
                    "selected_entity_type": ENTITY_TYPE_CARD,
                    "selected_entity_title": "Canvas",
                },
                source="command_router",
            )
            self.assertEqual(1, len(classified))
            self.assertEqual(1, len(dispatched))
            self.assertEqual(ws_id, classified[0].get("workspace_id"))
            self.assertEqual("ent-22", dispatched[0].get("workspace_entity_id"))
            self.assertEqual(ENTITY_TYPE_CARD, dispatched[0].get("workspace_entity_type"))
        finally:
            service.unload()


if __name__ == "__main__":
    unittest.main()
