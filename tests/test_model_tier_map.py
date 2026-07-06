"""Program 4 — settings-backed model tier routing."""

from __future__ import annotations

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.entity.entity import ENTITY_TYPE_CARD
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import MODEL_RESOLVE_REQUEST, MODEL_SELECTED, SETTINGS_SNAPSHOT
from ai_command_center.services.model_router_service import ModelRouterService


def test_model_router_uses_settings_tier_map_for_reasoning() -> None:
    bus = EventBus()
    router = ModelRouterService(bus)
    selected: list[dict] = []
    bus.subscribe(MODEL_SELECTED, lambda e: selected.append(dict(e.payload)))
    router.start()
    try:
        bus.publish(
            SETTINGS_SNAPSHOT,
            {
                "default_model": "llama3.2:3b",
                "provider": "ollama",
                "model_tier_map": {
                    "fast": "llama3.2:3b",
                    "balanced": "llama3.2:3b",
                    "reasoning": "gpt-4o-mini",
                },
            },
            source="test",
        )
        bus.publish(
            MODEL_RESOLVE_REQUEST,
            {
                "request_id": "tier-1",
                "intent": INTENT_CHAT,
                "query": "implement the auth module",
                "workspace_id": "ws-1",
                "selected_entity_type": ENTITY_TYPE_CARD,
                "selected_entity_id": "card-1",
            },
            source="test",
        )
        assert len(selected) == 1
        payload = selected[0]
        assert payload["model"] == "gpt-4o-mini"
        assert payload["routing_tier"] == "reasoning"
        assert payload["reason"] == "workspace_task_hint"
    finally:
        router.stop()


def test_model_selected_projects_into_app_state() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    router = ModelRouterService(bus)
    router.start()
    try:
        bus.publish(
            SETTINGS_SNAPSHOT,
            {"default_model": "llama3.2:3b", "provider": "ollama"},
            source="test",
        )
        bus.publish(
            MODEL_RESOLVE_REQUEST,
            {"request_id": "ms-1", "intent": INTENT_CHAT, "query": "hello"},
            source="test",
        )
        selection = store.snapshot.model_selection
        assert selection.model == "llama3.2:3b"
        assert selection.routing_tier == "balanced"
        assert selection.resolved_by == "model_router"
    finally:
        router.stop()
        store.close()
