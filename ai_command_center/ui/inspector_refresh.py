"""Shared timing helpers for developer inspector refresh paths (PERF-002)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from ai_command_center.core.perf.metrics import get_perf_metrics

T = TypeVar("T")


def record_inspector_refresh(name: str, elapsed_ms: float, *, skipped: bool = False) -> None:
    """Record ``inspector.refresh.<name>`` timing; count fingerprint skips."""
    metrics = get_perf_metrics()
    if skipped:
        metrics.incr(f"inspector.refresh.{name}.skipped")
        return
    metrics.record(f"inspector.refresh.{name}", elapsed_ms)


def timed_inspector_refresh(name: str, work: Callable[[], T]) -> T:
    """Run refresh work and record wall-clock ms under ``inspector.refresh.<name>``."""
    started = time.perf_counter()
    result = work()
    record_inspector_refresh(name, (time.perf_counter() - started) * 1000.0)
    return result
