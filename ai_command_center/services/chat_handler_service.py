"""Routes chat intents through ContextManager before Ollama (Phase 3A skeleton)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Callable

from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import Event
from ai_command_center.platform.model_registry import model_warning
from ai_command_center.services.base import BaseService
from ai_command_center.services.command_router_service import INTENT_CHAT
from ai_command_center.services.ollama_service import OllamaServiceBase

if TYPE_CHECKING:
    from ai_command_center.services.obsidian_service import ObsidianService
    from ai_command_center.services.session_service import SessionService


class ChatHandlerService(BaseService):
    """
    Handles command.routed intents for chat.

    Every AI request MUST pass through ContextManager.build_context() first.
  Phase 3B adds real streaming; Phase 3C adds note injection; Phase 3D adds history.
    """

    name = "chat_handler"

    def __init__(
        self,
        bus,
        context_manager: ContextManager,
        ollama: OllamaServiceBase,
        obsidian: ObsidianService | None = None,
        session: SessionService | None = None,
    ) -> None:
        super().__init__(bus)
        self._context_manager = context_manager
        self._ollama = ollama
        self._obsidian = obsidian
        self._session = session
        self._default_model = "llama3.2:3b"
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe("command.routed", self._on_command_routed)
        )
        self._unsubscribers.append(
            self._bus.subscribe("settings.snapshot", self._on_settings_snapshot)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_settings_snapshot(self, event: Event) -> None:
        self._default_model = str(
            event.payload.get("default_model", self._default_model)
        )

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

        notes_raw = args.get("notes")
        notes: list[str] = []
        if isinstance(notes_raw, list):
            notes = [str(n) for n in notes_raw if str(n).strip()]
        if self._obsidian is not None:
            notes.extend(self._obsidian.get_context_notes())

        history: list[tuple[str, str]] | None = None
        if self._session is not None:
            history = self._session.get_context_history()

        bundle = self._context_manager.build_context(
            query,
            clipboard=clipboard_text,
            notes=notes or None,
            conversation_history=history,
        )
        if not bundle.prompt:
            self._bus.publish(
                "chat.error",
                {"message": "Empty prompt after context assembly"},
                source=self.name,
            )
            return

        model = self._default_model
        warning = model_warning(model)
        if warning:
            self._bus.publish(
                "app.warning",
                {"message": warning, "model": model},
                source=self.name,
            )

        request_id = uuid.uuid4().hex
        self._bus.publish(
            "command.routed",
            {
                **event.payload,
                "status": "processing",
                "request_id": request_id,
                "context_sources": list(bundle.sources),
                "token_estimate": bundle.token_estimate,
            },
            source=self.name,
        )

        if self._session is not None:
            self._session.append_user_message(query)

        try:
            self._ollama.stream_chat(bundle, model=model, request_id=request_id)
        except Exception as exc:
            self._bus.publish(
                "chat.error",
                {
                    "request_id": request_id,
                    "message": str(exc),
                },
                source=self.name,
            )
            self._bus.publish(
                "app.error",
                {"message": f"Chat failed: {exc}"},
                source=self.name,
            )
