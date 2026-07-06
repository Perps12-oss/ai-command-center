"""Shared sync-bus context assembly for chat and external capability invoke.

Sync cascade contract: ``assemble_for_command`` publishes ``MEMORY_LOOKUP_REQUEST``,
``SESSION_HISTORY_REQUEST``, optional ``MODEL_RESOLVE_REQUEST``, and
``ENTITY_CONTEXT_REQUEST`` synchronously. Handlers for those topics must populate
results before ``publish`` returns so assembly can read notes, history, model,
and entity scope inline. Do not defer those lookups without changing this contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_command_center.core.clipboard_intent import wants_clipboard
from ai_command_center.core.context_manager import ContextBundle, ContextManager
from ai_command_center.core.entity.entity_context import format_entity_context
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    ENTITY_CONTEXT_REQUEST,
    ENTITY_CONTEXT_RESULT,
    MEMORY_LOOKUP_REQUEST,
    MEMORY_LOOKUP_RESULT,
    MODEL_RESOLVE_REQUEST,
    MODEL_RESOLVE_RESULT,
    SESSION_HISTORY_REQUEST,
    SESSION_HISTORY_RESULT,
)


@dataclass(frozen=True, slots=True)
class AssembledContext:
    """Context bundle plus optional model resolution metadata."""

    bundle: ContextBundle
    session_scope: dict[str, str]
    model: str
    provider: str


def context_bundle_to_dict(bundle: ContextBundle) -> dict[str, object]:
    """Serialize a ContextBundle for RuntimeInvocationRequest payloads."""
    return {
        "prompt": bundle.prompt,
        "sources": list(bundle.sources),
        "token_estimate": bundle.token_estimate,
        "version": bundle.version,
    }


class CapabilityContextAssembler:
    """Builds ContextBundle via synchronous EventBus cascade (Invariant 6)."""

    def __init__(
        self,
        bus: EventBus,
        context_manager: ContextManager,
        *,
        obsidian: Any | None = None,
        default_model: str = "llama3.2:3b",
        default_provider: str = "ollama",
    ) -> None:
        self._bus = bus
        self._context_manager = context_manager
        self._obsidian = obsidian
        self._default_model = default_model
        self._default_provider = default_provider

    @staticmethod
    def session_scope_from_payload(event_payload: dict, args: dict) -> dict[str, str]:
        scope: dict[str, str] = {}
        for key in (
            "workspace_entity_id",
            "workspace_entity_type",
            "workspace_entity_title",
            "workspace_entity_description",
            "workspace_entity_url",
            "workspace_entity_path",
        ):
            value = str(event_payload.get(key) or args.get(key, "")).strip()
            if value:
                scope[key] = value
        return scope

    def assemble_for_command(
        self,
        *,
        request_id: str,
        query: str,
        event_payload: dict[str, object],
        args: dict[str, object],
        source: str,
        include_model_resolve: bool = True,
        clipboard: str | None = None,
    ) -> AssembledContext:
        pending: dict[str, object] = {}

        def _on_memory_result(event) -> None:
            rid = str(event.payload.get("request_id", ""))
            if rid == request_id:
                pending["graph_snippets"] = list(event.payload.get("snippets", []))

        def _on_session_result(event) -> None:
            rid = str(event.payload.get("request_id", ""))
            if rid == request_id:
                pending["history"] = list(event.payload.get("history", []))

        def _on_model_result(event) -> None:
            rid = str(event.payload.get("request_id", ""))
            if rid == request_id:
                pending["model"] = str(event.payload.get("model", self._default_model))
                provider = str(event.payload.get("provider", "")).strip()
                if provider:
                    pending["provider"] = provider

        def _on_entity_result(event) -> None:
            rid = str(event.payload.get("request_id", ""))
            if rid == request_id:
                pending["entity_snippets"] = list(event.payload.get("snippets", []))

        unsubs = [
            self._bus.subscribe(MEMORY_LOOKUP_RESULT, _on_memory_result),
            self._bus.subscribe(SESSION_HISTORY_RESULT, _on_session_result),
            self._bus.subscribe(MODEL_RESOLVE_RESULT, _on_model_result),
            self._bus.subscribe(ENTITY_CONTEXT_RESULT, _on_entity_result),
        ]
        try:
            clip_intent = wants_clipboard(query)
            notes_raw = args.get("notes")
            notes: list[str] = []
            if isinstance(notes_raw, list):
                notes = [str(n) for n in notes_raw if str(n).strip()]
            if self._obsidian is not None:
                notes.extend(
                    str(n) for n in self._obsidian.get_context_notes() if str(n).strip()
                )

            session_scope = self.session_scope_from_payload(event_payload, args)
            memory_scope: dict[str, object] = {"query": query}
            workspace_id = str(
                event_payload.get("workspace_id") or args.get("workspace_id", "")
            ).strip()
            if workspace_id:
                memory_scope["workspace_id"] = workspace_id

            self._bus.publish(
                MEMORY_LOOKUP_REQUEST,
                {"request_id": request_id, **memory_scope},
                source=source,
            )
            self._bus.publish(
                SESSION_HISTORY_REQUEST,
                {"request_id": request_id, **session_scope},
                source=source,
            )
            if include_model_resolve:
                self._bus.publish(
                    MODEL_RESOLVE_REQUEST,
                    {
                        "request_id": request_id,
                        "intent": INTENT_CHAT,
                        "query": query,
                    },
                    source=source,
                )

            workspace_entity_id = str(
                event_payload.get("workspace_entity_id")
                or args.get("workspace_entity_id", "")
            ).strip()
            if workspace_entity_id:
                self._bus.publish(
                    ENTITY_CONTEXT_REQUEST,
                    {"request_id": request_id, "entity_id": workspace_entity_id},
                    source=source,
                )

            graph_snippets = [
                str(n) for n in pending.get("graph_snippets", []) if str(n).strip()
            ]
            entity_snippets = [
                str(n) for n in pending.get("entity_snippets", []) if str(n).strip()
            ]
            if entity_snippets:
                graph_snippets = entity_snippets + graph_snippets
            elif workspace_entity_id:
                fallback = format_entity_context(
                    {
                        "entity_id": workspace_entity_id,
                        "entity_type": str(
                            event_payload.get("workspace_entity_type")
                            or args.get("workspace_entity_type", "entity")
                        ),
                        "entity_title": str(
                            event_payload.get("workspace_entity_title")
                            or args.get("workspace_entity_title", workspace_entity_id)
                        ),
                        "entity_description": str(
                            event_payload.get("workspace_entity_description")
                            or args.get("workspace_entity_description", "")
                        ),
                        "url": str(
                            event_payload.get("workspace_entity_url")
                            or args.get("workspace_entity_url", "")
                        ),
                        "path": str(
                            event_payload.get("workspace_entity_path")
                            or args.get("workspace_entity_path", "")
                        ),
                    }
                )
                if fallback:
                    graph_snippets.insert(0, fallback)

            history = pending.get("history")
            model = str(pending.get("model", self._default_model))
            provider = str(pending.get("provider", self._default_provider))

            bundle = self._context_manager.build_context(
                query,
                clipboard=clipboard,
                notes=notes or None,
                graph_snippets=graph_snippets or None,
                conversation_history=history if isinstance(history, list) else None,
                clipboard_intent=clip_intent,
            )
            return AssembledContext(
                bundle=bundle,
                session_scope=session_scope,
                model=model,
                provider=provider,
            )
        finally:
            for unsub in unsubs:
                unsub()
