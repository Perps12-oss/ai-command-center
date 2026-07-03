"""Single- and per-entity chat persistence — load history, append messages (Phase 3D + C3)."""

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
    UI_CHAT_NEW_SESSION,
    UI_OPEN_CHAT,
)
from ai_command_center.repositories.conversation_repository import (
    CONTEXT_HISTORY_LIMIT,
    DEFAULT_CONVERSATION_ID,
    ConversationRepository,
    entity_conversation_id,
)
from ai_command_center.services.base import BaseService


class SessionService(BaseService):
    """Persists conversations; supports default and per-entity session keys."""

    name = "session"

    def __init__(self, bus, repo: ConversationRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._default_model = "llama3.2:3b"
        self._active_conversation_id = DEFAULT_CONVERSATION_ID
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
        self._unsubscribers.append(
            self._bus.subscribe(UI_OPEN_CHAT, self._on_open_chat)
        )
        self._unsubscribers.append(
            self._bus.subscribe(UI_CHAT_NEW_SESSION, self._on_new_session)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_settings_snapshot(self, event: Event) -> None:
        model = str(event.payload.get("default_model", ""))
        if model:
            self._default_model = model
            self._repo.ensure_conversation(
                self._active_conversation_id,
                model=model,
            )

    def get_context_history(self) -> list[tuple[str, str]]:
        return self._repo.get_history_pairs(
            CONTEXT_HISTORY_LIMIT,
            conversation_id=self._active_conversation_id,
        )

    def append_user_message(self, content: str) -> None:
        if content.strip():
            self._repo.append_message(
                "user",
                content,
                conversation_id=self._active_conversation_id,
            )

    def _switch_conversation(self, conversation_id: str, *, title: str = "Session") -> None:
        self._active_conversation_id = conversation_id
        self._repo.ensure_conversation(
            conversation_id,
            model=self._default_model,
            title=title,
        )
        self._publish_history()

    def _on_open_chat(self, event: Event) -> None:
        entity_id = str(event.payload.get("entity_id", "")).strip()
        if not entity_id:
            self._switch_conversation(DEFAULT_CONVERSATION_ID)
            return
        entity_type = str(event.payload.get("entity_type", "entity"))
        title = str(event.payload.get("title", entity_id))
        cid = entity_conversation_id(entity_type, entity_id)
        self._switch_conversation(cid, title=title[:80] or "Entity chat")

    def _on_new_session(self, _event: Event) -> None:
        self._switch_conversation(DEFAULT_CONVERSATION_ID)
        self._repo.clear_messages(DEFAULT_CONVERSATION_ID)
        self._publish_history()

    def _on_history_request(self, event: Event) -> None:
        self._bus.publish(
            SESSION_HISTORY_RESULT,
            {
                "request_id": event.payload.get("request_id", ""),
                "history": self.get_context_history(),
                "conversation_id": self._active_conversation_id,
            },
            source=self.name,
        )

    def _on_update_request(self, event: Event) -> None:
        role = str(event.payload.get("role", "user")).strip() or "user"
        content = str(event.payload.get("content", "")).strip()
        if content:
            self._repo.append_message(
                role,
                content,
                conversation_id=self._active_conversation_id,
            )
            self._bus.publish(
                SESSION_UPDATE_RESULT,
                {
                    "request_id": event.payload.get("request_id", ""),
                    "role": role,
                    "content": content,
                    "conversation_id": self._active_conversation_id,
                },
                source=self.name,
            )

    def _on_chat_complete(self, event: Event) -> None:
        text = str(event.payload.get("text", "")).strip()
        if not text:
            return
        self._repo.append_message(
            "assistant",
            text,
            conversation_id=self._active_conversation_id,
        )
        self._publish_history()

    def _publish_history(self) -> None:
        messages = [
            {"role": m.role, "content": m.content, "created_at": m.created_at}
            for m in self._repo.list_messages(self._active_conversation_id)
        ]
        self._bus.publish(
            CHAT_HISTORY_LOADED,
            {
                "messages": messages,
                "conversation_id": self._active_conversation_id,
            },
            source=self.name,
        )
