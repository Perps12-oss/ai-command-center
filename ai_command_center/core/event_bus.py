"""Thread-safe publish/subscribe event bus.

Handlers run synchronously on the caller thread by default. Optional central
dispatch queue (R4b) defers ``ASYNC_ELIGIBLE`` topics to an ``event-dispatch``
daemon thread when enabled via ``async_dispatch=True`` or env
``EVENTBUS_DISPATCH_QUEUE=1``.
"""

from __future__ import annotations

import logging
import os
import queue
import threading
import time
import traceback
import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ai_command_center.core.events.dispatch_policy import (
    DispatchTier,
    get_dispatch_tier,
    get_time_budget_ms,
)
from ai_command_center.core.events.topics import BUS_HANDLER_ERROR

logger = logging.getLogger(__name__)

WILDCARD_TOPIC = "*"
DISPATCH_QUEUE_ENV = "EVENTBUS_DISPATCH_QUEUE"

EVENT_ENTITY_CREATED = "entity.created"
EVENT_ENTITY_UPDATED = "entity.updated"
EVENT_ENTITY_DELETED = "entity.deleted"
EVENT_ENTITY_RELATIONSHIPS_CHANGED = "entity.relationships.changed"
EVENT_RELATIONSHIP_CREATED = "relationship.created"
EVENT_RELATIONSHIP_DELETED = "relationship.deleted"
EVENT_RELATIONSHIP_QUERY_REQUEST = "relationship.query.request"
EVENT_ACTION_REGISTERED = "action.registered"
EVENT_ACTION_INVOKED = "action.invoked"
EVENT_ACTION_COMPLETED = "action.completed"
EVENT_ACTION_FAILED = "action.failed"
EVENT_WORKSPACE_CREATED = "workspace.created"
EVENT_WORKSPACE_ACTIVATED = "workspace.activated"
EVENT_WORKSPACE_DEACTIVATED = "workspace.deactivated"
EVENT_WORKSPACE_LAYOUT_CHANGED = "workspace.layout.changed"
EVENT_TIMELINE_EVENT = "timeline.event"
EVENT_SEARCH_EXECUTED = "search.executed"
EVENT_SEARCH_RESULTS = "search.results"
EVENT_COMMAND_PALETTE_OPENED = "command_palette.opened"
EVENT_COMMAND_PALETTE_SEARCH = "command_palette.search"
EVENT_COMMAND_PALETTE_ITEM_SELECTED = "command_palette.item.selected"
EVENT_AGENT_SPAWNED = "agent.spawned"
EVENT_AGENT_TERMINATED = "agent.terminated"
EVENT_AI_ACTION_INVOKED = "ai.action.invoked"
EVENT_AI_ACTION_COMPLETED = "ai.action.completed"
EVENT_PLUGIN_LOADED = "plugin.loaded"
EVENT_PLUGIN_UNLOADED = "plugin.unloaded"
EVENT_PLUGIN_REGISTERED_ENTITY = "plugin.registered.entity"
EVENT_PLUGIN_REGISTERED_ACTION = "plugin.registered.action"
EVENT_PLUGIN_REGISTERED_VIEW = "plugin.registered.view"
EVENT_PLUGIN_REGISTERED_SEARCH_PROVIDER = "plugin.registered.search_provider"
EVENT_OBSERVABILITY_METRIC = "observability.metric"
EVENT_OBSERVABILITY_ERROR = "observability.error"
EVENT_PERMISSION_CHECK = "permission.check"
EVENT_PERMISSION_DENIED = "permission.denied"
EVENT_SNAPSHOT_CREATED = "snapshot.created"
EVENT_SNAPSHOT_RESTORED = "snapshot.restored"


def dispatch_queue_enabled_from_env() -> bool:
    raw = os.environ.get(DISPATCH_QUEUE_ENV, "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Event:
    topic: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=time.time)
    source: str = "system"


Subscriber = Callable[[Event], None]


class WildcardSubscriptionError(RuntimeError):
    """Raised when subscribe_all or subscribe('*') is used without debug_mode."""


