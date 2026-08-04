"""Shared timing helpers for developer inspector refresh paths (PERF-002)."""

from __future__ import annotations

from ai_command_center.core.perf.metrics import get_perf_metrics


def record_inspector_refresh(name: str, elapsed_ms: float, *, skipped: bool = False) -> None:
    """Record ``inspector.refresh.<name>`` timing; count fingerprint skips."""
    metrics = get_perf_metrics()
    if skipped:
        metrics.incr(f"inspector.refresh.{name}.skipped")
        return
    metrics.record(f"inspector.refresh.{name}", elapsed_ms)
