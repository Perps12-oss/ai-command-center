"""ExecutionEvent capture service — bus-only append-only event stream (ACC UI PR 8)."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CHAT_CANCELLED,
    CHAT_COMPLETE,
    CHAT_ERROR,
    CHAT_STARTED,
    EXECUTION_EVENT_APPENDED,
    EXECUTION_EVENTS_LOADED,
    ORCHESTRATION_RUN_SNAPSHOT,
    TOOL_COMPLETED,
    TOOL_FAILED,
    TOOL_RESULT,
    TOOL_STARTED,
)
from ai_command_center.domain.execution_event import ExecutionEvent, _dict_to_pairs
from ai_command_center.repositories.execution_event_repository import ExecutionEventRepository
from ai_command_center.services.base import BaseService

_CAPTURED_TOPICS: tuple[str, ...] = (
    ORCHESTRATION_RUN_SNAPSHOT,
    CHAT_STARTED,
    CHAT_COMPLETE,
    CHAT_ERROR,
    CHAT_CANCELLED,
    TOOL_STARTED,
    TOOL_COMPLETED,
    TOOL_FAILED,
    TOOL_RESULT,
)


class ExecutionEventService(BaseService):
    """Subscribes to execution-related bus topics and appends ExecutionEvent rows."""

    name = "execution_event"

    def __init__(self, bus, *, repo: ExecutionEventRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._unsubscribers: list[Callable[[], None]] = []
        self._last_event_by_request: dict[str, str] = {}

    def _on_load(self) -> None:
        for topic in _CAPTURED_TOPICS:
            self._unsubscribers.append(self._bus.subscribe(topic, self._on_bus_event))
        self._publish_recent_events()

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._last_event_by_request.clear()

    def _publish_recent_events(self) -> None:
        events = self._repo.list_recent()
        if not events:
            return
        self._bus.publish(
            EXECUTION_EVENTS_LOADED,
            {"events": [event.to_bus_payload() for event in events]},
            source=self.name,
        )

    def _publish_appended(self, event: ExecutionEvent) -> None:
        self._bus.publish(
            EXECUTION_EVENT_APPENDED,
            event.to_bus_payload(),
            source=self.name,
        )

    @staticmethod
    def _request_id(payload: dict) -> str:
        request_id = str(payload.get("request_id", "")).strip()
        if request_id:
            return request_id
        invoke_id = str(payload.get("invoke_id", "")).strip()
        if invoke_id:
            return invoke_id
        return ""

    @staticmethod
    def _trace_id(payload: dict, request_id: str) -> str:
        trace_id = str(payload.get("trace_id", "")).strip()
        if trace_id:
            return trace_id
        if request_id:
            return request_id
        return uuid.uuid4().hex

    @staticmethod
    def _scope(payload: dict, *, fallback: str) -> str:
        for key in ("scope", "source", "tool", "intent"):
            value = str(payload.get(key, "")).strip()
            if value:
                return value
        return fallback

    def _should_skip(self, event: Event) -> bool:
        if event.topic == CHAT_COMPLETE and event.payload.get("orchestration"):
            return True
        return False

    def _on_bus_event(self, event: Event) -> None:
        if self._should_skip(event):
            return
        payload = dict(event.payload)
        request_id = self._request_id(payload)
        trace_id = self._trace_id(payload, request_id)
        parent_event_id = self._last_event_by_request.get(request_id) if request_id else None
        stored = self._repo.append(
            ExecutionEvent(
                event_id=uuid.uuid4().hex,
                trace_id=trace_id,
                parent_event_id=parent_event_id,
                timestamp=event.timestamp,
                event_type=event.topic,
                actor=str(event.source or self.name),
                scope=self._scope(payload, fallback=event.topic),
                request_id=request_id,
                payload=_dict_to_pairs(payload),
                state_diff=None,
            )
        )
        if request_id:
            self._last_event_by_request[request_id] = stored.event_id
        self._publish_appended(stored)
