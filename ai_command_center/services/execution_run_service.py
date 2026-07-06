"""Append-only execution run capture for time-travel diagnostics."""

from __future__ import annotations

from collections.abc import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import CHAT_COMPLETE, ORCHESTRATION_RUN_SNAPSHOT
from ai_command_center.repositories.execution_run_repository import ExecutionRunRepository
from ai_command_center.services.base import BaseService


class ExecutionRunService(BaseService):
    """Subscribes to orchestration and chat completion; persists append-only runs."""

    name = "execution_run"

    def __init__(self, bus, *, repo: ExecutionRunRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(ORCHESTRATION_RUN_SNAPSHOT, self._on_orchestration_snapshot)
        )
        self._unsubscribers.append(
            self._bus.subscribe(CHAT_COMPLETE, self._on_chat_complete)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_orchestration_snapshot(self, event: Event) -> None:
        payload = event.payload
        request_id = str(payload.get("request_id", "")).strip()
        if not request_id:
            return
        self._repo.append(
            request_id=request_id,
            source="orchestration",
            snapshot=dict(payload),
        )

    def _on_chat_complete(self, event: Event) -> None:
        payload = event.payload
        if payload.get("orchestration"):
            return
        request_id = str(payload.get("request_id", "")).strip()
        if not request_id:
            return
        self._repo.append(
            request_id=request_id,
            source="chat",
            snapshot={
                "request_id": request_id,
                "text": str(payload.get("text", "")),
                "model": str(payload.get("model", "")),
            },
        )
