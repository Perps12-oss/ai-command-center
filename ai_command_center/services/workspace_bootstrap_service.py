"""Auto-bootstrap a workspace for deferred first commands.

When ExecutionAuthority emits ``ui.workspace.required`` because no active
workspace exists, this service creates/selects a default workspace and replays
the deferred command via ``ui.command``.
"""

from __future__ import annotations

from collections.abc import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    UI_COMMAND,
    UI_CREATE_WORKSPACE,
    UI_WORKSPACE_REQUIRED,
    WORKSPACE_ACTIVE,
    WORKSPACE_DEACTIVATED,
)
from ai_command_center.services.base import BaseService

_DEFAULT_WORKSPACE_TITLE = "My Workspace"
_DEFAULT_WORKSPACE_DESCRIPTION = "Auto-created to run your first command."


class WorkspaceBootstrapService(BaseService):
    """Creates/selects a default workspace and replays deferred commands."""

    name = "workspace_bootstrap"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []
        self._active_workspace_id: str = ""
        self._pending_commands: list[dict[str, str]] = []
        self._bootstrap_inflight = False

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(UI_WORKSPACE_REQUIRED, self._on_workspace_required)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_ACTIVE, self._on_workspace_active)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_DEACTIVATED, self._on_workspace_deactivated)
        )

    def _on_unload(self) -> None:
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        self._pending_commands.clear()
        self._bootstrap_inflight = False
        self._active_workspace_id = ""

    def _on_workspace_active(self, event: Event) -> None:
        self._active_workspace_id = str(event.payload.get("workspace_id", "")).strip()
        if self._active_workspace_id:
            self._bootstrap_inflight = False
            self._replay_pending_commands()

    def _on_workspace_deactivated(self, event: Event) -> None:
        workspace_id = str(event.payload.get("workspace_id", "")).strip()
        if not workspace_id or workspace_id == self._active_workspace_id:
            self._active_workspace_id = ""

    def _on_workspace_required(self, event: Event) -> None:
        text = str(event.payload.get("text", "")).strip()
        if not text:
            return
        request_id = str(event.payload.get("request_id", "")).strip()
        self._pending_commands.append({"text": text, "request_id": request_id})

        if self._active_workspace_id:
            self._replay_pending_commands()
            return

        if self._bootstrap_inflight:
            return
        self._bootstrap_inflight = True
        self._bus.publish(
            UI_CREATE_WORKSPACE,
            {
                "title": _DEFAULT_WORKSPACE_TITLE,
                "description": _DEFAULT_WORKSPACE_DESCRIPTION,
            },
            source=self.name,
        )

    def _replay_pending_commands(self) -> None:
        pending = list(self._pending_commands)
        self._pending_commands.clear()
        for item in pending:
            payload = {
                "text": item["text"],
                "replayed_from_workspace_bootstrap": True,
            }
            request_id = item.get("request_id", "")
            if request_id:
                payload["request_id"] = request_id
            self._bus.publish(UI_COMMAND, payload, source=self.name)
