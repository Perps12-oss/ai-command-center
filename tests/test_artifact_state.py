"""ArtifactState reducer tests."""

from __future__ import annotations

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.events.topics import ARTIFACT_CREATED, ARTIFACT_UPDATED


def test_artifact_created_projects_recent_artifacts(event_bus) -> None:
    store = AppStateStore(event_bus)

    event_bus.publish(
        ARTIFACT_CREATED,
        {
            "artifact_id": "art-1",
            "kind": "code",
            "label": "main.py",
            "size_bytes": 2048,
            "content_ref": "file://main.py",
            "execution_id": "exec-1",
            "mime_type": "text/x-python",
            "created_at": 100.0,
            "updated_at": 100.0,
        },
        source="artifact",
    )

    snap = store.snapshot
    assert len(snap.recent_artifacts) == 1
    item = snap.recent_artifacts[0]
    assert item.artifact_id == "art-1"
    assert item.kind == "code"
    assert item.label == "main.py"
    assert item.size_bytes == 2048
    assert item.execution_id == "exec-1"


def test_artifact_updated_replaces_existing_entry(event_bus) -> None:
    store = AppStateStore(event_bus)

    event_bus.publish(
        ARTIFACT_CREATED,
        {
            "artifact_id": "art-1",
            "kind": "text",
            "label": "Draft",
            "size_bytes": 10,
            "created_at": 1.0,
            "updated_at": 1.0,
        },
        source="artifact",
    )
    event_bus.publish(
        ARTIFACT_UPDATED,
        {
            "artifact_id": "art-1",
            "kind": "text",
            "label": "Final",
            "size_bytes": 20,
            "created_at": 1.0,
            "updated_at": 2.0,
        },
        source="artifact",
    )

    snap = store.snapshot
    assert len(snap.recent_artifacts) == 1
    assert snap.recent_artifacts[0].label == "Final"
    assert snap.recent_artifacts[0].size_bytes == 20
    assert snap.recent_artifacts[0].updated_at == 2.0


def test_artifact_created_prepends_most_recent(event_bus) -> None:
    store = AppStateStore(event_bus)

    for idx in range(2):
        event_bus.publish(
            ARTIFACT_CREATED,
            {
                "artifact_id": f"art-{idx}",
                "kind": "text",
                "label": f"Artifact {idx}",
                "created_at": float(idx),
                "updated_at": float(idx),
            },
            source="artifact",
        )

    ids = [item.artifact_id for item in store.snapshot.recent_artifacts]
    assert ids == ["art-1", "art-0"]


def test_empty_artifact_payload_noop(event_bus) -> None:
    store = AppStateStore(event_bus)

    event_bus.publish(ARTIFACT_CREATED, {"kind": "text", "label": "orphan"}, source="artifact")

    assert store.snapshot.recent_artifacts == ()
