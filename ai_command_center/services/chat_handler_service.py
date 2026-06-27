"""Routes chat intents through ContextManager before Ollama (Phase 3A skeleton)."""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ai_command_center.core.clipboard_intent import (
    empty_clipboard_message,
    wants_clipboard,
)
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    APP_ERROR,
    APP_WARNING,
    CHAT_CANCELLED,
    CHAT_ERROR,
    COMMAND_ROUTED,
    CONTEXT_OVER_BUDGET,
    CONTEXT_SNAPSHOT_CREATED,
    CONTEXT_TRIMMED,
    MEMORY_LOOKUP_REQUEST,
    MEMORY_LOOKUP_RESULT,
    MODEL_RESOLVE_REQUEST,
    MODEL_RESOLVE_RESULT,
    NOTE_CONTEXT_REQUEST,
    NOTE_CONTEXT_RESULT,
    SESSION_HISTORY_REQUEST,
    SESSION_HISTORY_RESULT,
    SESSION_UPDATE_REQUEST,
    SETTINGS_SNAPSHOT,
    UI_CHAT_CANCEL,
)
from ai_command_center.platform.model_registry import model_warning
from ai_command_center.services.base import BaseService
from ai_command_center.services.command_router_service import INTENT_CHAT

if TYPE_CHECKING:
    from ai_command_center.services.ollama_service import OllamaServiceBase


