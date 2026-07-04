"""Task → model routing — static map, no autonomous switching (Phase 4F)."""

from __future__ import annotations

import logging
from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    MODEL_RESOLVE_REQUEST,
    MODEL_RESOLVE_RESULT,
    MODEL_SELECTED,
    SETTINGS_SNAPSHOT,
)
from ai_command_center.platform.model_registry import classify_model
from ai_command_center.providers.provider_registry import ProviderRegistry
from ai_command_center.services.base import BaseService

logger = logging.getLogger(__name__)


class ModelRouterService(BaseService):
    name = "model_router"

    def __init__(self, bus, provider_registry: ProviderRegistry | None = None) -> None:
        super().__init__(bus)
        from ai_command_center.providers.provider_registry import build_default_registry

        self._registry = provider_registry or build_default_registry()
        self._default_model = "llama3.2:3b"
        self._summarize_model = "llama3.2:3b"
        self._provider = "ollama"
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(SETTINGS_SNAPSHOT, self._on_settings_snapshot)
        )
        self._unsubscribers.append(
            self._bus.subscribe(MODEL_RESOLVE_REQUEST, self._on_resolve_request)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_settings_snapshot(self, event: Event) -> None:
        default = str(event.payload.get("default_model", "")).strip()
        if default:
            self._default_model = default
        summarize = str(event.payload.get("summarize_model", "")).strip()
        if summarize:
            self._summarize_model = summarize
        provider = str(event.payload.get("provider", "")).strip()
        if provider:
            self._provider = provider

    def _on_resolve_request(self, event: Event) -> None:
        intent = str(event.payload.get("intent", "chat"))
        query = str(event.payload.get("query", ""))
        model, provider = self.resolve(intent=intent, query=query)
        self._bus.publish(
            MODEL_RESOLVE_RESULT,
            {
                "request_id": event.payload.get("request_id", ""),
                "model": model,
                "provider": provider,
            },
            source=self.name,
        )

    def resolve(self, *, intent: str, query: str) -> tuple[str, str]:
        """Pick (model, provider) for a chat request via ProviderRegistry."""
        lower = query.lower()
        if intent == "chat" and any(
            token in lower for token in ("summarize", "summary", "tl;dr", "tldr")
        ):
            model = self._summarize_model
            reason = "summarize_intent"
        else:
            model = self._default_model
            reason = "default"
        provider = (
            self._registry.resolve_for_model(model, provider=self._provider)
            or self._provider
        )
        logger.info(
            "model.resolve intent=%s model=%s provider=%s reason=%s",
            intent,
            model,
            provider,
            reason,
        )
        self._bus.publish(
            MODEL_SELECTED,
            {
                "model": model,
                "intent": intent,
                "reason": reason,
                "provider": provider,
                "tier": classify_model(model).value,
            },
            source=self.name,
        )
        return model, provider
