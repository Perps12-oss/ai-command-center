"""InspectorState reducer for the global inspector selection rail."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    UI_INSPECT_CLEAR,
    UI_INSPECT_NAVIGATE,
    UI_INSPECT_SELECT,
)
from ai_command_center.domain.inspectable import InspectableRef


@dataclass(frozen=True, slots=True)
class InspectorState:
    """Presentation state for the global inspector."""

    selected: InspectableRef | None = None
    collapsed: bool = False
    revision: int = 0


def _parse_inspect_ref(payload: dict[str, Any]) -> InspectableRef | None:
    ref = InspectableRef.from_payload(payload)
    if not ref.kind or not ref.ref_id:
        return None
    return ref


def reduce_inspector_state(state: InspectorState, event: Event) -> InspectorState:
    """Pure reducer for inspector selection intents."""
    if event.topic == UI_INSPECT_SELECT:
        ref = _parse_inspect_ref(event.payload)
        if ref is None or ref == state.selected:
            return state
        return replace(state, selected=ref, revision=state.revision + 1)
    if event.topic == UI_INSPECT_CLEAR:
        if state.selected is None:
            return state
        return replace(state, selected=None, revision=state.revision + 1)
    if event.topic == UI_INSPECT_NAVIGATE:
        return state
    return state


__all__ = ["InspectorState", "reduce_inspector_state"]
