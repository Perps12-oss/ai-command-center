"""
Passive telemetry — observation only (Phase 5C+).

Subscribes to EventBus topics, stores append-only SQLite log of raw bus events,
and publishes normalized TelemetryEvent back to the EventBus. No inference,
correlation, or behavioral classification at runtime.
Derived metrics: telemetry_summary.py (offline only).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CHAT_CANCELLED,
    CHAT_COMPLETE,
    CHAT_ERROR,
    CHAT_STARTED,
    COMMAND_ROUTED,
    CONTEXT_OVER_BUDGET,
    CONTEXT_SNAPSHOT_CREATED,
    CONTEXT_TRIMMED,
    ENTITY_CREATED,
    ENTITY_DELETED,
    ENTITY_UPDATED,
    MEMORY_LOOKUP_REQUEST,
    MEMORY_REMEMBER,
    MEMORY_STORED,
    NOTE_CREATED,
    NOTE_ERROR,
    NOTE_SEARCH_RESULTS,
    TELEMETRY_EVENT,
    TOOL_INVOKE,
    TOOL_ERROR,
    TOOL_RESULT,
    UI_COMMAND,
    UI_NAVIGATE,
    UI_OPEN_CHAT,
    UI_PALETTE_CLOSE,
    UI_PALETTE_OPEN,
)
from ai_command_center.repositories.telemetry_repository import TelemetryRepository
from ai_command_center.domain.telemetry_event import TelemetryEvent
from ai_command_center.services.base import BaseService

_HANDLER_SLOW_MS = 5.0

# Explicit topic subscriptions only — no wildcard taps in production.
_BUS_TOPICS = (
    UI_COMMAND,
    COMMAND_ROUTED,
    UI_PALETTE_OPEN,
    UI_PALETTE_CLOSE,
    UI_NAVIGATE,
    CHAT_STARTED,
    CHAT_COMPLETE,
    CHAT_ERROR,
    CHAT_CANCELLED,
    UI_OPEN_CHAT,
    ENTITY_CREATED,
    ENTITY_UPDATED,
    ENTITY_DELETED,
    TOOL_INVOKE,
    TOOL_RESULT,
    TOOL_ERROR,
    NOTE_SEARCH_RESULTS,
    NOTE_CREATED,
    NOTE_ERROR,
    MEMORY_REMEMBER,
    MEMORY_LOOKUP_REQUEST,
    MEMORY_STORED,
    CONTEXT_SNAPSHOT_CREATED,
    CONTEXT_OVER_BUDGET,
    CONTEXT_TRIMMED,
)


class TelemetryService(BaseService):
    """Dumb camera: bus event → normalized TelemetryEvent → EventBus + SQLite."""

    name = "telemetry"

    def __init__(self, bus, repo: TelemetryRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._unsubscribers: list[Callable[[], None]] = []

    @property
    def session_id(self) -> str:
        return self._session_id

    def _on_load(self) -> None:
        for topic in _BUS_TOPICS:
            self._unsubscribers.append(self._bus.subscribe(topic, self._on_bus_event))

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _record(self, event: str, payload: dict[str, Any], *, timestamp: float | None = None) -> None:
        body = {"session_id": self._session_id, **payload, **self._extract_scope(payload)}
        ts_iso = datetime.fromtimestamp(
            timestamp or time.time(), tz=timezone.utc
        ).isoformat()
        self._repo.insert(event, body, timestamp=ts_iso)

    @staticmethod
    def _extract_scope(payload: dict[str, Any]) -> dict[str, str]:
        """Normalize workspace/entity identifiers from bus payload variants."""
        workspace_id = str(payload.get("workspace_id", "")).strip()
        entity_id = str(
            payload.get("entity_id") or payload.get("workspace_entity_id") or ""
        ).strip()
        workspace_context = payload.get("workspace_context")
        if isinstance(workspace_context, dict):
            workspace_id = workspace_id or str(workspace_context.get("workspace_id", "")).strip()
            entity_id = entity_id or str(workspace_context.get("entity_id", "")).strip()
        scope: dict[str, str] = {}
        if workspace_id:
            scope["workspace_id"] = workspace_id
        if entity_id:
            scope["entity_id"] = entity_id
        return scope

    def _on_bus_event(self, event: Event) -> None:
        started = time.perf_counter()
        payload = {
            "bus_source": event.source,
            "bus_event_id": event.event_id,
            **dict(event.payload),
        }
        self._record(event.topic, payload, timestamp=event.timestamp)
        normalized = TelemetryEvent(
            event_type=event.topic,
            payload=tuple({**payload, **self._extract_scope(payload)}.items()),
            emitted_at=datetime.fromtimestamp(event.timestamp, tz=timezone.utc),
        )
        self._bus.publish(
            TELEMETRY_EVENT,
            {
                "event_type": normalized.event_type,
                "payload": dict(normalized.payload),
                "emitted_at": normalized.timestamp,
                "session_id": self._session_id,
            },
            source=self.name,
        )
        handler_ms = (time.perf_counter() - started) * 1000.0
        if handler_ms >= _HANDLER_SLOW_MS:
            self._record(
                "telemetry.handler_time",
                {
                    "topic": event.topic,
                    "latency_ms": round(handler_ms, 2),
                    "bus_source": event.source,
                },
                timestamp=event.timestamp,
            )
