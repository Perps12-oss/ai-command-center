"""ArtifactRepository persistence tests."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from ai_command_center.domain.artifact import Artifact
from ai_command_center.repositories.artifact_repository import ArtifactRepository
from ai_command_center.repositories.database_bootstrap_repository import DatabaseBootstrapRepository


def _repo(tmp_path: Path) -> tuple[ArtifactRepository, sqlite3.Connection]:
    conn = sqlite3.connect(tmp_path / "artifacts.db")
    conn.row_factory = sqlite3.Row
    DatabaseBootstrapRepository().apply(conn)
    return ArtifactRepository(conn), conn


def test_artifact_repository_insert_list_get_update() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo, conn = _repo(Path(tmp))
        try:
            created = repo.insert(
                Artifact(
                    artifact_id="art-1",
                    kind="text",
                    label="Hello",
                    content="world",
                    request_id="req-1",
                    source="chat",
                )
            )
            assert created.artifact_id == "art-1"
            assert created.size_bytes == 0

            loaded = repo.get("art-1")
            assert loaded is not None
            assert loaded.content == "world"

            updated = repo.update(
                Artifact(
                    artifact_id="art-1",
                    kind="markdown",
                    label="Hello updated",
                    content="updated body",
                    request_id="req-1",
                    source="chat",
                )
            )
            assert updated is not None
            assert updated.kind == "markdown"
            assert updated.label == "Hello updated"

            recent = repo.list_recent()
            assert len(recent) == 1
            assert recent[0].artifact_id == "art-1"
        finally:
            conn.close()
