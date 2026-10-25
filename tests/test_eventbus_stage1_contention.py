"""Stream D Stage 1 contention report — pytest-facing assertions (IP-D)."""

from __future__ import annotations

from tools.eventbus_stage1_contention import (
    run_baseline_async,
    run_gate4_topic_mix,
    run_slow_async_vs_sync_critical,
)

SYNC_BUDGET_MS = 5.0
QUEUE_BUDGET = 100


def test_eventbus_stage1_baseline_fifo_and_depth() -> None:
    result = run_baseline_async(n=1500)
    assert result.fifo_ok is True
    assert result.dropped_events == 0
    assert result.peak_queue_depth < QUEUE_BUDGET * 20  # unbounded default; record only
    data = result.to_dict()
    assert data["handler_invocations"] >= 1500


def test_eventbus_stage1_sync_critical_not_starved_by_slow_async() -> None:
    """Isolation unlock condition: SYNC_CRITICAL p99 must stay within 5 ms."""
    result = run_slow_async_vs_sync_critical(n_async=80, n_sync=40, slow_ms=3.0)
    data = result.to_dict()
    assert result.dropped_events == 0
    assert data["sync_complete_p99_ms"] < SYNC_BUDGET_MS, data
    assert data["sync_complete_avg_ms"] < SYNC_BUDGET_MS, data


def test_eventbus_stage1_gate4_topic_mix_ui_command_budget() -> None:
    result = run_gate4_topic_mix(n=200)
    data = result.to_dict()
    assert result.dropped_events == 0
    assert result.fifo_ok is True
    assert data["sync_complete_p99_ms"] < SYNC_BUDGET_MS, data
