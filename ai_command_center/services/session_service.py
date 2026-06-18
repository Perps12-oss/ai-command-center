"""Single-session chat persistence — load history, append messages (Phase 3D)."""

from __future__ import annotations

from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.db.conversation_repository import (
    CONTEXT_HISTORY_LIMIT,
    ConversationRepository,
)
from ai_command_center.services.base import BaseService


class SessionService(BaseService):
    """Persists one conversation; publishes history for UI on load."""

    name = "session"

    def __init__(self, bus, repo: ConversationRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._default_model = "llama3.2:3b"
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._repo.ensure_default(model=self._default_model)
        self._publish_history()
        self._unsubscribers.append(
            self._bus.subscribe("settings.snapshot", self._on_settings_snapshot)
        )
        self._unsubscribers.append(
            self._bus.subscribe("chat.complete", self._on_chat_complete)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_settings_snapshot(self, event: Event) -> None:
        model = str(event.payload.get("default_model", ""))
        if model:
            self._default_model = model
            self._repo.ensure_default(model=model)

    def get_context_history(self) -> list[tuple[str, str]]:
        return self._repo.get_history_pairs(CONTEXT_HISTORY_LIMIT)

    def append_user_message(self, content: str) -> None:
        if content.strip():
            self._repo.append_message("user", content)

    def _on_chat_complete(self, event: Event) -> None:
        text = str(event.payload.get("text", "")).strip()
        if not text:
            return
        self._repo.append_message("assistant", text)

    def _publish_history(self) -> None:
        self._bus.publish(
            "chat.history_loaded",
            {"messages": self._repo.list_messages()},
            source=self.name,
        )
