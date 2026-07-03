"""Dispatch policy time budgets and exceedance log levels."""

from __future__ import annotations

from ai_command_center.core.events import topics as T
from ai_command_center.core.events.dispatch_policy import (
    budget_exceedance_is_warning,
    get_time_budget_ms,
)


def test_heavy_sync_standard_topics_have_recalibrated_budgets() -> None:
    assert get_time_budget_ms(T.SYSTEM_SNAPSHOT) >= 100
    assert get_time_budget_ms(T.OLLAMA_STATUS) >= 300
    assert get_time_budget_ms(T.CHAT_HISTORY_LOADED) >= 50


def test_streaming_topics_have_relaxed_budgets() -> None:
    assert get_time_budget_ms(T.CHAT_CHUNK) >= 200
    assert get_time_budget_ms(T.LLM_CHUNK) >= 200


def test_async_eligible_exceedance_logs_at_debug_only() -> None:
    assert not budget_exceedance_is_warning(T.CHAT_CHUNK)
    assert not budget_exceedance_is_warning(T.TELEMETRY_EVENT)


def test_sync_critical_exceedance_logs_as_warning() -> None:
    assert budget_exceedance_is_warning(T.UI_COMMAND)
    assert budget_exceedance_is_warning(T.UI_NAVIGATE)
