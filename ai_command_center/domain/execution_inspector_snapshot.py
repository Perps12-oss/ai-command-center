"""Domain snapshot for execution inspector projection."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from ai_command_center.core.state.execution_event_state import (
    ExecutionEventItem,
    ExecutionScrubberState,
)
from ai_command_center.core.state.execution_state import ExecutionContext
from ai_command_center.core.state.execution_timeline_state import ExecutionTimelineState
from ai_command_center.domain.brain_state_snapshot import PlanSnapshot

_MAX_RECENT_EXECUTION_EVENTS = 100


@dataclass(frozen=True, slots=True)
class ExecutionInspectorSnapshot:
    """Consolidated immutable execution diagnostic view."""

    execution_context: ExecutionContext = field(default_factory=ExecutionContext)
    execution_scrubber: ExecutionScrubberState = field(default_factory=ExecutionScrubberState)
    execution_timeline: ExecutionTimelineState = field(default_factory=ExecutionTimelineState)
    recent_execution_events: tuple[ExecutionEventItem, ...] = ()
    planner_last_plan: PlanSnapshot = field(default_factory=PlanSnapshot)
    revision: int = 0

    @classmethod
    def from_components(
        cls,
        *,
        execution_context: ExecutionContext,
        execution_scrubber: ExecutionScrubberState,
        execution_timeline: ExecutionTimelineState,
        recent_execution_events: tuple[ExecutionEventItem, ...],
        planner_last_plan: PlanSnapshot,
        revision: int,
    ) -> "ExecutionInspectorSnapshot":
        """Create a normalized snapshot from the current AppState slices."""
        events = recent_execution_events[:_MAX_RECENT_EXECUTION_EVENTS]
        return cls(
            execution_context=execution_context,
            execution_scrubber=execution_scrubber,
            execution_timeline=execution_timeline,
            recent_execution_events=events,
            planner_last_plan=planner_last_plan,
            revision=revision,
        )

    def with_revision(self, revision: int) -> "ExecutionInspectorSnapshot":
        return replace(self, revision=revision)

