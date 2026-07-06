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
from ai_command_center.platform.model_registry import (
    classify_model,
    normalize_tier_map,
)
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
        self._tier_map = normalize_tier_map({}, default_model=self._default_model)
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
        self._tier_map = normalize_tier_map(
            event.payload.get("model_tier_map"),
            default_model=self._default_model,
        )

    def _model_for_tier(self, tier: str) -> str:
        return self._tier_map.get(tier) or self._default_model

    def _on_resolve_request(self, event: Event) -> None:
        intent = str(event.payload.get("intent", "chat"))
        query = str(event.payload.get("query", ""))
        workspace_id = str(event.payload.get("workspace_id", "")).strip()
        selected_entity_type = str(event.payload.get("selected_entity_type", "")).strip()
        selected_entity_id = str(event.payload.get("selected_entity_id", "")).strip()
        model, provider = self.resolve(
            intent=intent,
            query=query,
            workspace_id=workspace_id,
            selected_entity_type=selected_entity_type,
            selected_entity_id=selected_entity_id,
        )
        result_payload: dict[str, object] = {
            "request_id": event.payload.get("request_id", ""),
            "model": model,
            "provider": provider,
        }
        if workspace_id:
            result_payload["workspace_id"] = workspace_id
        if selected_entity_type:
            result_payload["selected_entity_type"] = selected_entity_type
        if selected_entity_id:
            result_payload["selected_entity_id"] = selected_entity_id
        self._bus.publish(MODEL_RESOLVE_RESULT, result_payload, source=self.name)

    def resolve(
        self,
        *,
        intent: str,
        query: str,
        workspace_id: str = "",
        selected_entity_type: str = "",
        selected_entity_id: str = "",
    ) -> tuple[str, str]:
        """Pick (model, provider) for a chat request via ProviderRegistry."""
        lower = query.lower()
        summarize_tokens = ("summarize", "summary", "tl;dr", "tldr")
        routing_tier = "balanced"
        if intent == "chat" and any(token in lower for token in summarize_tokens):
            model = self._summarize_model
            reason = "summarize_intent"
            routing_tier = "fast"
        elif selected_entity_type == "note" and any(token in lower for token in summarize_tokens):
            model = self._summarize_model
            reason = "workspace_note_hint"
            routing_tier = "fast"
        elif selected_entity_type in {"card", "resource"} and any(
            hint in lower for hint in ("implement", "refactor", "fix bug", "write code")
        ):
            model = self._model_for_tier("reasoning")
            reason = "workspace_task_hint"
            routing_tier = "reasoning"
        else:
            model = self._model_for_tier("balanced")
            reason = "workspace_default" if workspace_id else "default"
            routing_tier = "balanced"
        provider = (
            self._registry.resolve_for_model(model, provider=self._provider)
            or self._provider
        )
        logger.info(
            "model.resolve intent=%s model=%s provider=%s reason=%s workspace=%s entity=%s",
            intent,
            model,
            provider,
            reason,
            workspace_id or "-",
            selected_entity_type or "-",
        )
        selected_payload: dict[str, object] = {
            "model": model,
            "intent": intent,
            "reason": reason,
            "provider": provider,
            "routing_tier": routing_tier,
            "capability_tier": classify_model(model).value,
            "tier": classify_model(model).value,
            "resolved_by": "model_router",
        }
        if workspace_id:
            selected_payload["workspace_id"] = workspace_id
        if selected_entity_type:
            selected_payload["selected_entity_type"] = selected_entity_type
        if selected_entity_id:
            selected_payload["selected_entity_id"] = selected_entity_id
        self._bus.publish(MODEL_SELECTED, selected_payload, source=self.name)
        return model, provider
