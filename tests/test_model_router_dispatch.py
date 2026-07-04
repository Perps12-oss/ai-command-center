"""Integration tests for ModelRouter → single provider LLM dispatch (Program 1 S3)."""

from __future__ import annotations

from ai_command_center.core.context_manager import ContextBundle
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    LLM_REQUEST,
    MODEL_RESOLVE_REQUEST,
    MODEL_RESOLVE_RESULT,
    SETTINGS_SNAPSHOT,
)
from ai_command_center.providers.provider_registry import build_default_registry
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
