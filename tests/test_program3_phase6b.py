"""Program 3 Phase 6b — workspace-aware orchestration and routing scope."""

from __future__ import annotations

import unittest
from uuid import uuid4

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    GOAL_SUBMIT_REQUEST,
    MODEL_RESOLVE_REQUEST,
    MODEL_RESOLVE_RESULT,
    MODEL_SELECTED,
    SETTINGS_SNAPSHOT,
    UI_COMMAND,
    WORKSPACE_ACTIVE,
)
from ai_command_center.core.entity.entity import ENTITY_TYPE_CARD
from ai_command_center.domain.runtime_capability import CapabilityKind
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.services.model_router_service import ModelRouterService
from ai_command_center.services.runtime_capability_router_service import (
    RuntimeCapabilityRouterService,
)


class Phase6bOrchestrationScopeTests(unittest.TestCase):
    def test_authority_goal_submit_includes_workspace_scope(self) -> None:
        bus = EventBus()
        service = ExecutionAuthorityService(bus)
        service.load()
        goals: list[dict] = []
        bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: goals.append(dict(e.payload)))
        try:
            ws_id = uuid4().hex
            bus.publish(
                WORKSPACE_ACTIVE,
                {"workspace_id": ws_id, "title": "Scope"},
                source="tests",
            )
            bus.publish(
                UI_COMMAND,
                {
                    "text": "hello capability",
                    "selected_entity_id": "card-1",
                    "selected_entity_type": ENTITY_TYPE_CARD,
                    "selected_entity_title": "Ops",
                },
                source="tests",
            )
            self.assertEqual(1, len(goals))
            payload = goals[0]
            self.assertEqual(ws_id, payload.get("workspace_id"))
            self.assertEqual("llm", payload["plan"]["steps"][0]["capability"])
            self.assertEqual("card-1", payload["workspace_context"].get("entity_id"))
            self.assertEqual(ENTITY_TYPE_CARD, payload["workspace_context"].get("entity_type"))
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
    def test_runtime_capability_router_is_classifier_and_provider_map_only(self) -> None:
        bus = EventBus()
        service = RuntimeCapabilityRouterService(bus)
        service.load()
        try:
            bus.publish(
                SETTINGS_SNAPSHOT,
                {"capability_provider_planning": "native"},
                source="settings",
            )
            self.assertEqual(
                CapabilityKind.PLANNING,
                RuntimeCapabilityRouterService.classify("schedule standup"),
            )
            self.assertEqual("native", service.resolve_provider(CapabilityKind.PLANNING))
        finally:
            service.unload()


if __name__ == "__main__":
    unittest.main()
