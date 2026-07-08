"""Routes chat intents through ContextManager before LLM dispatch (Phase 3A).

Context assembly is delegated to ``CapabilityContextAssembler`` (shared with
``RuntimeCapabilityRouterService`` for external invoke). See that module for the sync
bus cascade contract.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from ai_command_center.core.capability_context_assembler import CapabilityContextAssembler
from ai_command_center.core.capability_external_registry import is_externally_handled
from ai_command_center.orchestration.orchestration_registry import is_orchestration_handled
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
    CONTEXT_COMPLETE,
    CONTEXT_OVER_BUDGET,
    CONTEXT_SNAPSHOT_CREATED,
    CONTEXT_TRIMMED,
    LLM_REQUEST,
    SESSION_UPDATE_REQUEST,
    SETTINGS_SNAPSHOT,
)
from ai_command_center.platform.model_registry import model_warning
from ai_command_center.services.base import BaseService
from ai_command_center.core.events.intents import INTENT_CHAT

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
        *,
        context_assembler: CapabilityContextAssembler | None = None,
    ) -> None:
        super().__init__(bus)
        self._context_manager = context_manager
        self._obsidian = obsidian
        self._session = session
        self._default_model = "llama3.2:3b"
        self._provider = "ollama"
        self._assembler = context_assembler or CapabilityContextAssembler(
            bus,
            context_manager,
            obsidian=obsidian,
        )
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(self._bus.subscribe(COMMAND_ROUTED, self._on_command_routed))
        self._unsubscribers.append(self._bus.subscribe(SETTINGS_SNAPSHOT, self._on_settings_snapshot))

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_settings_snapshot(self, event: Event) -> None:
        self._default_model = str(
            event.payload.get("default_model", self._default_model)
        )
        self._provider = str(event.payload.get("provider", self._provider)).strip() or "ollama"
        self._assembler._default_model = self._default_model
        self._assembler._default_provider = self._provider

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

        request_id = str(event.payload.get("request_id") or "").strip() or uuid.uuid4().hex
        if is_orchestration_handled(request_id):
            logger.info(
                "chat.deferred_orchestration request_id=%s",
                request_id,
            )
            return
        if is_externally_handled(request_id):
            logger.info(
                "chat.deferred_external request_id=%s provider=non-native",
                request_id,
            )
            # Full auto-fallback after a failed external invoke (post sidecar error)
            # is deferred: sidecar publishes CHAT_ERROR and clears the external mark,
            # but this handler does not re-run. Pre-invoke fallback uses CAPABILITY_FALLBACK
            # without marking external, so native assembly proceeds on the same bus turn.
            return

        logger.info("chat.request_started request_id=%s query_len=%d", request_id, len(query))

        assembled = self._assembler.assemble_for_command(
            request_id=request_id,
            query=query,
            event_payload=dict(event.payload),
            args=dict(args),
            source=self.name,
            include_model_resolve=True,
            clipboard=clipboard_text,
        )
        bundle = assembled.bundle
        session_scope = assembled.session_scope
        model = assembled.model
        provider = assembled.provider

        budget = self._context_manager.context_budget_tokens
        workspace_id = str(session_scope.get("workspace_id", "")).strip()
        self._bus.publish(
            CONTEXT_SNAPSHOT_CREATED,
            {
                "context_size_tokens": bundle.token_estimate,
                "sources": list(bundle.sources),
                "budget_tokens": budget,
                "workspace_id": workspace_id,
                "workspace_context_snippets": list(assembled.workspace_context_snippets),
            },
            source=self.name,
        )
        if assembled.workspace_context_snippets:
            self._bus.publish(
                CONTEXT_COMPLETE,
                {
                    "request_id": request_id,
                    "workspace_id": workspace_id,
                    "snippet_count": len(assembled.workspace_context_snippets),
                    "workspace_context_snippets": list(
                        assembled.workspace_context_snippets
                    ),
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
            {
                "request_id": request_id,
                "role": "user",
                "content": query,
                **session_scope,
            },
            source=self.name,
        )

        self._bus.publish(
            LLM_REQUEST,
            {
                "request_id": request_id,
                "model": model,
                "provider": provider,
                "bundle": bundle,
            },
            source=self.name,
        )
