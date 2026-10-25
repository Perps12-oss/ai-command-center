"""Stream D Stage 1 — EventBus contention / burst / starvation harness (IP-D §11).

Measurement only. Does not change dispatch policy or introduce pools.
Linux/CI results are headless and must not be used as Windows GUI budget close-out
(PERFORMANCE_CONSTITUTION Art. V).
"""

from __future__ import annotations

import statistics
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    AUTONOMY_SCORE_UPDATED,
    CHAT_CHUNK,
    DECISION_RECORD_UPDATED,
    FEDERATION_QUERY_REQUEST,
    MODEL_SELECTED,
    UI_COMMAND,
)


@dataclass
class ScenarioResult:
    name: str
    n_async: int = 0
    n_sync: int = 0
    peak_queue_depth: int = 0
    dropped_events: int = 0
    handler_invocations: int = 0
    handler_duration_avg_ms: float = 0.0
    publish_ms: list[float] = field(default_factory=list)
    sync_complete_ms: list[float] = field(default_factory=list)
    async_drain_ms: float = 0.0
    fifo_ok: bool | None = None
    notes: str = ""

    def percentile(self, values: list[float], p: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        idx = min(len(ordered) - 1, max(0, int(round((p / 100.0) * (len(ordered) - 1)))))
        return ordered[idx]

    def to_dict(self) -> dict[str, Any]:
        pub = self.publish_ms
        sync = self.sync_complete_ms
        return {
            "name": self.name,
            "n_async": self.n_async,
            "n_sync": self.n_sync,
            "peak_queue_depth": self.peak_queue_depth,
            "dropped_events": self.dropped_events,
            "handler_invocations": self.handler_invocations,
            "handler_duration_avg_ms": round(self.handler_duration_avg_ms, 4),
            "publish_avg_ms": round(statistics.fmean(pub), 4) if pub else 0.0,
            "publish_p99_ms": round(self.percentile(pub, 99), 4),
            "sync_complete_avg_ms": round(statistics.fmean(sync), 4) if sync else 0.0,
            "sync_complete_p99_ms": round(self.percentile(sync, 99), 4),
            "async_drain_ms": round(self.async_drain_ms, 4),
            "fifo_ok": self.fifo_ok,
            "notes": self.notes,
        }


def _wait_idle(bus: EventBus, *, timeout_s: float = 5.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if bus.dispatch_queue_depth == 0:
            return
        time.sleep(0.001)


def run_baseline_async(n: int = 2000) -> ScenarioResult:
    """Fast ASYNC_ELIGIBLE handlers; record publish cost and drain."""
    bus = EventBus(async_dispatch=True)
    received: list[int] = []
    done = threading.Event()
    peak = 0

    def handler(event) -> None:
        received.append(int(event.payload["seq"]))
        if len(received) == n:
            done.set()

    bus.subscribe(CHAT_CHUNK, handler)
    result = ScenarioResult(name="baseline_async_fast", n_async=n)
    t0 = time.perf_counter()
    for seq in range(n):
        t_pub = time.perf_counter()
        bus.publish(CHAT_CHUNK, {"seq": seq}, source="stage1")
        result.publish_ms.append((time.perf_counter() - t_pub) * 1000.0)
        peak = max(peak, bus.dispatch_queue_depth)
    assert done.wait(timeout=10.0)
    result.async_drain_ms = (time.perf_counter() - t0) * 1000.0
    result.peak_queue_depth = peak
    result.fifo_ok = received == list(range(n))
    metrics = bus.get_handler_metrics()
    result.handler_invocations = int(metrics["handler_invocations"])
    result.handler_duration_avg_ms = float(metrics["handler_duration_avg_ms"])
    result.dropped_events = int(metrics["dropped_events"])
    bus.shutdown()
    return result


def run_slow_async_vs_sync_critical(
    n_async: int = 200,
    n_sync: int = 50,
    slow_ms: float = 2.0,
) -> ScenarioResult:
    """Slow async handlers on the dispatch worker; SYNC_CRITICAL must stay inline.

    If UI_COMMAND completion stays within the 5 ms sync budget while CHAT_CHUNK
    is slow, single-queue isolation is not justified by starvation.
    """
    bus = EventBus(async_dispatch=True)
    async_done = threading.Event()
    async_count = 0
    lock = threading.Lock()
    peak = 0

    def slow_chunk(_event) -> None:
        nonlocal async_count
        time.sleep(slow_ms / 1000.0)
        with lock:
            async_count += 1
            if async_count >= n_async:
                async_done.set()

    bus.subscribe(CHAT_CHUNK, slow_chunk)
    bus.subscribe(UI_COMMAND, lambda _e: None)

    result = ScenarioResult(
        name="slow_async_vs_sync_critical",
        n_async=n_async,
        n_sync=n_sync,
        notes=f"slow_handler={slow_ms}ms",
    )
    for seq in range(n_async):
        bus.publish(CHAT_CHUNK, {"seq": seq}, source="stage1")
        peak = max(peak, bus.dispatch_queue_depth)

    for i in range(n_sync):
        t0 = time.perf_counter()
        bus.publish(UI_COMMAND, {"text": f"cmd-{i}"}, source="stage1")
        result.sync_complete_ms.append((time.perf_counter() - t0) * 1000.0)
        peak = max(peak, bus.dispatch_queue_depth)

    assert async_done.wait(timeout=30.0)
    result.peak_queue_depth = peak
    metrics = bus.get_handler_metrics()
    result.handler_invocations = int(metrics["handler_invocations"])
    result.handler_duration_avg_ms = float(metrics["handler_duration_avg_ms"])
    result.dropped_events = int(metrics["dropped_events"])
    bus.shutdown()
    return result


def run_gate4_topic_mix(n: int = 400) -> ScenarioResult:
    """Burst of Gate 4 emission topics plus UI_COMMAND (post A/B/C/E load)."""
    bus = EventBus(async_dispatch=True)
    counts = {DECISION_RECORD_UPDATED: 0, AUTONOMY_SCORE_UPDATED: 0, MODEL_SELECTED: 0}
    lock = threading.Lock()
    remaining = {"n": n * 3}
    done = threading.Event()

    def _count(topic: str):
        def handler(_event) -> None:
            with lock:
                counts[topic] += 1
                remaining["n"] -= 1
                if remaining["n"] <= 0:
                    done.set()

        return handler

    for topic in counts:
        bus.subscribe(topic, _count(topic))
    bus.subscribe(FEDERATION_QUERY_REQUEST, lambda _e: None)
    bus.subscribe(UI_COMMAND, lambda _e: None)

    result = ScenarioResult(name="gate4_topic_mix", n_async=n * 3, n_sync=n)
    peak = 0
    for i in range(n):
        t0 = time.perf_counter()
        bus.publish(DECISION_RECORD_UPDATED, {"record_id": str(i)}, source="stage1")
        bus.publish(AUTONOMY_SCORE_UPDATED, {"aggregate": 0.8, "band": "low"}, source="stage1")
        bus.publish(MODEL_SELECTED, {"model": "llama3.2:3b", "reason": "default"}, source="stage1")
        bus.publish(FEDERATION_QUERY_REQUEST, {"request_id": str(i), "query": ""}, source="stage1")
        t_sync = time.perf_counter()
        bus.publish(UI_COMMAND, {"text": "goal: mix"}, source="stage1")
        result.sync_complete_ms.append((time.perf_counter() - t_sync) * 1000.0)
        result.publish_ms.append((time.perf_counter() - t0) * 1000.0)
        peak = max(peak, bus.dispatch_queue_depth)

    assert done.wait(timeout=10.0)
    _wait_idle(bus)
    result.peak_queue_depth = peak
    result.fifo_ok = counts[DECISION_RECORD_UPDATED] == n
    metrics = bus.get_handler_metrics()
    result.handler_invocations = int(metrics["handler_invocations"])
    result.handler_duration_avg_ms = float(metrics["handler_duration_avg_ms"])
    result.dropped_events = int(metrics["dropped_events"])
    bus.shutdown()
    return result


def run_all() -> dict[str, Any]:
    scenarios = [
        run_baseline_async(),
        run_slow_async_vs_sync_critical(),
        run_gate4_topic_mix(),
    ]
    payload = {
        "host": "linux-headless",
        "gui_claims_valid": False,
        "budgets": {
            "publish_ms": 0.2,
            "sync_handler_ms": 5.0,
            "queue_depth": 100,
        },
        "scenarios": [s.to_dict() for s in scenarios],
    }
    return payload


def main() -> None:
    import json
    import sys

    json.dump(run_all(), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
