"""Artifact catalog service — bus-only facade over ArtifactRepository."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    ARTIFACT_CREATED,
    ARTIFACTS_LOADED,
    ARTIFACT_UPDATED,
    CHAT_COMPLETE,
    TOOL_RESULT,
    UI_ARTIFACT_ACTION,
)
from ai_command_center.domain.artifact import (
    Artifact,
    infer_chat_artifact_kind,
    infer_tool_artifact_kind,
)
from ai_command_center.repositories.artifact_repository import ArtifactRepository
from ai_command_center.services.base import BaseService

_MAX_LABEL = 120


class ArtifactService(BaseService):
    """Persists artifacts and publishes catalog events to the EventBus."""

    name = "artifact"

    def __init__(self, bus, *, repo: ArtifactRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(TOOL_RESULT, self._on_tool_result)
        )
        self._unsubscribers.append(
            self._bus.subscribe(CHAT_COMPLETE, self._on_chat_complete)
        )
        self._unsubscribers.append(
            self._bus.subscribe(UI_ARTIFACT_ACTION, self._on_ui_artifact_action)
        )
        self._publish_recent_artifacts()

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _publish_recent_artifacts(self) -> None:
        artifacts = self._repo.list_recent()
        if not artifacts:
            return
        self._bus.publish(
            ARTIFACTS_LOADED,
            {"artifacts": [artifact.to_bus_payload() for artifact in artifacts]},
            source=self.name,
        )

    def _publish_created(self, artifact: Artifact) -> None:
        self._bus.publish(
            ARTIFACT_CREATED,
            artifact.to_bus_payload(),
            source=self.name,
        )

    def _publish_updated(self, artifact: Artifact) -> None:
        self._bus.publish(
            ARTIFACT_UPDATED,
            artifact.to_bus_payload(),
            source=self.name,
        )

    @staticmethod
    def _scope_from_payload(payload: dict) -> tuple[str, str, str]:
        request_id = str(payload.get("request_id", "")).strip()
        workspace_id = str(payload.get("workspace_id", "")).strip()
        entity_id = str(payload.get("entity_id", "")).strip()
        workspace_context = payload.get("workspace_context")
        if isinstance(workspace_context, dict):
            workspace_id = workspace_id or str(
                workspace_context.get("workspace_id", "")
            ).strip()
            entity_id = entity_id or str(workspace_context.get("entity_id", "")).strip()
        return request_id, workspace_id, entity_id

    def _on_tool_result(self, event: Event) -> None:
        payload = event.payload
        if not bool(payload.get("success", False)):
            return
        output = str(payload.get("output", "")).strip()
        if not output:
            return
        tool_name = str(payload.get("tool", "tool")).strip() or "tool"
        invoke_id = str(payload.get("invoke_id", "")).strip()
        request_id, workspace_id, entity_id = self._scope_from_payload(payload)
        artifact_id = f"tool:{invoke_id or uuid.uuid4().hex}"
        label = f"{tool_name} output"
        if len(output) > _MAX_LABEL:
            label = f"{tool_name}: {output[:_MAX_LABEL - 3]}..."
        artifact = self._repo.insert(
            Artifact(
                artifact_id=artifact_id,
                kind=infer_tool_artifact_kind(tool_name),
                label=label,
                content=output,
                size_bytes=len(output.encode("utf-8")),
                request_id=request_id,
                workspace_id=workspace_id,
                entity_id=entity_id,
                source="tool",
            )
        )
        self._publish_created(artifact)

    def _on_chat_complete(self, event: Event) -> None:
        payload = event.payload
        if payload.get("orchestration"):
            return
        text = str(payload.get("text", "")).strip()
        if not text:
            return
        request_id, workspace_id, entity_id = self._scope_from_payload(payload)
        if not request_id:
            request_id = str(payload.get("request_id", "")).strip()
        artifact_id = f"chat:{request_id or uuid.uuid4().hex}"
        label = text[:_MAX_LABEL]
        if len(text) > _MAX_LABEL:
            label = f"{label[:-3]}..."
        artifact = self._repo.insert(
            Artifact(
                artifact_id=artifact_id,
                kind=infer_chat_artifact_kind(text),
                label=label or "Assistant response",
                content=text,
                size_bytes=len(text.encode("utf-8")),
                request_id=request_id,
                workspace_id=workspace_id,
                entity_id=entity_id,
                source="chat",
            )
        )
        self._publish_created(artifact)

    def _on_ui_artifact_action(self, event: Event) -> None:
        payload = event.payload
        action = str(payload.get("action", "")).strip().lower()
        artifact_id = str(payload.get("artifact_id", "")).strip()
        if not artifact_id:
            return
        if action not in {"preview", "open", "refresh"}:
            return
        artifact = self._repo.get(artifact_id)
        if artifact is None:
            return
        self._publish_updated(
            Artifact(
                artifact_id=artifact.artifact_id,
                kind=artifact.kind,
                label=artifact.label,
                content=artifact.content,
                size_bytes=artifact.size_bytes,
                mime_type=artifact.mime_type,
                request_id=artifact.request_id,
                workspace_id=artifact.workspace_id,
                entity_id=artifact.entity_id,
                source=artifact.source,
                created_at=artifact.created_at,
                updated_at=time.time(),
            )
        )
