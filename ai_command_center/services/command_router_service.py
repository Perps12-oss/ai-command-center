"""Pure command classifier library (workspace tracking only).

Decision-making for typed UI_COMMAND is owned by ExecutionAuthorityService.
Classification lives in ``core.command_classify`` — this service does not
publish decision events.
"""

from __future__ import annotations

from typing import Callable

from ai_command_center.core.command_classify import classify_command
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.intents import INTENT_NAVIGATE
from ai_command_center.core.events.topics import (
    WORKSPACE_ACTIVE,
    WORKSPACE_DEACTIVATED,
)
from ai_command_center.services.base import BaseService

# Navigation may proceed without an active workspace (soft gate).
_WORKSPACE_OPTIONAL_INTENTS: frozenset[str] = frozenset({INTENT_NAVIGATE})


class CommandRouterService(BaseService):
    """
    Workspace tracker + classify() facade.

    MUST NOT: subscribe to UI_COMMAND for decision-making, plan, orchestrate,
    or publish competing decision fan-out. ExecutionAuthority owns intake.
    """

    name = "command_router"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []
        self._active_workspace_id: str = ""

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_ACTIVE, self._on_workspace_active)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_DEACTIVATED, self._on_workspace_deactivated)
        )

    def _on_workspace_active(self, event: Event) -> None:
        self._active_workspace_id = str(event.payload.get("workspace_id", "")).strip()

    def _on_workspace_deactivated(self, event: Event) -> None:
        cleared = str(event.payload.get("workspace_id", "")).strip()
        if not cleared or cleared == self._active_workspace_id:
            self._active_workspace_id = ""

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    @staticmethod
    def classify(text: str) -> tuple[str, dict[str, str]]:
        """Prefix/keyword classification table (no LLM, no execution)."""
        return classify_command(text)

    _classify = classify
