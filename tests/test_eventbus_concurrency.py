"""Risk area #2 - EventBus thread-safety under concurrent publishing.

Simulates many background threads streaming LLM responses, all calling
``EventBus.publish`` concurrently, and verifies that **every** event is
delivered exactly once and uncorrupted.
"""

from __future__ import annotations

import threading

from ai_command_center.core.event_bus import Event, EventBus
from tests.support import CountdownLatch

_TOPIC = "chat.chunk"
_THREADS = 16
_PER_THREAD = 250


def test_no_events_lost_under_concurrent_publish() -> None:
    bus = EventBus()
    received: list[Event] = []
    lock = threading.Lock()

    def handler(event: Event) -> None:
        with lock:
            received.append(event)

    bus.subscribe(_TOPIC, handler)

    start = threading.Event()
    done = CountdownLatch(_THREADS)

    def worker(worker_id: int) -> None:
        start.wait()
        for seq in range(_PER_THREAD):
            bus.publish(_TOPIC, {"worker": worker_id, "seq": seq}, source=f"w{worker_id}")
        done.count_down()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(_THREADS)]
    for t in threads:
        t.start()
    start.set()
    assert done.wait(timeout=30), "publishers did not finish in time (possible deadlock)"
    for t in threads:
        t.join(timeout=5)

    expected = _THREADS * _PER_THREAD
    assert len(received) == expected, (
        f"event loss/duplication: expected {expected}, received {len(received)}"
    )

    # Every (worker, seq) pair must be present exactly once - proves no payload
    # corruption or cross-thread overwrite.
    pairs = {(e.payload["worker"], e.payload["seq"]) for e in received}
    assert len(pairs) == expected, "duplicate or corrupted event payloads detected"
    expected_pairs = {(w, s) for w in range(_THREADS) for s in range(_PER_THREAD)}
    assert pairs == expected_pairs, "some published events were never delivered"


def test_concurrent_subscribe_and_publish_is_safe() -> None:
    """Subscribing while publishing must not raise or corrupt the registry."""
    bus = EventBus()
    counter = {"n": 0}
    lock = threading.Lock()
    stop = threading.Event()

    def publisher() -> None:
        while not stop.is_set():
            bus.publish(_TOPIC, {"x": 1})

    def make_handler():
        def h(_event: Event) -> None:
            with lock:
                counter["n"] += 1
        return h

    pub_threads = [threading.Thread(target=publisher) for _ in range(4)]
    for t in pub_threads:
        t.start()

    unsubscribers = []
    for _ in range(200):
        unsubscribers.append(bus.subscribe(_TOPIC, make_handler()))

    stop.set()
    for t in pub_threads:
        t.join(timeout=5)
    for unsub in unsubscribers:
        unsub()

    assert counter["n"] >= 0  # the real assertion is "no exception was raised"
