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
from ai_command_center.services.base import BaseService

logger = logging.getLogger(__name__)


class ModelRouterService(BaseService):
    name = "model_router"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._default_model = "llama3.2:3b"
        self._summarize_model = "llama3.2:3b"
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

    def _on_resolve_request(self, event: Event) -> None:
        intent = str(event.payload.get("intent", "chat"))
        query = str(event.payload.get("query", ""))
        model = self.resolve(intent=intent, query=query)
        self._bus.publish(
            MODEL_RESOLVE_RESULT,
            {"request_id": event.payload.get("request_id", ""), "model": model},
            source=self.name,
        )

    def resolve(self, *, intent: str, query: str) -> str:
        """Pick model for a chat request; settings default_model always wins as base."""
        lower = query.lower()
        if intent == "chat" and any(
            token in lower for token in ("summarize", "summary", "tl;dr", "tldr")
        ):
            model = self._summarize_model
            reason = "summarize_intent"
        else:
            model = self._default_model
            reason = "default"
        logger.info("model.resolve intent=%s model=%s reason=%s", intent, model, reason)
        self._bus.publish(
            MODEL_SELECTED,
            {
                "model": model,
                "intent": intent,
                "reason": reason,
                "tier": classify_model(model).value,
            },
            source=self.name,
        )
        return model
