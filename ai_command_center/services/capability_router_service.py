"""Routes command.routed chat intents to capability kinds and runtime providers."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from ai_command_center.core.capability_context_assembler import (
    CapabilityContextAssembler,
    context_bundle_to_dict,
)
from ai_command_center.core.capability_external_registry import (
    clear_external_request,
    mark_external_request,
)
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    CAPABILITY_CLASSIFIED,
    CAPABILITY_DISPATCH,
    CAPABILITY_FALLBACK,
    CHAT_ERROR,
    COMMAND_ROUTED,
    CONTEXT_SNAPSHOT_CREATED,
    TELEMETRY_EVENT,
)
from ai_command_center.domain.runtime_capability import (
    CapabilityKind,
    ProviderHealthState,
    RuntimeInvocationRequest,
)
from ai_command_center.runtime.provider_registry import RuntimeProviderRegistry
from ai_command_center.services.base import BaseService

_logger = logging.getLogger(__name__)

_PREFIX_KIND: dict[str, CapabilityKind] = {
    "/plan": CapabilityKind.PLANNING,
    "/code": CapabilityKind.CODING,
    "/research": CapabilityKind.RESEARCH,
    "/agent": CapabilityKind.AGENTS,
    "/memory": CapabilityKind.MEMORY,
}

_PLANNING_HINTS: tuple[str, ...] = (
    "plan my",
    "schedule",
    "calendar",
    "agenda",
    "what's on my calendar",
    "whats on my calendar",
)

_CODING_HINTS: tuple[str, ...] = (
    "write code",
    "implement ",
    "refactor ",
    "fix this bug",
    "pull request",
)

_DEFAULT_PROVIDER_MAP: dict[CapabilityKind, str] = {
    CapabilityKind.CHAT: "native",
    CapabilityKind.PLANNING: "qwenpaw",
    CapabilityKind.CODING: "qwenpaw",
    CapabilityKind.RESEARCH: "native",
    CapabilityKind.AUTOMATION: "native",
    CapabilityKind.AGENTS: "native",
    CapabilityKind.MEMORY: "native",
}


class CapabilityRouterService(BaseService):
    """Classifies capabilities and dispatches to ARI providers (Invariant 13)."""

    name = "capability_router"

    def __init__(
        self,
        bus,
        *,
        provider_registry: RuntimeProviderRegistry | None = None,
        context_manager: ContextManager | None = None,
        context_assembler: CapabilityContextAssembler | None = None,
        obsidian=None,
    ) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []
        self._registry = provider_registry or RuntimeProviderRegistry()
        self._provider_map = dict(_DEFAULT_PROVIDER_MAP)
        self._context_manager = context_manager or ContextManager()
        self._assembler = context_assembler or CapabilityContextAssembler(
            bus,
            self._context_manager,
            obsidian=obsidian,
        )

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(COMMAND_ROUTED, self._on_command_routed)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    @staticmethod
    def classify(text: str) -> CapabilityKind:
        normalized = text.strip()
        lower = normalized.lower()
        for prefix, kind in _PREFIX_KIND.items():
            if lower.startswith(prefix):
                return kind
        if any(hint in lower for hint in _PLANNING_HINTS):
            return CapabilityKind.PLANNING
        if any(hint in lower for hint in _CODING_HINTS):
            return CapabilityKind.CODING
        return CapabilityKind.CHAT

    def resolve_provider(self, kind: CapabilityKind) -> str:
        return self._provider_map.get(kind, "native")

    def _on_command_routed(self, event: Event) -> None:
        if event.source != "command_router":
            return
        if event.payload.get("intent") != INTENT_CHAT:
            return
        args = event.payload.get("args") or {}
        query = str(args.get("prompt", "")).strip()
        if not query:
            return

        kind = self.classify(query)
        provider_id = self.resolve_provider(kind)
        request_id = str(event.payload.get("request_id") or uuid.uuid4().hex)

        self._bus.publish(
            CAPABILITY_CLASSIFIED,
            {
                "request_id": request_id,
                "kind": kind.value,
                "provider_id": provider_id,
                "query": query,
            },
            source=self.name,
        )

        dispatch_payload = {
            "request_id": request_id,
            "kind": kind.value,
            "provider_id": provider_id,
            "fallback_provider_id": "native",
            "query": query,
            "command_routed": dict(event.payload),
        }
        self._bus.publish(CAPABILITY_DISPATCH, dispatch_payload, source=self.name)

        if provider_id == "native":
            return

        provider = self._registry.resolve_for_kind(kind, provider_id)
        if provider is None:
            self._emit_fallback(request_id, kind, provider_id, "provider not registered")
            return

        health = provider.health()
        if health.state != ProviderHealthState.READY:
            self._emit_fallback(
                request_id,
                kind,
                provider_id,
                health.detail or f"{provider_id} {health.state.value}",
            )
            return

        assembled = self._assembler.assemble_for_command(
            request_id=request_id,
            query=query,
            event_payload=dict(event.payload),
            args=dict(args),
            source=self.name,
            include_model_resolve=False,
        )
        bundle = assembled.bundle
        budget = self._context_manager.context_budget_tokens
        self._bus.publish(
            CONTEXT_SNAPSHOT_CREATED,
            {
                "request_id": request_id,
                "context_size_tokens": bundle.token_estimate,
                "sources": list(bundle.sources),
                "budget_tokens": budget,
                "provider_id": provider_id,
            },
            source=self.name,
        )
        if not bundle.prompt:
            message = "Empty prompt after context assembly"
            self._bus.publish(
                CHAT_ERROR,
                {"message": message, "request_id": request_id},
                source=self.name,
            )
            self._emit_fallback(request_id, kind, provider_id, message)
            return

        workspace_id = str(event.payload.get("workspace_id") or args.get("workspace_id", "")).strip()
        workspace_entity_id = str(
            event.payload.get("workspace_entity_id") or args.get("workspace_entity_id", "")
        ).strip()
        session_id = str(event.payload.get("session_id") or args.get("session_id", "")).strip()
        invocation = RuntimeInvocationRequest(
            request_id=request_id,
            kind=kind,
            provider_id=provider_id,
            query=query,
            workspace_id=workspace_id,
            workspace_entity_id=workspace_entity_id,
            session_id=session_id,
            context_bundle=context_bundle_to_dict(bundle),
        )
        mark_external_request(request_id)
        provider.invoke(invocation)

    def _emit_fallback(
        self,
        request_id: str,
        kind: CapabilityKind,
        provider_id: str,
        reason: str,
    ) -> None:
        _logger.info(
            "capability.fallback request_id=%s kind=%s provider=%s reason=%s",
            request_id,
            kind.value,
            provider_id,
            reason,
        )
        self._bus.publish(
            CAPABILITY_FALLBACK,
            {
                "request_id": request_id,
                "kind": kind.value,
                "provider_id": provider_id,
                "fallback_provider_id": "native",
                "reason": reason,
            },
            source=self.name,
        )
        clear_external_request(request_id)
        # Pre-invoke fallback: external mark was never set (or cleared above), so
        # ChatHandler on the same COMMAND_ROUTED turn proceeds with native LLM.
        # Post-invoke failure: sidecar publishes CHAT_ERROR; native re-run is deferred.
        self._bus.publish(
            TELEMETRY_EVENT,
            {
                "name": "capability.fallback",
                "request_id": request_id,
                "kind": kind.value,
                "provider_id": provider_id,
                "reason": reason,
            },
            source=self.name,
        )
