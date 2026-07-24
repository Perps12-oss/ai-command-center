"""
Passive telemetry — observation only (Phase 5C+).

All SQLite writes run on a dedicated worker with batching. Bus handlers only
enqueue; they never block the publisher (UI / EventBus) on disk I/O.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CHAT_CANCELLED,
    CHAT_COMPLETE,
    CHAT_ERROR,
    CHAT_STARTED,
    CONTEXT_OVER_BUDGET,
    CONTEXT_SNAPSHOT_CREATED,
    CONTEXT_TRIMMED,
    ENTITY_CREATED,
    ENTITY_DELETED,
    ENTITY_UPDATED,
    EXECUTION_AUTHORITY_DECISION,
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
from ai_command_center.core.events.handler_dispatch import HandlerDispatchMode
from ai_command_center.domain.telemetry_event import TelemetryEvent
from ai_command_center.repositories.telemetry_repository import TelemetryRepository
from ai_command_center.services.base import BaseService

logger = logging.getLogger(__name__)

_BATCH_MAX = 32
_BATCH_WAIT_S = 0.05
# Navigate/palette: SQLite audit only (no nested TELEMETRY_EVENT) — unchanged contract.
_NO_NEST_PUBLISH = frozenset({UI_NAVIGATE, UI_PALETTE_OPEN, UI_PALETTE_CLOSE})

# Explicit topic subscriptions only — no wildcard taps in production.
_BUS_TOPICS = (
    UI_COMMAND,
    EXECUTION_AUTHORITY_DECISION,
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
    """Dumb camera: bus event → async SQLite append (batched)."""

    name = "telemetry"

    def __init__(self, bus, repo: TelemetryRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._unsubscribers: list[Callable[[], None]] = []
        self._defer_queue: queue.SimpleQueue[Event | None] = queue.SimpleQueue()
        self._defer_thread: threading.Thread | None = None

    @property
    def session_id(self) -> str:
        return self._session_id

    def _on_load(self) -> None:
        self._defer_thread = threading.Thread(
            target=self._defer_worker,
            name="telemetry-defer",
            daemon=True,
        )
        self._defer_thread.start()
        for topic in _BUS_TOPICS:
            self._unsubscribers.append(
                self._bus.subscribe(
                    topic,
                    self._on_bus_event,
                    dispatch_mode=HandlerDispatchMode.ASYNC_QUEUE,
                )
            )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._defer_queue.put(None)
        thread = self._defer_thread
        self._defer_thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)

    def _defer_worker(self) -> None:
        batch: list[tuple[str, dict[str, Any], str]] = []
        nest: list[tuple[str, dict[str, Any], float]] = []
        while True:
            try:
                item = self._defer_queue.get(timeout=_BATCH_WAIT_S)
            except queue.Empty:
                try:
                    self._flush_batch(batch, nest)
                except Exception:
                    logger.exception("Telemetry batch flush failed")
                batch.clear()
                nest.clear()
                continue
            if item is None:
                try:
                    self._flush_batch(batch, nest)
                except Exception:
                    logger.exception("Telemetry final flush failed")
                break
            event = item
            try:
                payload = {
                    "session_id": self._session_id,
                    "bus_source": event.source,
                    "bus_event_id": event.event_id,
                    **dict(event.payload),
                    **self._extract_scope(dict(event.payload)),
                }
                ts_iso = datetime.fromtimestamp(
                    event.timestamp, tz=timezone.utc
                ).isoformat()
                batch.append((event.topic, payload, ts_iso))
                if event.topic not in _NO_NEST_PUBLISH:
                    nest.append((event.topic, payload, event.timestamp))
                while len(batch) < _BATCH_MAX:
                    try:
                        nxt = self._defer_queue.get_nowait()
                    except queue.Empty:
                        break
                    if nxt is None:
                        self._flush_batch(batch, nest)
                        return
                    payload = {
                        "session_id": self._session_id,
                        "bus_source": nxt.source,
                        "bus_event_id": nxt.event_id,
                        **dict(nxt.payload),
                        **self._extract_scope(dict(nxt.payload)),
                    }
                    ts_iso = datetime.fromtimestamp(
                        nxt.timestamp, tz=timezone.utc
                    ).isoformat()
                    batch.append((nxt.topic, payload, ts_iso))
                    if nxt.topic not in _NO_NEST_PUBLISH:
                        nest.append((nxt.topic, payload, nxt.timestamp))
                if len(batch) >= _BATCH_MAX:
                    self._flush_batch(batch, nest)
                    batch.clear()
                    nest.clear()
            except Exception:
                logger.exception(
                    "Deferred telemetry record failed topic=%s",
                    getattr(event, "topic", "?"),
                )

    def _flush_batch(
        self,
        batch: list[tuple[str, dict[str, Any], str]],
        nest: list[tuple[str, dict[str, Any], float]],
    ) -> None:
        if not batch:
            return
        started = time.perf_counter()
        try:
            self._repo.insert_many(
                [(event, payload, ts) for event, payload, ts in batch]
            )
            for topic, payload, ts in nest:
                normalized = TelemetryEvent(
                    event_type=topic,
                    payload=tuple(payload.items()),
                    emitted_at=datetime.fromtimestamp(ts, tz=timezone.utc),
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
        finally:
            try:
                from ai_command_center.core.perf.metrics import get_perf_metrics

                get_perf_metrics().record(
                    "sqlite.telemetry_batch",
                    (time.perf_counter() - started) * 1000.0,
                )
                get_perf_metrics().incr("sqlite.telemetry_rows", len(batch))
            except Exception:
                pass

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
        # Always enqueue — never SQLite or nest-publish on the publisher thread.
        self._defer_queue.put(event)
