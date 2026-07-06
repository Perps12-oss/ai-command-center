"""Bridges command.routed shell intent to tool.invoke (Phase 4B)."""

from __future__ import annotations

import uuid
from typing import Callable

from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION, build_workspace_context
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    COMMAND_ROUTED,
    TOOL_INVOKE,
    WORKSPACE_ACTIVE,
    WORKSPACE_DEACTIVATED,
)
from ai_command_center.services.base import BaseService
from ai_command_center.core.events.intents import INTENT_SHELL


class ShellToolService(BaseService):
    """Maps `>` commands to one-shot shell tool invocation."""

    name = "shell_tool"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []
        self._active_workspace_id: str = ""

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(COMMAND_ROUTED, self._on_command_routed)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_ACTIVE, self._on_workspace_active)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_DEACTIVATED, self._on_workspace_deactivated)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_workspace_active(self, event: Event) -> None:
        self._active_workspace_id = str(event.payload.get("workspace_id", "")).strip()

    def _on_workspace_deactivated(self, event: Event) -> None:
        cleared = str(event.payload.get("workspace_id", "")).strip()
        if not cleared or cleared == self._active_workspace_id:
            self._active_workspace_id = ""

    def _workspace_context_from_routed(self, event: Event) -> dict[str, str]:
        payload = event.payload
        workspace_id = str(payload.get("workspace_id", "")).strip() or self._active_workspace_id
        return build_workspace_context(
            workspace_id=workspace_id,
            entity_id=payload.get("workspace_entity_id"),
            entity_type=payload.get("workspace_entity_type"),
        )

    def _on_command_routed(self, event: Event) -> None:
        if event.source != "command_router":
            return
        if event.payload.get("intent") != INTENT_SHELL:
            return
        args = event.payload.get("args") or {}
        command = str(args.get("command", "")).strip()
        if not command:
            return
        self._bus.publish(
            TOOL_INVOKE,
            {
                "contract_version": TOOL_CONTRACT_VERSION,
                "invoke_id": uuid.uuid4().hex,
                "tool": "shell",
                "args": {"command": command},
                "actor_type": "user",
                "workspace_context": self._workspace_context_from_routed(event),
            },
            source=self.name,
        )
