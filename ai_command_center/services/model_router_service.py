"""Task → model routing — static map, no autonomous switching (Phase 4F)."""

from __future__ import annotations

from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.platform.model_registry import classify_model
from ai_command_center.services.base import BaseService


class ModelRouterService(BaseService):
    name = "model_router"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._default_model = "llama3.2:3b"
        self._summarize_model = "llama3.2:3b"
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe("settings.snapshot", self._on_settings_snapshot)
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
        self._bus.publish(
            "model.selected",
            {
                "model": model,
                "intent": intent,
                "reason": reason,
                "tier": classify_model(model).value,
            },
            source=self.name,
        )
        return model
