"""Process-wide performance counters (thread-safe, observation only)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TimingSample:
    name: str
    elapsed_ms: float
    at: float


class PerfMetrics:
    """Ring-buffer timings + counters for EventBus / AppState / UI / SQLite."""

    def __init__(self, *, maxlen: int = 256) -> None:
        self._lock = threading.Lock()
        self._samples: deque[TimingSample] = deque(maxlen=maxlen)
        self._counters: dict[str, int] = defaultdict(int)
        self._last_ms: dict[str, float] = {}
        self._started = time.time()

    def record(self, name: str, elapsed_ms: float) -> None:
        with self._lock:
            self._samples.append(
                TimingSample(name=name, elapsed_ms=float(elapsed_ms), at=time.time())
            )
            self._last_ms[name] = float(elapsed_ms)
            self._counters[f"{name}.count"] += 1

    def incr(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] += amount

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            by_name: dict[str, list[float]] = defaultdict(list)
            for sample in self._samples:
                by_name[sample.name].append(sample.elapsed_ms)
            summaries: dict[str, dict[str, float]] = {}
            for name, values in by_name.items():
                summaries[name] = {
                    "last_ms": self._last_ms.get(name, 0.0),
                    "avg_ms": sum(values) / len(values),
                    "max_ms": max(values),
                    "n": float(len(values)),
                }
            return {
                "uptime_s": round(time.time() - self._started, 1),
                "counters": dict(self._counters),
                "timings": summaries,
            }


_METRICS = PerfMetrics()


def get_perf_metrics() -> PerfMetrics:
    return _METRICS
