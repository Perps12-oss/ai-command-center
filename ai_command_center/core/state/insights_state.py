"""Insights workspace state projection (PR-UI-E13 placeholder).

Reserves an AppState slot for Phase 10+ insights without implementing
analytics. The reducer tracks open/select/refresh intents only.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    UI_INSIGHTS_OPEN,
    UI_INSIGHTS_REFRESH,
    UI_INSIGHTS_SELECT,
)


@dataclass(frozen=True, slots=True)
class InsightsSnapshot:
    """Placeholder projection for the Insights workspace."""

    status: str = "placeholder"
    message: str = (
        "Insights will summarize patterns across goals, agents, "
        "evidence, and world-model activity in a later phase."
    )
    selected_insight_id: str = ""
    revision: int = 0


def reduce_insights_state(state: Any, event: Event) -> Any:
    """Update the insights_state field on AppState from UI intents."""
    if not hasattr(state, "insights_state"):
        return state

    current: InsightsSnapshot = state.insights_state
    topic = event.topic
    payload = event.payload or {}

    if topic == UI_INSIGHTS_OPEN:
        new = replace(
            current,
            status="placeholder",
            revision=current.revision + 1,
        )
        return replace(state, insights_state=new)

    if topic == UI_INSIGHTS_SELECT:
        insight_id = str(payload.get("insight_id", "")).strip()
        new = replace(
            current,
            selected_insight_id=insight_id,
            revision=current.revision + 1,
        )
        return replace(state, insights_state=new)

    if topic == UI_INSIGHTS_REFRESH:
        new = replace(
            current,
            status="placeholder",
            revision=current.revision + 1,
        )
        return replace(state, insights_state=new)

    return state


__all__ = ["InsightsSnapshot", "reduce_insights_state"]
