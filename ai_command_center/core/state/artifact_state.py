"""ArtifactState reducer projecting recent_artifacts for AppState."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import ARTIFACT_CREATED, ARTIFACT_UPDATED
from ai_command_center.domain.artifact import ArtifactType

_MAX_RECENT_ARTIFACTS = 50


@dataclass(frozen=True, slots=True)
class ArtifactStateItem:
    """Projection of an artifact for AppState feeds."""

    artifact_id: str = ""
    kind: str = "text"
    label: str = ""
    size_bytes: int = 0
    content_ref: str = ""
    execution_id: str = ""
    mime_type: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0


def artifact_state_item_from_payload(payload: dict[str, Any]) -> ArtifactStateItem | None:
    artifact_id = str(payload.get("artifact_id", "")).strip()
    if not artifact_id:
        return None
    kind = ArtifactType.coerce(str(payload.get("kind", "text"))).value
    return ArtifactStateItem(
        artifact_id=artifact_id,
        kind=kind,
        label=str(payload.get("label", "")),
        size_bytes=int(payload.get("size_bytes", 0) or 0),
        content_ref=str(payload.get("content_ref", "")),
        execution_id=str(payload.get("execution_id", "")),
        mime_type=str(payload.get("mime_type", "")),
        created_at=float(payload.get("created_at", 0.0) or 0.0),
        updated_at=float(payload.get("updated_at", 0.0) or 0.0),
    )


def _upsert_recent(
    artifacts: tuple[ArtifactStateItem, ...],
    item: ArtifactStateItem,
) -> tuple[ArtifactStateItem, ...]:
    filtered = tuple(a for a in artifacts if a.artifact_id != item.artifact_id)
    updated = (item,) + filtered
    if len(updated) > _MAX_RECENT_ARTIFACTS:
        updated = updated[:_MAX_RECENT_ARTIFACTS]
    return updated


def reduce_artifact_created(state: Any, event: Event) -> Any:
    if event.topic != ARTIFACT_CREATED:
        return state
    item = artifact_state_item_from_payload(dict(event.payload))
    if item is None:
        return state
    return replace(
        state,
        recent_artifacts=_upsert_recent(state.recent_artifacts, item),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def reduce_artifact_updated(state: Any, event: Event) -> Any:
    if event.topic != ARTIFACT_UPDATED:
        return state
    item = artifact_state_item_from_payload(dict(event.payload))
    if item is None:
        return state
    return replace(
        state,
        recent_artifacts=_upsert_recent(state.recent_artifacts, item),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


ARTIFACT_REDUCERS: tuple[Any, ...] = (
    reduce_artifact_created,
    reduce_artifact_updated,
)


__all__ = [
    "ArtifactStateItem",
    "ARTIFACT_REDUCERS",
    "artifact_state_item_from_payload",
    "reduce_artifact_created",
    "reduce_artifact_updated",
]
