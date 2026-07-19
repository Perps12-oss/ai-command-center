"""ARI capability classification helpers and settings tracking.

No longer races on COMMAND_ROUTED. External capability dispatch is invoked only
via CAPABILITY_RUNTIME_REQUEST from ExecutionOrchestratorService.
"""

from __future__ import annotations

from collections.abc import Callable

from ai_command_center.core.capability_context_assembler import CapabilityContextAssembler
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import SETTINGS_SNAPSHOT
from ai_command_center.domain.capability_provider_settings import (
    capability_provider_map_from_payload,
    resolve_capability_provider,
)
from ai_command_center.domain.runtime_capability import CapabilityKind
from ai_command_center.runtime.provider_registry import RuntimeProviderRegistry
from ai_command_center.services.base import BaseService

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
    "agenda",
)

_CODING_HINTS: tuple[str, ...] = (
    "write code",
    "implement ",
    "refactor ",
    "fix this bug",
    "pull request",
)


class RuntimeCapabilityRouterService(BaseService):
    """Capability kind classifier + provider map (no COMMAND_ROUTED intake)."""

    name = "runtime_capability_router"

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
        self._user_provider_map: dict[str, str] = {}
        self._context_manager = context_manager or ContextManager()
        self._assembler = context_assembler or CapabilityContextAssembler(
            bus,
            self._context_manager,
            obsidian=obsidian,
        )

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(SETTINGS_SNAPSHOT, self._on_settings_snapshot)
        )

    def _on_settings_snapshot(self, event: Event) -> None:
        self._user_provider_map = capability_provider_map_from_payload(event.payload)

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
        return resolve_capability_provider(kind, self._user_provider_map)
