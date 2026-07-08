"""Task → model routing — static map, no autonomous switching (Phase 4F)."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

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
        self._model_tier_map: dict[str, str] = {}
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
        tier_map = event.payload.get("model_tier_map", {})
        self._model_tier_map = self._parse_model_tier_map(tier_map)

    def _on_resolve_request(self, event: Event) -> None:
        intent = str(event.payload.get("intent", "chat"))
        query = str(event.payload.get("query", ""))
        workspace_task_hint = str(event.payload.get("workspace_task_hint", "")).strip()
        workspace_entity_type = str(event.payload.get("workspace_entity_type", "")).strip()
        model, provider, reason = self._resolve_with_reason(
            intent=intent,
            query=query,
            workspace_task_hint=workspace_task_hint,
            workspace_entity_type=workspace_entity_type,
        )
        self._bus.publish(
            MODEL_RESOLVE_RESULT,
            {
                "request_id": event.payload.get("request_id", ""),
                "model": model,
                "provider": provider,
                "reason": reason,
            },
            source=self.name,
        )

    @staticmethod
    def _parse_model_tier_map(value: Any) -> dict[str, str]:
        if isinstance(value, dict):
            return {
                str(k).strip().lower(): str(v).strip()
                for k, v in value.items()
                if str(k).strip() and str(v).strip()
            }
        if isinstance(value, str):
            try:
                parsed = json.loads(value or "{}")
            except json.JSONDecodeError:
                return {}
            if isinstance(parsed, dict):
                return ModelRouterService._parse_model_tier_map(parsed)
        return {}

    def _mapped_model(self, *keys: str) -> tuple[str, str] | None:
        for key in keys:
            normalized = key.strip().lower()
            if not normalized:
                continue
            model = self._model_tier_map.get(normalized)
            if model:
                return model, f"tier_map:{normalized}"
        return None

    def resolve(
        self,
        *,
        intent: str,
        query: str,
        workspace_task_hint: str = "",
        workspace_entity_type: str = "",
    ) -> str:
        """Return the selected model name; legacy verification scripts use this."""
        model, _provider, _reason = self._resolve_with_reason(
            intent=intent,
            query=query,
            workspace_task_hint=workspace_task_hint,
            workspace_entity_type=workspace_entity_type,
        )
        return model

    def _resolve_with_reason(
        self,
        *,
        intent: str,
        query: str,
        workspace_task_hint: str = "",
        workspace_entity_type: str = "",
    ) -> tuple[str, str, str]:
        """Pick (model, provider) for a chat request via ProviderRegistry."""
        lower = query.lower()
        mapped = self._mapped_model(
            workspace_task_hint,
            f"entity:{workspace_entity_type}" if workspace_entity_type else "",
            workspace_entity_type,
            intent,
        )
        if mapped is not None:
            model, reason = mapped
        elif intent == "chat" and any(
            token in lower for token in ("summarize", "summary", "tl;dr", "tldr")
        ):
            mapped = self._mapped_model("summarize", "summary")
            if mapped is not None:
                model, reason = mapped
            else:
                model = self._summarize_model
                reason = "summarize_intent"
        else:
            mapped = self._mapped_model("default")
            if mapped is not None:
                model, reason = mapped
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
                "workspace_task_hint": workspace_task_hint,
                "workspace_entity_type": workspace_entity_type,
            },
            source=self.name,
        )
        return model, provider, reason
