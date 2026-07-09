"""Artifact AppState reducers (ACC UI Refurbishment PR 6)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    ARTIFACT_CREATED,
    ARTIFACTS_LOADED,
    ARTIFACT_UPDATED,
)
from ai_command_center.domain.artifact import Artifact

_MAX_ARTIFACTS = 50


@dataclass(frozen=True, slots=True)
class ArtifactCatalogItem:
    """AppState projection for the artifact catalog and inspector."""

    artifact_id: str = ""
    kind: str = "text"
    label: str = ""
    content: str = ""
    size_bytes: int = 0
    mime_type: str = ""
    request_id: str = ""
    workspace_id: str = ""
    entity_id: str = ""
    source: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0

    @classmethod
    def from_artifact(cls, artifact: Artifact) -> ArtifactCatalogItem:
        return cls(
            artifact_id=artifact.artifact_id,
            kind=artifact.normalized_kind(),
            label=artifact.label,
            content=artifact.content,
            size_bytes=artifact.size_bytes,
            mime_type=artifact.mime_type,
            request_id=artifact.request_id,
            workspace_id=artifact.workspace_id,
            entity_id=artifact.entity_id,
            source=artifact.source,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
        )

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ArtifactCatalogItem:
        return cls.from_artifact(Artifact.from_bus_payload(payload))


def _parse_catalog(payload: dict[str, Any]) -> tuple[ArtifactCatalogItem, ...]:
    raw = payload.get("artifacts") or []
    items: list[ArtifactCatalogItem] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        item = ArtifactCatalogItem.from_payload(entry)
        if item.artifact_id:
            items.append(item)
    return tuple(items)


def _upsert_catalog(
    catalog: tuple[ArtifactCatalogItem, ...],
    item: ArtifactCatalogItem,
) -> tuple[ArtifactCatalogItem, ...]:
    filtered = tuple(a for a in catalog if a.artifact_id != item.artifact_id)
    updated = (item,) + filtered
    if len(updated) > _MAX_ARTIFACTS:
        updated = updated[:_MAX_ARTIFACTS]
    return updated


def _reduce_artifact_created(state: Any, event: Event) -> Any:
    if event.topic != ARTIFACT_CREATED:
        return state
    item = ArtifactCatalogItem.from_payload(event.payload)
    if not item.artifact_id:
        return state
    return replace(
        state,
        recent_artifacts=_upsert_catalog(state.recent_artifacts, item),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_artifact_updated(state: Any, event: Event) -> Any:
    if event.topic != ARTIFACT_UPDATED:
        return state
    item = ArtifactCatalogItem.from_payload(event.payload)
    if not item.artifact_id:
        return state
    return replace(
        state,
        recent_artifacts=_upsert_catalog(state.recent_artifacts, item),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_artifacts_loaded(state: Any, event: Event) -> Any:
    if event.topic != ARTIFACTS_LOADED:
        return state
    catalog = _parse_catalog(event.payload)
    if not catalog:
        return state
    return replace(
        state,
        recent_artifacts=catalog[-_MAX_ARTIFACTS:],
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


ARTIFACT_REDUCERS: tuple[Any, ...] = (
    _reduce_artifact_created,
    _reduce_artifact_updated,
    _reduce_artifacts_loaded,
)

__all__ = [
    "ARTIFACT_REDUCERS",
    "ArtifactCatalogItem",
]
