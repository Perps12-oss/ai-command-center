"""Routes chat intents through ContextManager before Ollama (Phase 3A skeleton)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from ai_command_center.core.clipboard_intent import (
    empty_clipboard_message,
    wants_clipboard,
)
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    APP_WARNING,
    CHAT_ERROR,
    COMMAND_ROUTED,
    CONTEXT_OVER_BUDGET,
    CONTEXT_SNAPSHOT_CREATED,
    CONTEXT_TRIMMED,
    LLM_REQUEST,
    MEMORY_LOOKUP_REQUEST,
    MEMORY_LOOKUP_RESULT,
    MODEL_RESOLVE_REQUEST,
    MODEL_RESOLVE_RESULT,
    NOTE_CONTEXT_RESULT,
    SESSION_HISTORY_REQUEST,
    SESSION_HISTORY_RESULT,
    SESSION_UPDATE_REQUEST,
    SETTINGS_SNAPSHOT,
)
from ai_command_center.platform.model_registry import model_warning
from ai_command_center.services.base import BaseService
from ai_command_center.services.command_router_service import INTENT_CHAT

logger = logging.getLogger(__name__)


class ChatHandlerService(BaseService):
    """
    Handles command.routed intents for chat.

    Every AI request MUST pass through ContextManager.build_context() first.
    """

    name = "chat_handler"

    def __init__(
        self,
        bus,
        context_manager: ContextManager,
        obsidian=None,
        session=None,
    ) -> None:
        super().__init__(bus)
        self._context_manager = context_manager
        self._obsidian = obsidian
        self._session = session
        self._default_model = "llama3.2:3b"
        self._provider = "ollama"
        self._unsubscribers: list[Callable[[], None]] = []
        self._pending: dict[str, dict[str, object]] = {}

    def _on_load(self) -> None:
        self._unsubscribers.append(self._bus.subscribe(COMMAND_ROUTED, self._on_command_routed))
        self._unsubscribers.append(self._bus.subscribe(SETTINGS_SNAPSHOT, self._on_settings_snapshot))
        self._unsubscribers.append(self._bus.subscribe(NOTE_CONTEXT_RESULT, self._on_note_context_result))
        self._unsubscribers.append(self._bus.subscribe(MEMORY_LOOKUP_RESULT, self._on_memory_lookup_result))
        self._unsubscribers.append(self._bus.subscribe(SESSION_HISTORY_RESULT, self._on_session_history_result))
        self._unsubscribers.append(self._bus.subscribe(MODEL_RESOLVE_RESULT, self._on_model_resolve_result))

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_settings_snapshot(self, event: Event) -> None:
        self._default_model = str(
            event.payload.get("default_model", self._default_model)
        )
        self._provider = str(event.payload.get("provider", self._provider)).strip() or "ollama"

    def _request_result(self, request_id: str) -> dict[str, object]:
        entry = self._pending.setdefault(request_id, {})
        return entry

    def _publish_request(self, topic: str, request_id: str, payload: dict[str, object]) -> None:
        self._bus.publish(topic, {"request_id": request_id, **payload}, source=self.name)

    def _on_note_context_result(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id", ""))
        if request_id:
            self._request_result(request_id)["notes"] = list(event.payload.get("notes", []))

    def _on_memory_lookup_result(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id", ""))
        if request_id:
            self._request_result(request_id)["graph_snippets"] = list(event.payload.get("snippets", []))

    def _on_session_history_result(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id", ""))
        if request_id:
            self._request_result(request_id)["history"] = list(event.payload.get("history", []))

    def _on_model_resolve_result(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id", ""))
        if request_id:
            self._request_result(request_id)["model"] = str(event.payload.get("model", self._default_model))

    def _on_command_routed(self, event: Event) -> None:
        if event.payload.get("intent") != INTENT_CHAT:
            return
        if event.source != "command_router":
            return

        args = event.payload.get("args") or {}
        query = str(args.get("prompt", "")).strip()
        if not query:
            return

        clipboard = args.get("clipboard")
        clipboard_text = str(clipboard).strip() if clipboard else None
        if clipboard_text == "":
            clipboard_text = None

        clip_intent = wants_clipboard(query)
        if clip_intent and not clipboard_text:
            self._bus.publish(
                CHAT_ERROR,
                {"message": empty_clipboard_message()},
                source=self.name,
            )
            return

        request_id = uuid.uuid4().hex
        self._pending[request_id] = {}
        logger.info("chat.request_started request_id=%s query_len=%d", request_id, len(query))

        notes_raw = args.get("notes")
        notes: list[str] = []
        if isinstance(notes_raw, list):
            notes = [str(n) for n in notes_raw if str(n).strip()]
        if self._obsidian is not None:
            notes.extend(str(n) for n in self._obsidian.get_context_notes() if str(n).strip())
        self._publish_request(MEMORY_LOOKUP_REQUEST, request_id, {"query": query})
        self._publish_request(SESSION_HISTORY_REQUEST, request_id, {})
        self._publish_request(MODEL_RESOLVE_REQUEST, request_id, {"intent": INTENT_CHAT, "query": query})

        pending = self._pending.get(request_id, {})
        graph_snippets = [str(n) for n in pending.get("graph_snippets", []) if str(n).strip()]
        history = pending.get("history")
        model = str(pending.get("model", self._default_model))

        workspace_entity_id = str(args.get("workspace_entity_id", "")).strip()
        if workspace_entity_id:
            entity_type = str(args.get("workspace_entity_type", "entity"))
            entity_title = str(args.get("workspace_entity_title", workspace_entity_id))
            graph_snippets.insert(
                0,
                f"Workspace {entity_type}: {entity_title} (entity_id={workspace_entity_id})",
            )

        bundle = self._context_manager.build_context(
            query,
            clipboard=clipboard_text,
            notes=notes or None,
            graph_snippets=graph_snippets or None,
            conversation_history=history if isinstance(history, list) else None,
            clipboard_intent=clip_intent,
        )
        budget = self._context_manager.context_budget_tokens
        self._bus.publish(
            CONTEXT_SNAPSHOT_CREATED,
            {
                "context_size_tokens": bundle.token_estimate,
                "sources": list(bundle.sources),
                "budget_tokens": budget,
            },
            source=self.name,
        )
        if bundle.token_estimate >= budget:
            self._bus.publish(
                CONTEXT_OVER_BUDGET,
                {
                    "context_size_tokens": bundle.token_estimate,
                    "budget_tokens": budget,
                },
                source=self.name,
            )
        if "conversation_summary" in bundle.sources:
            self._bus.publish(
                CONTEXT_TRIMMED,
                {"reason": "history_compression", "sources": list(bundle.sources)},
                source=self.name,
            )
        elif bundle.prompt.rstrip().endswith("..."):
            self._bus.publish(
                CONTEXT_TRIMMED,
                {"reason": "query_truncated", "sources": list(bundle.sources)},
                source=self.name,
            )
        if not bundle.prompt:
            self._bus.publish(
                CHAT_ERROR,
                {"message": "Empty prompt after context assembly"},
                source=self.name,
            )
            return

        warning = model_warning(model)
        if warning:
            self._bus.publish(
                APP_WARNING,
                {"message": warning, "model": model},
                source=self.name,
            )

        self._bus.publish(
            COMMAND_ROUTED,
            {
                **event.payload,
                "status": "processing",
                "request_id": request_id,
                "context_sources": list(bundle.sources),
                "token_estimate": bundle.token_estimate,
            },
            source=self.name,
        )

        self._bus.publish(
            SESSION_UPDATE_REQUEST,
            {"request_id": request_id, "role": "user", "content": query},
            source=self.name,
        )

        self._bus.publish(
            LLM_REQUEST,
            {
                "request_id": request_id,
                "model": model,
                "provider": self._provider,
                "bundle": bundle,
            },
            source=self.name,
        )
        self._pending.pop(request_id, None)


