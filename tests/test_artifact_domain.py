"""Artifact domain contract tests."""

from __future__ import annotations

from ai_command_center.domain.artifact import (
    Artifact,
    ArtifactType,
    infer_chat_artifact_kind,
    infer_tool_artifact_kind,
)


def test_artifact_round_trips_bus_payload() -> None:
    artifact = Artifact(
        artifact_id="art-1",
        kind=ArtifactType.MARKDOWN.value,
        label="Summary",
        content="# Title",
        size_bytes=7,
        request_id="req-1",
        workspace_id="ws-1",
        entity_id="ent-1",
        source="chat",
        created_at=1.0,
        updated_at=2.0,
    )
    payload = artifact.to_bus_payload()
    restored = Artifact.from_bus_payload(payload)
    assert restored.artifact_id == "art-1"
    assert restored.normalized_kind() == ArtifactType.MARKDOWN.value
    assert restored.label == "Summary"
    assert restored.workspace_id == "ws-1"


def test_infer_tool_and_chat_kinds() -> None:
    assert infer_tool_artifact_kind("shell") == ArtifactType.CODE.value
    assert infer_tool_artifact_kind("note_search") == ArtifactType.MARKDOWN.value
    assert infer_chat_artifact_kind("plain answer") == ArtifactType.TEXT.value
    assert infer_chat_artifact_kind("# Heading\nbody") == ArtifactType.MARKDOWN.value
