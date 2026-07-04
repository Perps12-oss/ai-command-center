"""Thread-safe publish/subscribe event bus.

Handlers run synchronously on the caller thread by default. Optional central
dispatch queue (R4b) defers ``ASYNC_ELIGIBLE`` topics to an ``event-dispatch``
daemon thread when enabled via ``async_dispatch=True`` or env
``EVENTBUS_DISPATCH_QUEUE=1``.

R4c adds per-handler ``async_queue`` adapters (``EVENTBUS_ASYNC_ADAPTERS=1``),
bounded queue depth (``EVENTBUS_QUEUE_MAX_DEPTH``), and handler duration metrics.
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
    budget_exceedance_is_warning,
    get_dispatch_tier,
    get_time_budget_ms,
)
from ai_command_center.core.events.handler_dispatch import (
    HandlerDispatchMode,
    HandlerRegistration,
    async_adapters_enabled_from_env,
    queue_max_depth_from_env,
)
from ai_command_center.core.events.topics import BUS_HANDLER_ERROR, TELEMETRY_EVENT

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


@dataclass(frozen=True, slots=True)
class _HandlerJob:
    """Internal dispatch unit for topic or per-handler async queue."""

    event: Event
    handler: Callable[[Event], None] | None = None


Subscriber = Callable[[Event], None]


class WildcardSubscriptionError(RuntimeError):
    """Raised when subscribe_all or subscribe('*') is used without debug_mode."""


class EventBus:
    """Thread-safe event bus with optional async dispatch queue (R4b/R4c)."""

    def __init__(
        self,
        *,
        debug_mode: bool = False,
        async_dispatch: bool | None = None,
        async_adapters: bool | None = None,
        queue_max_depth: int | None = None,
    ) -> None:
        self._debug_mode = debug_mode
        self._async_dispatch = (
            async_dispatch
            if async_dispatch is not None
            else dispatch_queue_enabled_from_env()
        )
        self._async_adapters = (
            async_adapters
            if async_adapters is not None
            else async_adapters_enabled_from_env()
        )
        self._queue_max_depth = (
            queue_max_depth
            if queue_max_depth is not None
            else queue_max_depth_from_env()
        )
        self._lock = threading.RLock()
        self._subscribers: dict[str, list[HandlerRegistration]] = defaultdict(list)
        self._wildcard: list[HandlerRegistration] = []
        self._dispatch_queue: queue.Queue[_HandlerJob | None] | None = None
        self._dispatch_thread: threading.Thread | None = None
        self._shutdown = threading.Event()
        self._queue_depth = 0
        self._queue_depth_lock = threading.Lock()
        self._dropped_events = 0
        self._handler_duration_total_ms = 0.0
        self._handler_duration_count = 0
        self._topic_publish_counts: dict[str, int] = defaultdict(int)
        self._topic_counts_lock = threading.Lock()
        if self._async_dispatch or self._async_adapters:
            self._start_dispatch_thread()

    @property
    def debug_mode(self) -> bool:
        return self._debug_mode

    @property
    def async_dispatch(self) -> bool:
        return self._async_dispatch

    @property
    def async_adapters(self) -> bool:
        return self._async_adapters

    @property
    def queue_max_depth(self) -> int:
        return self._queue_max_depth

    @property
    def dispatch_queue_depth(self) -> int:
        with self._queue_depth_lock:
            return self._queue_depth

    @property
    def dropped_events(self) -> int:
        return self._dropped_events

    def get_topic_counts(self) -> dict[str, int]:
        """Return publish counts per topic (measure phase for S6)."""
        with self._topic_counts_lock:
            return dict(self._topic_publish_counts)

    def get_handler_metrics(self) -> dict[str, float | int]:
        count = self._handler_duration_count
        avg_ms = self._handler_duration_total_ms / count if count else 0.0
        return {
            "queue_depth": self.dispatch_queue_depth,
            "dropped_events": self._dropped_events,
            "handler_invocations": count,
            "handler_duration_avg_ms": avg_ms,
        }

    def _assert_wildcard_allowed(self) -> None:
        if not self._debug_mode:
            raise WildcardSubscriptionError(
                "Wildcard EventBus subscriptions are forbidden outside debug_mode. "
                "Use explicit topic subscriptions or EventBus(debug_mode=True) in diagnostics."
            )

    def _start_dispatch_thread(self) -> None:
        if self._dispatch_thread is not None:
            return
        self._dispatch_queue = queue.Queue(maxsize=self._queue_max_depth or 0)
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
                job = self._dispatch_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if job is None:
                self._dispatch_queue.task_done()
                break
            try:
                if job.handler is None:
                    self._invoke_handlers(job.event)
                else:
                    self._invoke_single_handler(job.event, job.handler)
            finally:
                with self._queue_depth_lock:
                    self._queue_depth = max(0, self._queue_depth - 1)
                self._dispatch_queue.task_done()

    def _should_enqueue_topic(self, topic: str) -> bool:
        if not self._async_dispatch or self._shutdown.is_set():
            return False
        return get_dispatch_tier(topic) is DispatchTier.ASYNC_ELIGIBLE

    def _should_async_handler(
        self, topic: str, registration: HandlerRegistration
    ) -> bool:
        if not self._async_adapters or self._shutdown.is_set():
            return False
        if get_dispatch_tier(topic) is DispatchTier.SYNC_CRITICAL:
            return False
        if registration.dispatch_mode is HandlerDispatchMode.ASYNCIO_BRIDGE:
            logger.debug(
                "asyncio_bridge handler on topic=%s runs sync until bridge wired",
                topic,
            )
            return False
        return registration.dispatch_mode is HandlerDispatchMode.ASYNC_QUEUE

    def _record_drop(self, topic: str) -> None:
        self._dropped_events += 1
        logger.warning(
            "EventBus dispatch queue full; dropped event topic=%s depth=%d",
            topic,
            self.dispatch_queue_depth,
        )
        try:
            self.publish(
                EVENT_OBSERVABILITY_METRIC,
                {
                    "metric_type": "eventbus.queue.dropped",
                    "value": 1,
                    "unit": "count",
                    "tags": {"topic": topic},
                },
                source="event_bus",
            )
        except Exception:
            logger.debug("Failed to publish drop metric", exc_info=True)

    def _enqueue(self, event: Event, handler: Subscriber | None = None) -> bool:
        if self._dispatch_queue is None:
            self._start_dispatch_thread()
        assert self._dispatch_queue is not None

        if self._queue_max_depth > 0 and self.dispatch_queue_depth >= self._queue_max_depth:
            drop_telemetry = os.environ.get(
                "EVENTBUS_QUEUE_DROP_TELEMETRY", ""
            ).strip().lower() in {"1", "true", "yes", "on"}
            if event.topic == TELEMETRY_EVENT and drop_telemetry:
                self._record_drop(event.topic)
                return False
            if get_dispatch_tier(event.topic) is DispatchTier.SYNC_CRITICAL:
                logger.error(
                    "Dispatch queue full for SYNC_CRITICAL topic=%s — invoking inline",
                    event.topic,
                )
                if handler is None:
                    self._invoke_handlers(event)
                else:
                    self._invoke_single_handler(event, handler)
                return True

        job = _HandlerJob(event=event, handler=handler)
        try:
            self._dispatch_queue.put_nowait(job)
        except queue.Full:
            self._record_drop(event.topic)
            return False

        with self._queue_depth_lock:
            self._queue_depth += 1
        return True

    def subscribe(
        self,
        topic: str,
        handler: Subscriber,
        *,
        dispatch_mode: HandlerDispatchMode = HandlerDispatchMode.SYNC,
    ) -> Callable[[], None]:
        if topic == WILDCARD_TOPIC:
            self._assert_wildcard_allowed()
        registration = HandlerRegistration(handler=handler, dispatch_mode=dispatch_mode)
        with self._lock:
            self._subscribers[topic].append(registration)

        def unsubscribe() -> None:
            with self._lock:
                handlers = self._subscribers.get(topic, [])
                if registration in handlers:
                    handlers.remove(registration)

        return unsubscribe

    def subscribe_all(
        self,
        handler: Subscriber,
        *,
        dispatch_mode: HandlerDispatchMode = HandlerDispatchMode.SYNC,
    ) -> Callable[[], None]:
        self._assert_wildcard_allowed()
        registration = HandlerRegistration(handler=handler, dispatch_mode=dispatch_mode)
        with self._lock:
            self._wildcard.append(registration)

        def unsubscribe() -> None:
            with self._lock:
                if registration in self._wildcard:
                    self._wildcard.remove(registration)

        return unsubscribe

    def publish(
        self,
        topic: str,
        payload: dict[str, Any] | None = None,
        *,
        source: str = "system",
    ) -> Event:
        event = Event(topic=topic, payload=dict(payload or {}), source=source)
        with self._topic_counts_lock:
            self._topic_publish_counts[topic] += 1
        if self._should_enqueue_topic(topic):
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
        if self._should_enqueue_topic(event.topic):
            self._enqueue(event)
            return
        self._invoke_handlers(event)

    def _collect_registrations(self, topic: str) -> list[HandlerRegistration]:
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
        return handlers

    def _invoke_handlers(self, event: Event) -> None:
        topic = event.topic
        registrations = self._collect_registrations(topic)
        deferred: list[tuple[Event, Subscriber]] = []

        for registration in registrations:
            if self._should_async_handler(topic, registration):
                deferred.append((event, registration.handler))
                continue
            self._invoke_single_handler(event, registration.handler)

        for deferred_event, handler in deferred:
            self._enqueue(deferred_event, handler)

    def _invoke_single_handler(self, event: Event, handler: Subscriber) -> None:
        topic = event.topic
        budget_ms = get_time_budget_ms(topic)
        start = time.perf_counter()
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
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self._handler_duration_total_ms += elapsed_ms
            self._handler_duration_count += 1
            if elapsed_ms > budget_ms:
                log = (
                    logger.warning
                    if budget_exceedance_is_warning(topic)
                    else logger.debug
                )
                log(
                    "EventBus handler exceeded budget topic=%s elapsed_ms=%.2f budget_ms=%d",
                    topic,
                    elapsed_ms,
                    budget_ms,
                )
            if (
                topic not in {EVENT_OBSERVABILITY_METRIC, BUS_HANDLER_ERROR}
                and (self._debug_mode or elapsed_ms > budget_ms)
            ):
                try:
                    self.publish(
                        EVENT_OBSERVABILITY_METRIC,
                        {
                            "metric_type": "eventbus.handler.duration_ms",
                            "value": round(elapsed_ms, 3),
                            "unit": "ms",
                            "tags": {"topic": topic},
                        },
                        source="event_bus",
                    )
                except Exception:
                    logger.debug("Failed to publish handler duration metric", exc_info=True)

    def shutdown(self) -> None:
        if self._dispatch_thread is None:
            return
        self._shutdown.set()
        assert self._dispatch_queue is not None
        try:
            self._dispatch_queue.put_nowait(None)
        except queue.Full:
            self._dispatch_queue.put(None)
        self._dispatch_thread.join(timeout=5.0)
        self._dispatch_thread = None
        self._dispatch_queue = None
