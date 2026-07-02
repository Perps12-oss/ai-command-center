"""Thread-safe publish/subscribe event bus."""

from __future__ import annotations

import logging
import threading
import time
import traceback
import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ai_command_center.core.events.topics import BUS_HANDLER_ERROR

logger = logging.getLogger(__name__)

WILDCARD_TOPIC = "*"

# Phase 1: Expanded event topics from frozen architecture specification
# Entity events
EVENT_ENTITY_CREATED = "entity.created"
EVENT_ENTITY_UPDATED = "entity.updated"
EVENT_ENTITY_DELETED = "entity.deleted"
EVENT_ENTITY_RELATIONSHIPS_CHANGED = "entity.relationships.changed"

# Relationship events
EVENT_RELATIONSHIP_CREATED = "relationship.created"
EVENT_RELATIONSHIP_DELETED = "relationship.deleted"
EVENT_RELATIONSHIP_QUERY_REQUEST = "relationship.query.request"

# Action events
EVENT_ACTION_REGISTERED = "action.registered"
EVENT_ACTION_INVOKED = "action.invoked"
EVENT_ACTION_COMPLETED = "action.completed"
EVENT_ACTION_FAILED = "action.failed"

# Workspace events
EVENT_WORKSPACE_CREATED = "workspace.created"
EVENT_WORKSPACE_ACTIVATED = "workspace.activated"
EVENT_WORKSPACE_DEACTIVATED = "workspace.deactivated"
EVENT_WORKSPACE_LAYOUT_CHANGED = "workspace.layout.changed"

# Timeline events (all major actions)
EVENT_TIMELINE_EVENT = "timeline.event"

# Search events
EVENT_SEARCH_EXECUTED = "search.executed"
EVENT_SEARCH_RESULTS = "search.results"

# Command palette events
EVENT_COMMAND_PALETTE_OPENED = "command_palette.opened"
EVENT_COMMAND_PALETTE_SEARCH = "command_palette.search"
EVENT_COMMAND_PALETTE_ITEM_SELECTED = "command_palette.item.selected"

# AI events
EVENT_AGENT_SPAWNED = "agent.spawned"
EVENT_AGENT_TERMINATED = "agent.terminated"
EVENT_AI_ACTION_INVOKED = "ai.action.invoked"
EVENT_AI_ACTION_COMPLETED = "ai.action.completed"

# Plugin events
EVENT_PLUGIN_LOADED = "plugin.loaded"
EVENT_PLUGIN_UNLOADED = "plugin.unloaded"
EVENT_PLUGIN_REGISTERED_ENTITY = "plugin.registered.entity"
EVENT_PLUGIN_REGISTERED_ACTION = "plugin.registered.action"
EVENT_PLUGIN_REGISTERED_VIEW = "plugin.registered.view"
EVENT_PLUGIN_REGISTERED_SEARCH_PROVIDER = "plugin.registered.search_provider"

# Observability events
EVENT_OBSERVABILITY_METRIC = "observability.metric"
EVENT_OBSERVABILITY_ERROR = "observability.error"

# Permission events
EVENT_PERMISSION_CHECK = "permission.check"
EVENT_PERMISSION_DENIED = "permission.denied"

# State snapshot events
EVENT_SNAPSHOT_CREATED = "snapshot.created"
EVENT_SNAPSHOT_RESTORED = "snapshot.restored"


@dataclass(frozen=True, slots=True)
class Event:
    """Immutable event envelope."""

    topic: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=time.time)
    source: str = "system"


Subscriber = Callable[[Event], None]


class WildcardSubscriptionError(RuntimeError):
    """Raised when subscribe_all or subscribe('*') is used without debug_mode."""


class EventBus:
    """
    Thread-safe event bus.
    Services publish; AppState and UI subscribe to explicit topics only.
  Wildcard taps require debug_mode=True (diagnostics / verify scripts).
    """

    def __init__(self, *, debug_mode: bool = False) -> None:
        self._debug_mode = debug_mode
        self._lock = threading.RLock()
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)
        self._wildcard: list[Subscriber] = []

    @property
    def debug_mode(self) -> bool:
        return self._debug_mode

    def _assert_wildcard_allowed(self) -> None:
        if not self._debug_mode:
            raise WildcardSubscriptionError(
                "Wildcard EventBus subscriptions are forbidden outside debug_mode. "
                "Use explicit topic subscriptions or EventBus(debug_mode=True) in diagnostics."
            )

    def subscribe(self, topic: str, handler: Subscriber) -> Callable[[], None]:
        """Subscribe to a topic. Returns an unsubscribe callable."""
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
        """Receive every published event. Diagnostics / debug_mode only."""
        self._assert_wildcard_allowed()
        with self._lock:
            self._wildcard.append(handler)

        def unsubscribe() -> None:
            with self._lock:
                if handler in self._wildcard:
                    self._wildcard.remove(handler)

        return unsubscribe

    def publish(self, topic: str, payload: dict[str, Any] | None = None, *, source: str = "system") -> Event:
        event = Event(topic=topic, payload=dict(payload or {}), source=source)
        with self._lock:
            handlers = list(self._wildcard)
            handlers.extend(self._subscribers.get(topic, []))
            if self._debug_mode:
                handlers.extend(self._subscribers.get(WILDCARD_TOPIC, []))

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
        return event

    def dispatch(self, event: Event) -> None:
        """Re-dispatch an existing event (e.g. from a queue)."""
        self.publish(event.topic, event.payload, source=event.source)
