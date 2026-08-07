"""Tiered EventBus dispatch policy (Phase 5 — R4a–R4d).

Classifies ``ASYNC_ELIGIBLE`` topics onto worker pools without changing
``SYNC_CRITICAL`` membership (Performance Constitution Art. X).
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any

from ai_command_center.core.events.async_dispatch_queue import AsyncDispatchQueue
from ai_command_center.core.events.dispatch_policy import (
    DispatchPolicy,
    DispatchTier,
    SyncDispatchPolicy,
    get_dispatch_tier,
)


class DispatchPool(str, Enum):
    """Worker pool names aligned with ``PHASE_5_ASYNC_EVENTBUS_PLAN.md`` §5.4."""

    IMMEDIATE = "immediate"
    """R4a — sync on publisher / dispatch thread."""
    TOOL_EXECUTION = "tool_execution"
    """R4b — single-worker queue for tool topics."""
    WORKFLOW = "workflow"
    """R4c — thread pool for workflow / agent / notes / telemetry."""
    MODEL = "model"
    """R4d — dedicated queue for llm / chat / model topics."""


def classify_dispatch_pool(topic: str) -> DispatchPool:
    """Map *topic* to a dispatch pool.

    Only ``ASYNC_ELIGIBLE`` topics leave ``IMMEDIATE``. ``SYNC_CRITICAL`` and
    ``SYNC_STANDARD`` always stay immediate.
    """
    tier = get_dispatch_tier(topic)
    if tier is DispatchTier.SYNC_CRITICAL or tier is DispatchTier.SYNC_STANDARD:
        return DispatchPool.IMMEDIATE
    if topic.startswith("tool."):
        return DispatchPool.TOOL_EXECUTION
    if topic.startswith(("llm.", "chat.", "model.")):
        return DispatchPool.MODEL
    return DispatchPool.WORKFLOW


class TieredDispatchPolicy(DispatchPolicy):
    """Route handlers through ``AsyncDispatchQueue`` pools when not immediate."""

    def __init__(self, queue: AsyncDispatchQueue) -> None:
        self._queue = queue
        self._sync = SyncDispatchPolicy()

    def supports_async(self) -> bool:
        return True

    def classify_pool(self, topic: str) -> DispatchPool:
        return classify_dispatch_pool(topic)

    def dispatch(self, handler: Callable[[Any], None], event: Any) -> None:
        topic = getattr(event, "topic", "")
        pool = classify_dispatch_pool(topic)
        if pool is DispatchPool.IMMEDIATE:
            self._sync.dispatch(handler, event)
            return
        if not self._queue.enqueue(pool.value, event, handler):
            # Backpressure fallback: never drop SYNC work; run inline.
            self._sync.dispatch(handler, event)


__all__ = [
    "DispatchPool",
    "TieredDispatchPolicy",
    "classify_dispatch_pool",
]
