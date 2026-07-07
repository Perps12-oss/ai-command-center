"""ArtifactService — bus-native artifact persistence and lifecycle events.

Subscribes to artifact.create.request / artifact.update.request, persists via
ArtifactRepository, and publishes artifact.created / artifact.updated.

Architecture contract
─────────────────────
• Does NOT call other services directly (Rule 3).
• Repositories own storage; this service never touches SQLite from callers.
• UI actions use ui.artifact.action (existing topic); persistence uses request topics.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import (
    ARTIFACT_CREATE_REQUEST,
    ARTIFACT_CREATED,
    ARTIFACT_UPDATE_REQUEST,
    ARTIFACT_UPDATED,
)
from ai_command_center.domain.artifact import ArtifactType
from ai_command_center.repositories.artifact_repository import ArtifactRepository
from ai_command_center.services.base import BaseService

logger = logging.getLogger(__name__)


class ArtifactService(BaseService):
    """Handles artifact create/update requests and publishes lifecycle events."""

    name = "artifact"

    def __init__(self, bus: EventBus, *, repo: ArtifactRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(ARTIFACT_CREATE_REQUEST, self._on_create_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(ARTIFACT_UPDATE_REQUEST, self._on_update_request)
        )
        logger.info("[ArtifactService] ready")

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_create_request(self, event: Event) -> None:
        payload = dict(event.payload) if event.payload else {}
        label = str(payload.get("label", "")).strip()
        if not label:
            logger.warning("[ArtifactService] create request missing label")
            return
        artifact = self._repo.create(
            kind=str(payload.get("kind", ArtifactType.TEXT.value)),
            label=label,
            size_bytes=int(payload.get("size_bytes", 0) or 0),
            content_ref=str(payload.get("content_ref", "")),
            execution_id=str(payload.get("execution_id", "")),
            mime_type=str(payload.get("mime_type", "")),
            artifact_id=str(payload.get("artifact_id", "")),
        )
        self._bus.publish(ARTIFACT_CREATED, artifact.to_dict(), source=self.name)

    def _on_update_request(self, event: Event) -> None:
        payload = dict(event.payload) if event.payload else {}
        artifact_id = str(payload.get("artifact_id", "")).strip()
        if not artifact_id:
            logger.warning("[ArtifactService] update request missing artifact_id")
            return
        updated = self._repo.update(
            artifact_id,
            label=payload.get("label"),
            size_bytes=payload.get("size_bytes"),
            content_ref=payload.get("content_ref"),
            mime_type=payload.get("mime_type"),
        )
        if updated is None:
            logger.warning("[ArtifactService] artifact not found: %s", artifact_id)
            return
        self._bus.publish(ARTIFACT_UPDATED, updated.to_dict(), source=self.name)


__all__ = ["ArtifactService"]
