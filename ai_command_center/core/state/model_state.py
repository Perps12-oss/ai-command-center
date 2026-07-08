"""Model AppState reducers (Program 4 W4 partial)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import MODEL_SELECTED


@dataclass(frozen=True, slots=True)
class ModelSelectionSnapshot:
    """Projection of the latest model.selected event."""

    model: str = ""
    provider: str = ""
    intent: str = ""
    reason: str = ""
    routing_tier: str = ""
    capability_tier: str = ""
    workspace_id: str = ""
    selected_entity_type: str = ""
    selected_entity_id: str = ""
    resolved_by: str = ""


def _reduce_model_selected(state: Any, event: Event) -> Any:
    if event.topic != MODEL_SELECTED:
        return state
    payload = event.payload
    return replace(
        state,
        model_selection=ModelSelectionSnapshot(
            model=str(payload.get("model", "")),
            provider=str(payload.get("provider", "")),
            intent=str(payload.get("intent", "")),
            reason=str(payload.get("reason", "")),
            routing_tier=str(payload.get("routing_tier", "")),
            capability_tier=str(payload.get("capability_tier", payload.get("tier", ""))),
            workspace_id=str(payload.get("workspace_id", "")),
            selected_entity_type=str(payload.get("selected_entity_type", "")),
            selected_entity_id=str(payload.get("selected_entity_id", "")),
            resolved_by=str(payload.get("resolved_by", "")),
        ),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


MODEL_REDUCERS: tuple[Any, ...] = (_reduce_model_selected,)
