"""ArtifactService bus integration tests."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    ARTIFACT_CREATED,
    ARTIFACTS_LOADED,
    ARTIFACT_UPDATED,
    CHAT_COMPLETE,
    TOOL_RESULT,
    UI_ARTIFACT_ACTION,
)
from ai_command_center.domain.artifact import Artifact
from ai_command_center.repositories.artifact_repository import ArtifactRepository
from ai_command_center.repositories.database_bootstrap_repository import DatabaseBootstrapRepository
from ai_command_center.services.artifact_service import ArtifactService


def _service(tmp_path: Path) -> tuple[EventBus, ArtifactService, ArtifactRepository]:
    conn = sqlite3.connect(tmp_path / "artifact_service.db")
    conn.row_factory = sqlite3.Row
    DatabaseBootstrapRepository().apply(conn)
    repo = ArtifactRepository(conn)
    bus = EventBus()
    service = ArtifactService(bus, repo=repo)
    return bus, service, repo


def test_tool_result_creates_artifact() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bus, service, repo = _service(Path(tmp))
        created: list[dict] = []
        bus.subscribe(ARTIFACT_CREATED, lambda e: created.append(dict(e.payload)))
        service.start()
        bus.publish(
            TOOL_RESULT,
            {
                "success": True,
                "tool": "shell",
                "invoke_id": "inv-1",
                "output": "echo hello",
                "request_id": "req-tool",
            },
            source="test",
        )
        service.stop()
        assert created
        assert created[0]["artifact_id"] == "tool:inv-1"
        assert created[0]["kind"] == "code"
        assert repo.get("tool:inv-1") is not None


def test_chat_complete_creates_artifact() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bus, service, repo = _service(Path(tmp))
        created: list[dict] = []
        bus.subscribe(ARTIFACT_CREATED, lambda e: created.append(dict(e.payload)))
        service.start()
        bus.publish(
            CHAT_COMPLETE,
            {
                "request_id": "req-chat",
                "text": "# Answer\nDone.",
            },
            source="test",
        )
        service.stop()
        assert created
        assert created[0]["artifact_id"] == "chat:req-chat"
        assert created[0]["kind"] == "markdown"
        assert repo.get("chat:req-chat") is not None


def test_startup_publishes_recent_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bus, service, repo = _service(Path(tmp))
        repo.insert(
            Artifact(
                artifact_id="seed-1",
                kind="text",
                label="Seed",
                content="seed",
                source="chat",
            )
        )
        loaded: list[dict] = []
        bus.subscribe(ARTIFACTS_LOADED, lambda e: loaded.append(dict(e.payload)))
        service.start()
        service.stop()
        assert loaded
        artifacts = loaded[0]["artifacts"]
        assert len(artifacts) == 1
        assert artifacts[0]["artifact_id"] == "seed-1"


def test_ui_artifact_action_publishes_updated_event() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bus, service, repo = _service(Path(tmp))
        repo.insert(
            Artifact(
                artifact_id="art-ui",
                kind="text",
                label="Preview",
                content="body",
                source="chat",
            )
        )
        updated: list[dict] = []
        bus.subscribe(ARTIFACT_UPDATED, lambda e: updated.append(dict(e.payload)))
        service.start()
        bus.publish(
            UI_ARTIFACT_ACTION,
            {"artifact_id": "art-ui", "action": "preview"},
            source="ui",
        )
        service.stop()
        assert updated
        assert updated[0]["artifact_id"] == "art-ui"