@dataclass
class _ChatRequest:
    """Mutable request state used by ChatHandlerService to coordinate upstream results."""

    request_id: str
    query: str
    clipboard: str | None
    notes: list[str]
    clip_intent: bool
    event_payload: dict[str, object]
    model: str | None = None
    graph_snippets: list[str] = field(default_factory=list)
    history: list[tuple[str, str]] | None = None
    memory_ready: bool = False
    history_ready: bool = False
    model_ready: bool = False
    started: bool = False
    cancelled: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


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
        ollama: OllamaServiceBase,
        obsidian=None,
        session=None,
        upstream_timeout_seconds: float = 0.0,
    ) -> None:
        super().__init__(bus)
        self._context_manager = context_manager
        self._ollama = ollama
        self._obsidian = obsidian
        self._session = session
        self._default_model = "llama3.2:3b"
        self._upstream_timeout = upstream_timeout_seconds
        self._unsubscribers: list[Callable[[], None]] = []
        self._requests: dict[str, _ChatRequest] = {}

    def _on_load(self) -> None:
        self._unsubscribers.append(self._bus.subscribe(COMMAND_ROUTED, self._on_command_routed))
        self._unsubscribers.append(self._bus.subscribe(SETTINGS_SNAPSHOT, self._on_settings_snapshot))
        self._unsubscribers.append(self._bus.subscribe(NOTE_CONTEXT_RESULT, self._on_note_context_result))
        self._unsubscribers.append(self._bus.subscribe(MEMORY_LOOKUP_RESULT, self._on_memory_lookup_result))
        self._unsubscribers.append(self._bus.subscribe(SESSION_HISTORY_RESULT, self._on_session_history_result))
        self._unsubscribers.append(self._bus.subscribe(MODEL_RESOLVE_RESULT, self._on_model_resolve_result))
        self._unsubscribers.append(self._bus.subscribe(UI_CHAT_CANCEL, self._on_chat_cancel))

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._requests.clear()

    def _on_settings_snapshot(self, event: Event) -> None:
        self._default_model = str(
            event.payload.get("default_model", self._default_model)
        )

    def _publish_request(self, topic: str, request_id: str, payload: dict[str, object]) -> None:
        self._bus.publish(topic, {"request_id": request_id, **payload}, source=self.name)

    def _on_note_context_result(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id", ""))
        req = self._requests.get(request_id)
        if not req:
            return
        with req.lock:
            req.notes = list(event.payload.get("notes", []))

    def _on_memory_lookup_result(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id", ""))
        req = self._requests.get(request_id)
        if not req:
            return
        with req.lock:
            req.graph_snippets = list(event.payload.get("snippets", []))
            req.memory_ready = True
        self._try_start_stream(request_id)

    def _on_session_history_result(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id", ""))
        req = self._requests.get(request_id)
        if not req:
            return
        with req.lock:
            req.history = list(event.payload.get("history", []))
            req.history_ready = True
        self._try_start_stream(request_id)

    def _on_model_resolve_result(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id", ""))
        req = self._requests.get(request_id)
        if not req:
            return
        with req.lock:
            req.model = str(event.payload.get("model", self._default_model))
            req.model_ready = True
        self._try_start_stream(request_id)

    def _on_chat_cancel(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id", ""))
        if not request_id:
            # Cancel the most recent not-yet-started pending request.
            for rid, req in self._requests.items():
                with req.lock:
                    if not req.started and not req.cancelled:
                        request_id = rid
                        break
        if not request_id:
            return
        req = self._requests.get(request_id)
        if not req:
            return
        with req.lock:
            if req.started:
                return
            req.cancelled = True
        self._requests.pop(request_id, None)
        self._bus.publish(
            CHAT_CANCELLED,
            {"request_id": request_id},
            source=self.name,
        )

    def _try_start_stream(self, request_id: str) -> None:
        req = self._requests.get(request_id)
        if not req:
            return
        with req.lock:
            if req.started or req.cancelled:
                return
            if not (req.memory_ready and req.history_ready and req.model_ready):
                return
            req.started = True
        self._start_stream(req)

    def _wait_and_start(self, request_id: str) -> None:
        time.sleep(self._upstream_timeout)
        req = self._requests.get(request_id)
        if not req:
            return
        with req.lock:
            if req.started or req.cancelled:
                return
            req.started = True
        self._start_stream(req)

    def _on_command_routed(self, event: Event) -> None:
        if event.payload.get("intent") != INTENT_CHAT:
            return
        if event.source != "command_router":
            return

        args = event.payload.get("args") or {}
        query = str(args.get("prompt", "")).strip()
        if not query:
            return

        request_id = uuid.uuid4().hex

        clipboard = args.get("clipboard")
        clipboard_text = str(clipboard).strip() if clipboard else None
        if clipboard_text == "":
            clipboard_text = None

        clip_intent = wants_clipboard(query)
        if clip_intent and not clipboard_text:
            self._bus.publish(
                CHAT_ERROR,
                {"request_id": request_id, "message": empty_clipboard_message()},
                source=self.name,
            )
            return

        notes_raw = args.get("notes")
        notes: list[str] = []
        if isinstance(notes_raw, list):
            notes = [str(n) for n in notes_raw if str(n).strip()]
        if self._obsidian is not None:
            notes.extend(str(n) for n in self._obsidian.get_context_notes() if str(n).strip())

        req = _ChatRequest(
            request_id=request_id,
            query=query,
            clipboard=clipboard_text,
            notes=notes,
            clip_intent=clip_intent,
            event_payload=dict(event.payload),
        )
        self._requests[request_id] = req

        self._publish_request(MEMORY_LOOKUP_REQUEST, request_id, {"query": query})
        self._publish_request(SESSION_HISTORY_REQUEST, request_id, {})
        self._publish_request(MODEL_RESOLVE_REQUEST, request_id, {"intent": INTENT_CHAT, "query": query})

        self._try_start_stream(request_id)
        with req.lock:
            already_started = req.started
            already_cancelled = req.cancelled
        if not already_started and not already_cancelled:
            if self._upstream_timeout <= 0:
                self._wait_and_start(request_id)
            else:
                threading.Thread(
                    target=self._wait_and_start,
                    args=(request_id,),
                    daemon=True,
                ).start()

    def _start_stream(self, req: _ChatRequest) -> None:
        try:
            model = req.model or self._default_model
            graph_snippets = [str(n) for n in req.graph_snippets if str(n).strip()]
            history = req.history

            bundle = self._context_manager.build_context(
                req.query,
                clipboard=req.clipboard,
                notes=req.notes or None,
                graph_snippets=graph_snippets or None,
                conversation_history=history if isinstance(history, list) else None,
                clipboard_intent=req.clip_intent,
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
                    {"request_id": req.request_id, "message": "Empty prompt after context assembly"},
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
                    **req.event_payload,
                    "status": "processing",
                    "request_id": req.request_id,
                    "context_sources": list(bundle.sources),
                    "token_estimate": bundle.token_estimate,
                },
                source=self.name,
            )

            self._bus.publish(
                SESSION_UPDATE_REQUEST,
                {"request_id": req.request_id, "role": "user", "content": req.query},
                source=self.name,
            )

            try:
                self._ollama.stream_chat(
                    bundle,
                    model=model,
                    request_id=req.request_id,
                )
            except Exception as exc:
                self._bus.publish(
                    CHAT_ERROR,
                    {
                        "request_id": req.request_id,
                        "message": str(exc),
                    },
                    source=self.name,
                )
                self._bus.publish(
                    APP_ERROR,
                    {"message": f"Chat failed: {exc}"},
                    source=self.name,
                )
        finally:
            self._requests.pop(req.request_id, None)


