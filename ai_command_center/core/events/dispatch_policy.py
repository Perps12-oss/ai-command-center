"""EventBus dispatch policy — topic classification for R4 async migration.

This module is **policy only** in R4a: constants and enums for documentation,
verification, and future enforcement. It does not change ``EventBus.publish()``
semantics.

Full design: ``docs/architecture/ASYNC_EVENTBUS_POLICY.md``
"""

from __future__ import annotations

from enum import Enum

from ai_command_center.core.events import topics as T

# Handler time budgets (milliseconds) on the bus/dispatch thread — design targets.
SYNC_CRITICAL_BUDGET_MS = 5
SYNC_STANDARD_BUDGET_MS = 10
ASYNC_ENQUEUE_BUDGET_MS = 1

# Per-topic overrides for handlers that legitimately exceed tier defaults while
# still running synchronously (AppState reduction, status polling, UI-adjacent work).
TOPIC_TIME_BUDGET_MS: dict[str, int] = {
    T.SYSTEM_SNAPSHOT: 150,
    T.OLLAMA_STATUS: 350,
    T.OPENAI_STATUS: 350,
    T.CHAT_HISTORY_LOADED: 50,
    T.CHAT_CHUNK: 250,
    T.LLM_CHUNK: 250,
    T.UI_NAVIGATE: 10,
}


class DispatchTier(str, Enum):
    """How a topic's handlers may be executed under R4 dispatch policy."""

    SYNC_CRITICAL = "sync_critical"
    """Must run synchronously on dispatch thread; ordering matters."""
    SYNC_STANDARD = "sync_standard"
    """Synchronous; eventual async dispatch allowed only with explicit flag."""
    ASYNC_ELIGIBLE = "async_eligible"
    """May be queued to central dispatch worker (R4b+)."""


# Topics that MUST remain synchronous through R4c (see ASYNC_EVENTBUS_POLICY.md).
SYNC_CRITICAL_TOPICS: frozenset[str] = frozenset(
    {
        T.SETTINGS_SNAPSHOT,
        T.SETTINGS_CHANGED,
        T.SETTINGS_UPDATED,
        T.SETTINGS_SET_REQUEST,
        T.SERVICE_STARTED,
        T.SERVICE_READY,
        T.SERVICE_STOPPED,
        T.SERVICE_ERROR,
        T.SERVICE_STATE_CHANGED,
        T.BUS_HANDLER_ERROR,
        T.UI_COMMAND,
        T.UI_NAVIGATE,
        T.COMMAND_ROUTED,
    }
)

# Topics that MAY move to async central dispatch (R4b+).
ASYNC_ELIGIBLE_TOPICS: frozenset[str] = frozenset(
    {
        T.TOOL_INVOKE,
        T.NOTE_INDEX_PROGRESS,
        T.NOTE_INDEX_COMPLETE,
        T.NOTES_INDEXED,
        T.NOTE_SEARCH_RESULTS,
        T.CHAT_CHUNK,
        T.CHAT_COMPLETE,
        T.CHAT_STARTED,
        T.CHAT_ERROR,
        T.LLM_CHUNK,
        T.LLM_COMPLETE,
        T.LLM_ERROR,
        T.TOOL_STARTED,
        T.TOOL_COMPLETED,
        T.TOOL_FAILED,
        T.TOOL_RESULT,
        T.TELEMETRY_EVENT,
        T.MEMORY_LOOKUP_RESULT,
        T.MEMORY_STORED,
        T.AGENT_SPAWNED,
        T.AGENT_TASK_COMPLETE,
        T.AGENT_TERMINATED,
        T.AGENT_PIPELINE_STARTED,
        T.AGENT_PIPELINE_STAGE,
        T.AGENT_PIPELINE_PLANNED,
        T.AGENT_PIPELINE_COMPLETE,
        T.WORKFLOW_STARTED,
        T.WORKFLOW_STEP_STARTED,
        T.WORKFLOW_STEP_COMPLETED,
        T.WORKFLOW_COMPLETED,
        T.WORKFLOW_FAILED,
    }
)

_TOPIC_TIER: dict[str, DispatchTier] = {
    **{t: DispatchTier.SYNC_CRITICAL for t in SYNC_CRITICAL_TOPICS},
    **{t: DispatchTier.ASYNC_ELIGIBLE for t in ASYNC_ELIGIBLE_TOPICS},
}


def get_dispatch_tier(topic: str) -> DispatchTier:
    """Return the dispatch tier for a topic; default SYNC_STANDARD."""
    return _TOPIC_TIER.get(topic, DispatchTier.SYNC_STANDARD)


def get_time_budget_ms(topic: str) -> int:
    """Return recommended handler time budget for *topic* (design target only)."""
    override = TOPIC_TIME_BUDGET_MS.get(topic)
    if override is not None:
        return override
    tier = get_dispatch_tier(topic)
    if tier is DispatchTier.SYNC_CRITICAL:
        return SYNC_CRITICAL_BUDGET_MS
    if tier is DispatchTier.ASYNC_ELIGIBLE:
        return ASYNC_ENQUEUE_BUDGET_MS
    return SYNC_STANDARD_BUDGET_MS


def budget_exceedance_is_warning(topic: str) -> bool:
    """Return True when a budget exceedance should log at WARNING level.

    ASYNC_ELIGIBLE topics may still run inline on the sync path until R4b+
    async dispatch is enabled; those exceedances are DEBUG-only to avoid spam.
    """
    return get_dispatch_tier(topic) is not DispatchTier.ASYNC_ELIGIBLE


__all__ = [
    "ASYNC_ELIGIBLE_TOPICS",
    "ASYNC_ENQUEUE_BUDGET_MS",
    "DispatchTier",
    "SYNC_CRITICAL_BUDGET_MS",
    "SYNC_CRITICAL_TOPICS",
    "SYNC_STANDARD_BUDGET_MS",
    "TOPIC_TIME_BUDGET_MS",
    "budget_exceedance_is_warning",
    "get_dispatch_tier",
    "get_time_budget_ms",
]