class EventBus:
    """Thread-safe event bus with optional async dispatch queue (R4b)."""

    def __init__(
        self,
        *,
        debug_mode: bool = False,
        async_dispatch: bool | None = None,
    ) -> None:
        self._debug_mode = debug_mode
        self._async_dispatch = (
            async_dispatch
            if async_dispatch is not None
            else dispatch_queue_enabled_from_env()
        )
        self._lock = threading.RLock()
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)
        self._wildcard: list[Subscriber] = []
        self._dispatch_queue: queue.Queue[Event | None] | None = None
        self._dispatch_thread: threading.Thread | None = None
        self._shutdown = threading.Event()
        self._queue_depth = 0
        self._queue_depth_lock = threading.Lock()
        if self._async_dispatch:
            self._start_dispatch_thread()

    @property
    def debug_mode(self) -> bool:
        return self._debug_mode

    @property
    def async_dispatch(self) -> bool:
        return self._async_dispatch

    @property
    def dispatch_queue_depth(self) -> int:
        with self._queue_depth_lock:
            return self._queue_depth

    def _assert_wildcard_allowed(self) -> None:
        if not self._debug_mode:
            raise WildcardSubscriptionError(
                "Wildcard EventBus subscriptions are forbidden outside debug_mode. "
                "Use explicit topic subscriptions or EventBus(debug_mode=True) in diagnostics."
            )

    def _start_dispatch_thread(self) -> None:
        self._dispatch_queue = queue.Queue()
        self._dispatch_thread = threading.Thread(
            target=self._dispatch_worker,
            name="event-dispatch",
            daemon=True,
        )
        self._dispatch_thread.start()

    def _dispatch_worker(self) -> None:
        assert self._dispatch_queue is not None
        while not self._shutdown.is_set():
            try:
                event = self._dispatch_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if event is None:
                self._dispatch_queue.task_done()
                break
            try:
                self._invoke_handlers(event)
            finally:
                with self._queue_depth_lock:
                    self._queue_depth = max(0, self._queue_depth - 1)
                self._dispatch_queue.task_done()

    def _should_enqueue(self, topic: str) -> bool:
        if not self._async_dispatch or self._shutdown.is_set():
            return False
        return get_dispatch_tier(topic) is DispatchTier.ASYNC_ELIGIBLE

    def _enqueue(self, event: Event) -> None:
        assert self._dispatch_queue is not None
        with self._queue_depth_lock:
            self._queue_depth += 1
        self._dispatch_queue.put(event)

    def subscribe(self, topic: str, handler: Subscriber) -> Callable[[], None]:
        if topic == WILDCARD_TOPIC:
            self._assert_wildcard_allowed()
        with self._lock:
            self._subscribers[topic].append(handler)

        def unsubscribe() -> None:
            with self._lock:
                handlers = self._subscribers.get(topic, [])
                if handler in handlers:
                    handlers.remove(handler)

        return unsubscribe

    def subscribe_all(self, handler: Subscriber) -> Callable[[], None]:
        self._assert_wildcard_allowed()
        with self._lock:
            self._wildcard.append(handler)

        def unsubscribe() -> None:
            with self._lock:
                if handler in self._wildcard:
                    self._wildcard.remove(handler)

        return unsubscribe

    def publish(
        self,
        topic: str,
        payload: dict[str, Any] | None = None,
        *,
        source: str = "system",
    ) -> Event:
        event = Event(topic=topic, payload=dict(payload or {}), source=source)
        if self._should_enqueue(topic):
            if self._debug_mode:
                logger.debug(
                    "EventBus enqueue topic=%s tier=%s budget_ms=%s",
                    topic,
                    get_dispatch_tier(topic).value,
                    get_time_budget_ms(topic),
                )
            self._enqueue(event)
            return event
        self._invoke_handlers(event)
        return event

    def dispatch(self, event: Event) -> None:
        if self._should_enqueue(event.topic):
            self._enqueue(event)
            return
        self._invoke_handlers(event)

    def _invoke_handlers(self, event: Event) -> None:
        topic = event.topic
        with self._lock:
            handlers = list(self._wildcard)
            handlers.extend(self._subscribers.get(topic, []))
            if self._debug_mode:
                handlers.extend(self._subscribers.get(WILDCARD_TOPIC, []))
                logger.debug(
                    "EventBus dispatch topic=%s tier=%s handlers=%d",
                    topic,
                    get_dispatch_tier(topic).value,
                    len(handlers),
                )

        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                logger.exception(
                    "EventBus handler failed for topic=%s source=%s",
                    topic,
                    event.source,
                )
                if topic != BUS_HANDLER_ERROR:
                    try:
                        self.publish(
                            BUS_HANDLER_ERROR,
                            {
                                "topic": topic,
                                "source": event.source,
                                "error": str(exc),
                                "traceback": traceback.format_exc(limit=5),
                            },
                            source="event_bus",
                        )
                    except Exception:
                        logger.exception("Failed to publish bus.handler_error")

    def shutdown(self) -> None:
        if not self._async_dispatch or self._dispatch_thread is None:
            return
        self._shutdown.set()
        assert self._dispatch_queue is not None
        self._dispatch_queue.put(None)
        self._dispatch_thread.join(timeout=5.0)
        self._dispatch_thread = None
        self._dispatch_queue = None
