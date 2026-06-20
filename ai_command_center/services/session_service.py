"""Single-session chat persistence — load history, append messages (Phase 3D)."""

from __future__ import annotations

from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CHAT_COMPLETE,
    CHAT_HISTORY_LOADED,
    SETTINGS_SNAPSHOT,
    SESSION_HISTORY_REQUEST,
    SESSION_HISTORY_RESULT,
    SESSION_UPDATE_REQUEST,
    SESSION_UPDATE_RESULT,
)
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
            self._bus.subscribe(SETTINGS_SNAPSHOT, self._on_settings_snapshot)
        )
        self._unsubscribers.append(
            self._bus.subscribe(CHAT_COMPLETE, self._on_chat_complete)
        )
        self._unsubscribers.append(
            self._bus.subscribe(SESSION_HISTORY_REQUEST, self._on_history_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(SESSION_UPDATE_REQUEST, self._on_update_request)
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

    def _on_history_request(self, event: Event) -> None:
        self._bus.publish(
            SESSION_HISTORY_RESULT,
            {
                "request_id": event.payload.get("request_id", ""),
                "history": self.get_context_history(),
            },
            source=self.name,
        )

    def _on_update_request(self, event: Event) -> None:
        role = str(event.payload.get("role", "user")).strip() or "user"
        content = str(event.payload.get("content", "")).strip()
        if content:
            self._repo.append_message(role, content)
            self._bus.publish(
                SESSION_UPDATE_RESULT,
                {"request_id": event.payload.get("request_id", ""), "role": role, "content": content},
                source=self.name,
            )

    def _on_chat_complete(self, event: Event) -> None:
        text = str(event.payload.get("text", "")).strip()
        if not text:
            return
        self._repo.append_message("assistant", text)
        self._publish_history()

    def _publish_history(self) -> None:
        messages = [
            {"role": m.role, "content": m.content, "created_at": m.created_at}
            for m in self._repo.list_messages()
        ]
        self._bus.publish(
            CHAT_HISTORY_LOADED,
            {"messages": messages},
            source=self.name,
        )
