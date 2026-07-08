"""Integration tests for ModelRouter → single provider LLM dispatch (Program 1 S3)."""

from __future__ import annotations

from ai_command_center.core.context_manager import ContextBundle
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    COMMAND_ROUTED,
    LLM_REQUEST,
    MODEL_SELECTED,
    MEMORY_LOOKUP_REQUEST,
    MEMORY_LOOKUP_RESULT,
    MODEL_RESOLVE_REQUEST,
    MODEL_RESOLVE_RESULT,
    SESSION_HISTORY_REQUEST,
    SESSION_HISTORY_RESULT,
    SETTINGS_SNAPSHOT,
)
from ai_command_center.providers.provider_registry import build_default_registry
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.model_router_service import ModelRouterService
from ai_command_center.services.ollama_http_service import OllamaHttpService
from ai_command_center.services.openai_http_service import OpenAIHttpService


def test_model_router_resolves_provider_and_single_llm_handler() -> None:
    bus = EventBus()
    registry = build_default_registry()
    router = ModelRouterService(bus, registry)
    ollama = OllamaHttpService(bus)
    openai = OpenAIHttpService(bus)

    router.start()
    ollama.start()
    openai.start()
    try:
        bus.publish(
            SETTINGS_SNAPSHOT,
            {"default_model": "gpt-4o-mini", "provider": "openai"},
            source="test",
        )

        resolve_results: list[dict] = []
        llm_handlers: list[str] = []

        bus.subscribe(
            MODEL_RESOLVE_RESULT,
            lambda e: resolve_results.append(dict(e.payload)),
        )

        def _track_ollama(event) -> None:
            provider = str(event.payload.get("provider", "")).strip()
            if provider == "ollama":
                llm_handlers.append("ollama")

        def _track_openai(event) -> None:
            provider = str(event.payload.get("provider", "")).strip()
            if provider == "openai":
                llm_handlers.append("openai")

        unsub_ollama = bus.subscribe(LLM_REQUEST, _track_ollama)
        unsub_openai = bus.subscribe(LLM_REQUEST, _track_openai)
        try:
            bus.publish(
                MODEL_RESOLVE_REQUEST,
                {"request_id": "r1", "intent": "chat", "query": "hello"},
                source="test",
            )

            assert len(resolve_results) == 1
            assert resolve_results[0]["model"] == "gpt-4o-mini"
            assert resolve_results[0]["provider"] == "openai"

            bundle = ContextBundle(
                prompt="hello",
                sources=("query",),
                token_estimate=1,
            )
            bus.publish(
                LLM_REQUEST,
                {
                    "request_id": "r1",
                    "model": resolve_results[0]["model"],
                    "provider": resolve_results[0]["provider"],
                    "bundle": bundle,
                },
                source="test",
            )
            assert llm_handlers == ["openai"]
        finally:
            unsub_ollama()
            unsub_openai()
    finally:
        ollama.stop()
        openai.stop()
        router.stop()


def test_model_router_uses_settings_backed_workspace_task_hint() -> None:
    bus = EventBus()
    router = ModelRouterService(bus, build_default_registry())
    selected: list[dict] = []
    resolved: list[dict] = []
    bus.subscribe(MODEL_SELECTED, lambda e: selected.append(dict(e.payload)))
    bus.subscribe(MODEL_RESOLVE_RESULT, lambda e: resolved.append(dict(e.payload)))

    router.start()
    try:
        bus.publish(
            SETTINGS_SNAPSHOT,
            {
                "default_model": "llama3.2:3b",
                "provider": "ollama",
                "model_tier_map": {"entity:note": "qwen2.5:7b", "summarize": "llama3.1:8b"},
            },
            source="test",
        )
        bus.publish(
            MODEL_RESOLVE_REQUEST,
            {
                "request_id": "note-1",
                "intent": "chat",
                "query": "explain this note",
                "workspace_task_hint": "entity:note",
                "workspace_entity_type": "note",
            },
            source="test",
        )

        assert resolved[0]["model"] == "qwen2.5:7b"
        assert resolved[0]["reason"] == "tier_map:entity:note"
        assert selected[0]["workspace_task_hint"] == "entity:note"
        assert selected[0]["workspace_entity_type"] == "note"
    finally:
        router.stop()


def test_chat_handler_uses_model_router_before_llm_dispatch() -> None:
    bus = EventBus()
    router = ModelRouterService(bus, build_default_registry())
    chat = ChatHandlerService(bus, ContextManager(max_context_tokens=4096))
    provider_handlers: list[str] = []
    llm_payloads: list[dict] = []
    resolve_requests: list[dict] = []

    def _session_history(event) -> None:
        bus.publish(
            SESSION_HISTORY_RESULT,
            {"request_id": event.payload["request_id"], "history": []},
            source="test",
        )

    def _memory_lookup(event) -> None:
        bus.publish(
            MEMORY_LOOKUP_RESULT,
            {"request_id": event.payload["request_id"], "snippets": []},
            source="test",
        )

    def _track_resolve(event) -> None:
        resolve_requests.append(dict(event.payload))

    def _ollama_provider(event) -> None:
        if event.payload.get("provider") == "ollama":
            provider_handlers.append("ollama")

    def _openai_provider(event) -> None:
        if event.payload.get("provider") == "openai":
            provider_handlers.append("openai")

    unsubs = [
        bus.subscribe(SESSION_HISTORY_REQUEST, _session_history),
        bus.subscribe(MEMORY_LOOKUP_REQUEST, _memory_lookup),
        bus.subscribe(MODEL_RESOLVE_REQUEST, _track_resolve),
        bus.subscribe(LLM_REQUEST, lambda e: llm_payloads.append(dict(e.payload))),
        bus.subscribe(LLM_REQUEST, _ollama_provider),
        bus.subscribe(LLM_REQUEST, _openai_provider),
    ]

    router.start()
    chat.start()
    try:
        bus.publish(
            SETTINGS_SNAPSHOT,
            {"default_model": "gpt-4o-mini", "provider": "openai"},
            source="test",
        )
        bus.publish(
            COMMAND_ROUTED,
            {
                "intent": INTENT_CHAT,
                "args": {"prompt": "hello through the router"},
            },
            source="command_router",
        )

        assert len(resolve_requests) == 1
        assert resolve_requests[0]["intent"] == INTENT_CHAT
        assert len(llm_payloads) == 1
        assert llm_payloads[0]["model"] == "gpt-4o-mini"
        assert llm_payloads[0]["provider"] == "openai"
        assert provider_handlers == ["openai"]
    finally:
        chat.stop()
        router.stop()
        for unsub in unsubs:
            unsub()
