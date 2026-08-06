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


def test_distinct_tier_models_without_brain_vendor_branch() -> None:
    """ADR-023 M2: settings-backed distinct tiers; no hardcoded vendor in Brain."""
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
                "summarize_model": "llama3.2:1b",
                "model_tier_map": {
                    "fast": "llama3.2:1b",
                    "balanced": "llama3.2:3b",
                    "reasoning": "gpt-4o-mini",
                },
            },
            source="test",
        )
        # Summarize → fast tier model from map / summarize_model path
        bus.publish(
            MODEL_RESOLVE_REQUEST,
            {
                "request_id": "tier-fast",
                "intent": INTENT_CHAT,
                "query": "please summarize this note",
            },
            source="test",
        )
        # Code + card → reasoning
        bus.publish(
            MODEL_RESOLVE_REQUEST,
            {
                "request_id": "tier-reason",
                "intent": INTENT_CHAT,
                "query": "refactor the auth module",
                "workspace_id": "ws-1",
                "selected_entity_type": ENTITY_TYPE_CARD,
                "selected_entity_id": "card-1",
            },
            source="test",
        )
        # Plain → balanced
        bus.publish(
            MODEL_RESOLVE_REQUEST,
            {
                "request_id": "tier-bal",
                "intent": INTENT_CHAT,
                "query": "what time is it",
            },
            source="test",
        )
        assert len(selected) >= 3
        by_tier: dict[str, str] = {}
        for item in selected:
            by_tier[str(item.get("routing_tier"))] = str(item.get("model"))
        assert by_tier.get("reasoning") == "gpt-4o-mini"
        assert by_tier.get("balanced") == "llama3.2:3b"
        assert by_tier.get("fast") in {"llama3.2:1b", "llama3.2:3b"}
        assert by_tier["reasoning"] != by_tier["balanced"]
    finally:
        router.stop()


def test_brain_runtime_source_has_no_vendor_model_literals() -> None:
    from pathlib import Path

    text = Path("ai_command_center/services/brain_runtime_service.py").read_text(
        encoding="utf-8"
    )
    assert "gpt-4o" not in text
    assert "gpt-4" not in text
    assert "claude-" not in text.lower()
