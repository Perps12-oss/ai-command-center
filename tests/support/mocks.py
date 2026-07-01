"""Deterministic, network-free test doubles.

These mirror the public contracts of the real components closely enough to test
behaviour, while staying fast and side-effect free:

* :class:`RecordingEventBus` - a real :class:`EventBus` that also records every
  published event (thread-safe) so concurrency tests can assert nothing is lost.
* :class:`FakeOllamaClient` - returns canned / adversarial completions instead of
  calling Ollama over HTTP.
* :class:`StubLifecycleService` - a :class:`BaseService` with configurable
  start/stop latency (and an optional permanent hang) for lifecycle tests.
* :class:`CountdownLatch` - a tiny synchronisation primitive used to coordinate
  worker threads.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from typing import Any

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.services.base import BaseService


class CountdownLatch:
    """Block until ``count`` ``count_down()`` calls have occurred."""

    def __init__(self, count: int) -> None:
        if count < 0:
            raise ValueError("count must be non-negative")
        self._count = count
        self._lock = threading.Lock()
        self._event = threading.Event()
        if count == 0:
            self._event.set()

    def count_down(self, n: int = 1) -> None:
        with self._lock:
            self._count = max(0, self._count - n)
            if self._count == 0:
                self._event.set()

    @property
    def remaining(self) -> int:
        with self._lock:
            return self._count

    def wait(self, timeout: float | None = None) -> bool:
        return self._event.wait(timeout)


class RecordingEventBus(EventBus):
    """A real EventBus that also keeps a thread-safe log of published events."""

    def __init__(self, *, debug_mode: bool = False) -> None:
        super().__init__(debug_mode=debug_mode)
        self._recorded: list[Event] = []
        self._record_lock = threading.Lock()

    def publish(
        self,
        topic: str,
        payload: dict[str, Any] | None = None,
        *,
        source: str = "system",
    ) -> Event:
        event = super().publish(topic, payload, source=source)
        with self._record_lock:
            self._recorded.append(event)
        return event

    @property
    def recorded(self) -> list[Event]:
        with self._record_lock:
            return list(self._recorded)

    def events_for(self, topic: str) -> list[Event]:
        return [e for e in self.recorded if e.topic == topic]

    def clear(self) -> None:
        with self._record_lock:
            self._recorded.clear()


class FakeOllamaClient:
    """Stand-in for the Ollama HTTP client.

    Configure ``responses`` with the (possibly adversarial) text the model should
    "generate". Each call to :meth:`generate` returns the next queued response,
    repeating the last one once exhausted. :meth:`stream` yields it in chunks.
    """

    def __init__(self, responses: list[str] | None = None, *, chunk_size: int = 8) -> None:
        self._responses = list(responses or ["ok"])
        self._chunk_size = max(1, chunk_size)
        self._index = 0
        self.calls: list[dict[str, Any]] = []

    def _next(self, prompt: str, model: str) -> str:
        self.calls.append({"prompt": prompt, "model": model})
        if self._index < len(self._responses):
            text = self._responses[self._index]
            self._index += 1
        else:
            text = self._responses[-1]
        return text

    def generate(self, prompt: str, *, model: str = "fake-model") -> str:
        return self._next(prompt, model)

    def stream(self, prompt: str, *, model: str = "fake-model") -> Iterator[str]:
        text = self._next(prompt, model)
        for i in range(0, len(text), self._chunk_size):
            yield text[i : i + self._chunk_size]


class StubLifecycleService(BaseService):
    """Service with configurable lifecycle latency for deadlock/chaos tests."""

    def __init__(
        self,
        bus: EventBus,
        name: str = "stub",
        *,
        load_delay: float = 0.0,
        unload_delay: float = 0.0,
        hang_on_unload: bool = False,
    ) -> None:
        super().__init__(bus)
        self.name = name
        self._load_delay = load_delay
        self._unload_delay = unload_delay
        self._hang_on_unload = hang_on_unload
        self.load_count = 0
        self.unload_count = 0
        self._release = threading.Event()

    def _on_load(self) -> None:
        self.load_count += 1
        if self._load_delay:
            time.sleep(self._load_delay)

    def _on_unload(self) -> None:
        self.unload_count += 1
        if self._hang_on_unload:
            # Block until explicitly released (simulates a deadlocked teardown).
            self._release.wait()
            return
        if self._unload_delay:
            time.sleep(self._unload_delay)

    def release(self) -> None:
        """Unblock a hung unload so the test process can clean up."""
        self._release.set()
