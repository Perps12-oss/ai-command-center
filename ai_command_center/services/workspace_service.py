"""Workspace runtime service — wires the pure v3.5 workspace domain to the EventBus.

This is the runtime/service layer for the Workspace OS domain (``ai_command_center/
workspace/``). It is **pull-based and event-driven**: it acts only when a ``ui.command``
event arrives — it starts no background threads and observes no OS state on its own.
All evidence (command text, clipboard, vault path) is read from event payloads handed
in by upstream layers, keeping acquisition explicit.

On each command it deterministically resolves the active ``WorkspaceContext`` (with
lease continuity) and produces pre-AI suggestions, then publishes a single
``workspace.resolved`` event for AppState/UI to consume.
"""

from __future__ import annotations

from typing import Callable

from ai_command_center.core.contracts import WORKSPACE_RESOLVED_VERSION
from ai_command_center.core.event_bus import Event
from ai_command_center.services.base import BaseService
from ai_command_center.workspace.context_acquisition import (
    CallableProvider,
    ContextAcquirer,
    ContextSource,
)
from ai_command_center.workspace.domain import TelemetrySnapshot
from ai_command_center.workspace.suggestions import SuggestionEngine
from ai_command_center.workspace.resolver import WorkspaceResolver


class WorkspaceService(BaseService):
    """Resolves the active workspace + suggestions for each command, via the bus."""

    name = "workspace"

    def __init__(
        self,
        bus,
        *,
        resolver: WorkspaceResolver | None = None,
        suggestion_engine: SuggestionEngine | None = None,
    ) -> None:
        super().__init__(bus)
        self._resolver = resolver or WorkspaceResolver()
        self._suggestions = suggestion_engine or SuggestionEngine()
        self._vault_path: str = ""
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(self._bus.subscribe("ui.command", self._on_ui_command))
        self._unsubscribers.append(
            self._bus.subscribe("settings.snapshot", self._on_settings_snapshot)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_settings_snapshot(self, event: Event) -> None:
        self._vault_path = str(event.payload.get("obsidian_vault_path", "") or "")

    def _on_ui_command(self, event: Event) -> None:
        text = str(event.payload.get("text", "")).strip()
        if not text:
            return
        clipboard = str(event.payload.get("clipboard", "") or "")

        snapshot = TelemetrySnapshot(
            timestamp=event.timestamp,
            target_hwnd=0,
            app_name="AI Command Center",
            window_title=text,
            clipboard_text=clipboard,
        )
        context = self._resolver.resolve(
            snapshot,
            vault_path=self._vault_path or None,
        )

        acquired = self._acquire(text, clipboard)
        suggestions = self._suggestions.suggest(acquired)

        self._bus.publish(
            "workspace.resolved",
            {
                "contract_version": WORKSPACE_RESOLVED_VERSION,
                "workspace_id": context.workspace_id,
                "title": context.title,
                "inferred_task": context.inferred_task,
                "confidence": float(context.metadata.get("confidence", 0.0)),
                "evidence_source": str(context.metadata.get("evidence_source", "none")),
                "suggestions": [
                    {"label": s.label, "command": s.command, "score": s.score}
                    for s in suggestions
                ],
            },
            source=self.name,
        )

    def _acquire(self, text: str, clipboard: str):
        acquirer = ContextAcquirer()
        acquirer.register(
            CallableProvider(
                ContextSource.EXPLICIT_INPUT,
                lambda: text or None,
                key="command",
            )
        )
        acquirer.register(
            CallableProvider(
                ContextSource.CLIPBOARD,
                lambda: clipboard or None,
                key="clipboard",
            )
        )
        return acquirer.acquire()
