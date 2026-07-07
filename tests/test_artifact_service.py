"""ArtifactService bus integration tests."""

from __future__ import annotations

from pathlib import Path

from ai_command_center.core.events.topics import (
    ARTIFACT_CREATE_REQUEST,
    ARTIFACT_CREATED,
    ARTIFACT_UPDATE_REQUEST,
    ARTIFACT_UPDATED,
)
from ai_command_center.db.connection import connect, init_database
from ai_command_center.repositories.artifact_repository import ArtifactRepository
from ai_command_center.services.artifact_service import ArtifactService
from tests.support.mocks import RecordingEventBus


def test_create_request_persists_and_publishes_created() -> None:
    db = init_database(connect(Path(":memory:")))
    repo = ArtifactRepository(db)
    bus = RecordingEventBus()
    svc = ArtifactService(bus, repo=repo)
    svc.start()

    bus.publish(
        ARTIFACT_CREATE_REQUEST,
        {
            "artifact_id": "art-1",
            "kind": "markdown",
            "label": "README",
            "size_bytes": 1024,
            "content_ref": "vault://README.md",
            "execution_id": "exec-9",
        },
        source="test",
    )
    svc.stop()

    stored = repo.get("art-1")
    assert stored is not None
    assert stored.label == "README"
    assert stored.kind.value == "markdown"

    created_events = [e for e in bus.recorded if e.topic == ARTIFACT_CREATED]
    assert len(created_events) == 1
    assert created_events[0].payload["artifact_id"] == "art-1"


def test_update_request_publishes_updated() -> None:
    db = init_database(connect(Path(":memory:")))
    repo = ArtifactRepository(db)
    repo.create(kind="text", label="Old", artifact_id="art-2")
    bus = RecordingEventBus()
    svc = ArtifactService(bus, repo=repo)
    svc.start()

    bus.publish(
        ARTIFACT_UPDATE_REQUEST,
        {"artifact_id": "art-2", "label": "New"},
        source="test",
    )
    svc.stop()

    stored = repo.get("art-2")
    assert stored is not None
    assert stored.label == "New"

    updated_events = [e for e in bus.recorded if e.topic == ARTIFACT_UPDATED]
    assert len(updated_events) == 1
    assert updated_events[0].payload["label"] == "New"
