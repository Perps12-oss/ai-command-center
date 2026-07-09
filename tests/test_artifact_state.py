"""Artifact AppState reducer tests."""

from __future__ import annotations

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    ARTIFACT_CREATED,
    ARTIFACTS_LOADED,
    ARTIFACT_UPDATED,
)


def test_artifact_created_projects_recent_catalog() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        bus.publish(
            ARTIFACT_CREATED,
            {
                "artifact_id": "art-1",
                "kind": "text",
                "label": "First",
                "content": "one",
            },
            source="test",
        )
        snap = store.snapshot
        assert len(snap.recent_artifacts) == 1
        assert snap.recent_artifacts[0].artifact_id == "art-1"
        assert snap.recent_artifacts[0].label == "First"

        bus.publish(
            ARTIFACT_UPDATED,
            {
                "artifact_id": "art-1",
                "kind": "markdown",
                "label": "Updated",
                "content": "two",
            },
            source="test",
        )
        snap = store.snapshot
        assert snap.recent_artifacts[0].kind == "markdown"
        assert snap.recent_artifacts[0].content == "two"
    finally:
        store.close()


def test_artifacts_loaded_replaces_catalog() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        bus.publish(
            ARTIFACTS_LOADED,
            {
                "artifacts": [
                    {
                        "artifact_id": "a",
                        "kind": "text",
                        "label": "A",
                        "content": "alpha",
                    },
                    {
                        "artifact_id": "b",
                        "kind": "code",
                        "label": "B",
                        "content": "beta",
                    },
                ]
            },
            source="test",
        )
        snap = store.snapshot
        assert [item.artifact_id for item in snap.recent_artifacts] == ["a", "b"]
    finally:
        store.close()
