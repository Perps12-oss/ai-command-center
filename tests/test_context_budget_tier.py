"""Program 4 slice 2 — context budget tier downgrade."""

from __future__ import annotations

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.entity.entity import ENTITY_TYPE_CARD
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    CONTEXT_OVER_BUDGET,
    MODEL_RESOLVE_REQUEST,
    MODEL_SELECTED,
    SETTINGS_SNAPSHOT,
    TOOL_COMPLETED,
    TOOL_FAILED,
    TOOL_STARTED,
)
from ai_command_center.services.model_router_service import ModelRouterService


def test_context_over_budget_downgrades_reasoning_tier() -> None:
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
                    "fast": "llama3.2:1b",
                    "balanced": "llama3.2:3b",
                    "reasoning": "gpt-4o-mini",
                },
            },
            source="test",
        )
        bus.publish(
            MODEL_RESOLVE_REQUEST,
            {
                "request_id": "budget-1",
                "intent": INTENT_CHAT,
                "query": "implement the auth module",
                "workspace_id": "ws-1",
                "selected_entity_type": ENTITY_TYPE_CARD,
                "selected_entity_id": "card-1",
                "context_size_tokens": 9000,
                "budget_tokens": 8000,
                "context_over_budget": True,
            },
            source="test",
        )
        assert len(selected) == 1
        payload = selected[0]
        assert payload["model"] == "llama3.2:3b"
        assert payload["routing_tier"] == "balanced"
        assert payload["reason"] == "context_over_budget"
    finally:
        router.stop()


def test_context_over_budget_sticky_flag_downgrades_next_resolve() -> None:
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
                    "fast": "llama3.2:1b",
                    "balanced": "llama3.2:3b",
                    "reasoning": "gpt-4o-mini",
                },
            },
            source="test",
        )
        bus.publish(
            CONTEXT_OVER_BUDGET,
            {"context_size_tokens": 12000, "budget_tokens": 8000},
            source="test",
        )
        bus.publish(
            MODEL_RESOLVE_REQUEST,
            {
                "request_id": "budget-2",
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
        assert payload["model"] == "llama3.2:3b"
        assert payload["routing_tier"] == "balanced"
        assert payload["reason"] == "context_over_budget"
    finally:
        router.stop()


def test_recent_tool_runs_projects_into_app_state() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        bus.publish(
            TOOL_STARTED,
            {"tool": "shell", "invoke_id": "inv-1"},
            source="test",
        )
        bus.publish(
            TOOL_COMPLETED,
            {"tool": "shell", "invoke_id": "inv-1"},
            source="test",
        )
        bus.publish(
            TOOL_FAILED,
            {
                "tool": "read_file",
                "invoke_id": "inv-2",
                "error": "not found",
                "message": "file missing",
            },
            source="test",
        )
        runs = store.snapshot.recent_tool_runs
        assert len(runs) == 2
        assert runs[0].tool == "read_file"
        assert runs[0].status == "failed"
        assert runs[0].error == "not found"
        assert runs[1].tool == "shell"
        assert runs[1].status == "completed"
    finally:
        store.close()
