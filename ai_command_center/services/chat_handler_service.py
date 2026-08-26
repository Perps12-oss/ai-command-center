"""Routes llm capability steps through ContextManager before LLM dispatch.

ChatHandlerService is a capability handler only. It must not own user intake —
ExecutionAuthority + ExecutionOrchestrator invoke it via LLM_STEP_REQUEST when
a PlanStep has capability=\"llm\"/\"chat\".
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from ai_command_center.core.capability_context_assembler import CapabilityContextAssembler
from ai_command_center.core.clipboard_intent import (
    empty_clipboard_message,
    wants_clipboard,
)
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    APP_WARNING,
    CAPABILITY_COMPLETE,
    CAPABILITY_ERROR,
    CAPABILITY_PROVIDERS_READY,
    CHAT_COMPLETE,
    CHAT_ERROR,
    CONTEXT_COMPLETE,
    CONTEXT_OVER_BUDGET,
    CONTEXT_SNAPSHOT_CREATED,
    CONTEXT_TRIMMED,
    LLM_REQUEST,
    LLM_STEP_REQUEST,
    OLLAMA_STATUS,
    OPENAI_STATUS,
    ORCHESTRATION_PROVIDER_HEALTH,
    SESSION_UPDATE_REQUEST,
    SETTINGS_SNAPSHOT,
)
from ai_command_center.providers.defaults import provider_display_name
from ai_command_center.platform.model_registry import model_warning
from ai_command_center.services.base import BaseService

logger = logging.getLogger(__name__)

_LLM_CAPABILITIES = frozenset({"llm", "chat"})
_SETUP_LABELS = {
    "ollama": "Ollama",
    "openai": "OpenAI",
}


class ChatHandlerService(BaseService):
    """
    Handles llm/chat PlanSteps only.

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
        self._pending_steps: dict[str, dict[str, str]] = {}
        self._provider_health: dict[str, tuple[bool, str]] = {}

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(LLM_STEP_REQUEST, self._on_llm_step_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(SETTINGS_SNAPSHOT, self._on_settings_snapshot)
        )
        self._unsubscribers.append(
            self._bus.subscribe(CHAT_COMPLETE, self._on_chat_complete)
        )
        self._unsubscribers.append(
            self._bus.subscribe(CHAT_ERROR, self._on_chat_error)
        )
        self._unsubscribers.append(
            self._bus.subscribe(OLLAMA_STATUS, self._on_ollama_status)
        )
        self._unsubscribers.append(
            self._bus.subscribe(OPENAI_STATUS, self._on_openai_status)
        )
        self._unsubscribers.append(
            self._bus.subscribe(CAPABILITY_PROVIDERS_READY, self._on_capability_providers_ready)
        )
        self._unsubscribers.append(
            self._bus.subscribe(ORCHESTRATION_PROVIDER_HEALTH, self._on_orchestration_provider_health)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._pending_steps.clear()
        self._provider_health.clear()

    def _on_settings_snapshot(self, event: Event) -> None:
        self._default_model = str(
            event.payload.get("default_model", self._default_model)
        )
        self._provider = str(event.payload.get("provider", self._provider)).strip() or "ollama"
        self._assembler._default_model = self._default_model
        self._assembler._default_provider = self._provider

    def _on_ollama_status(self, event: Event) -> None:
        online = bool(event.payload.get("online", False))
        detail = str(event.payload.get("detail", "")).strip()
        self._provider_health["ollama"] = (online, detail)

    def _on_openai_status(self, event: Event) -> None:
        online = bool(event.payload.get("online", False))
        detail = str(event.payload.get("detail", "")).strip()
        self._provider_health["openai"] = (online, detail)

    def _on_capability_providers_ready(self, event: Event) -> None:
        for item in event.payload.get("providers") or []:
            if not isinstance(item, dict):
                continue
            provider_id = str(item.get("id", "")).strip()
            if not provider_id:
                continue
            health_raw = str(item.get("health_state", "")).strip().lower()
            healthy = health_raw in {"ready", "healthy"}
            detail = str(item.get("health_detail", "")).strip()
            self._provider_health[provider_id] = (healthy, detail)

    def _on_orchestration_provider_health(self, event: Event) -> None:
        provider_id = str(event.payload.get("provider_id", "")).strip()
        if not provider_id:
            return
        healthy = bool(event.payload.get("healthy", False))
        detail = str(event.payload.get("detail", "")).strip()
        self._provider_health[provider_id] = (healthy, detail)

    def _provider_ready(self, provider: str) -> tuple[bool, str]:
        key = provider.strip().lower()
        status = self._provider_health.get(key)
        if status is None:
            return False, "provider status unknown"
        return status

    def _provider_unavailable_message(self, provider: str, detail: str) -> str:
        display = provider_display_name(provider)
        setup_label = _SETUP_LABELS.get(provider.strip().lower(), display)
        detail_text = detail.strip()
        detail_line = f" {display} isn't available ({detail_text})." if detail_text else f" {display} isn't available."
        return (
            f"I need an AI provider to answer that.{detail_line}\n\n"
            f"[Set up {setup_label}] Open Settings > Providers (or run: settings)."
        )

    def _on_llm_step_request(self, event: Event) -> None:
        capability = str(event.payload.get("capability", "llm")).strip().lower()
        if capability and capability not in _LLM_CAPABILITIES:
            return

        args = event.payload.get("args") or {}
        query = str(
            args.get("prompt") or event.payload.get("prompt") or ""
        ).strip()
        if not query:
            self._fail_step(
                event,
                "empty prompt for llm capability step",
            )
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
            self._fail_step(event, empty_clipboard_message())
            return

        request_id = str(event.payload.get("request_id") or "").strip() or uuid.uuid4().hex
        run_id = str(event.payload.get("run_id", "")).strip()
        step_id = str(event.payload.get("step_id", "")).strip()
        if run_id and step_id:
            self._pending_steps[request_id] = {
                "run_id": run_id,
                "step_id": step_id,
            }

        provider_ready, provider_detail = self._provider_ready(self._provider)
        if not provider_ready:
            self._bus.publish(
                CAPABILITY_COMPLETE,
                {
                    "request_id": request_id,
                    "run_id": run_id,
                    "step_id": step_id,
                    "output": self._provider_unavailable_message(
                        self._provider,
                        provider_detail,
                    ),
                    "capability": "llm",
                },
                source=self.name,
            )
            return

        logger.info(
            "chat.llm_step_started request_id=%s run_id=%s step_id=%s query_len=%d",
            request_id,
            run_id,
            step_id,
            len(query),
        )

        event_payload = dict(event.payload.get("command_payload") or event.payload)
        assembled = self._assembler.assemble_for_command(
            request_id=request_id,
            query=query,
            event_payload=event_payload,
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
            self._fail_step(event, "Empty prompt after context assembly")
            return

        warning = model_warning(model)
        if warning:
            self._bus.publish(
                APP_WARNING,
                {"message": warning, "model": model},
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
                "run_id": run_id,
                "step_id": step_id,
                "capability": "llm",
            },
            source=self.name,
        )

    def _on_chat_complete(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id", "")).strip()
        pending = self._pending_steps.pop(request_id, None)
        if pending is None:
            return
        # Skip orchestration-styled completions that are not llm capability steps.
        if event.payload.get("orchestration") and not event.payload.get("capability"):
            self._pending_steps[request_id] = pending
            return
        self._bus.publish(
            CAPABILITY_COMPLETE,
            {
                "request_id": request_id,
                "run_id": pending["run_id"],
                "step_id": pending["step_id"],
                "output": str(event.payload.get("text", "")),
                "capability": "llm",
            },
            source=self.name,
        )

    def _on_chat_error(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id", "")).strip()
        pending = self._pending_steps.pop(request_id, None)
        if pending is None:
            return
        self._bus.publish(
            CAPABILITY_ERROR,
            {
                "request_id": request_id,
                "run_id": pending["run_id"],
                "step_id": pending["step_id"],
                "message": str(event.payload.get("message") or "llm step failed"),
                "capability": "llm",
            },
            source=self.name,
        )

    def _fail_step(self, event: Event, message: str) -> None:
        run_id = str(event.payload.get("run_id", "")).strip()
        step_id = str(event.payload.get("step_id", "")).strip()
        request_id = str(event.payload.get("request_id", "")).strip()
        if request_id:
            self._pending_steps.pop(request_id, None)
        if not run_id or not step_id:
            return
        self._bus.publish(
            CAPABILITY_ERROR,
            {
                "request_id": request_id,
                "run_id": run_id,
                "step_id": step_id,
                "message": message,
                "capability": "llm",
            },
            source=self.name,
        )
