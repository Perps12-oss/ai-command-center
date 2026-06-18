"""Thread-safe publish/subscribe event bus."""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

WILDCARD_TOPIC = "*"


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
            except Exception:
                continue
        return event

    def dispatch(self, event: Event) -> None:
        """Re-dispatch an existing event (e.g. from a queue)."""
        self.publish(event.topic, event.payload, source=event.source)
