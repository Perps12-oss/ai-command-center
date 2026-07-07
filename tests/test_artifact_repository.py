"""ArtifactRepository tests."""

from __future__ import annotations

from pathlib import Path

from ai_command_center.db.connection import connect, init_database
from ai_command_center.domain.artifact import ArtifactType
from ai_command_center.repositories.artifact_repository import ArtifactRepository


def _repo() -> ArtifactRepository:
    db = init_database(connect(Path(":memory:")))
    return ArtifactRepository(db)


def test_create_and_get() -> None:
    repo = _repo()
    artifact = repo.create(
        kind=ArtifactType.CODE,
        label="snippet.py",
        size_bytes=512,
        content_ref="inline:print('hi')",
        execution_id="req-1",
        mime_type="text/x-python",
        artifact_id="art-fixed",
    )
    assert artifact.artifact_id == "art-fixed"
    assert artifact.kind == ArtifactType.CODE
    assert artifact.label == "snippet.py"

    loaded = repo.get("art-fixed")
    assert loaded is not None
    assert loaded.execution_id == "req-1"
    assert loaded.size_bytes == 512


def test_update_partial_fields() -> None:
    repo = _repo()
    created = repo.create(kind="text", label="Draft", artifact_id="art-1")
    updated = repo.update("art-1", label="Final", size_bytes=99)
    assert updated is not None
    assert updated.label == "Final"
    assert updated.size_bytes == 99
    assert updated.created_at == created.created_at
    assert updated.updated_at >= created.updated_at


def test_list_by_execution_and_recent() -> None:
    repo = _repo()
    repo.create(kind="text", label="A", execution_id="exec-1", artifact_id="a1")
    repo.create(kind="code", label="B", execution_id="exec-1", artifact_id="a2")
    repo.create(kind="image", label="C", execution_id="exec-2", artifact_id="a3")

    by_exec = repo.list_by_execution("exec-1")
    assert [a.artifact_id for a in by_exec] == ["a1", "a2"]

    recent = repo.list_recent(limit=2)
    assert len(recent) == 2
    assert recent[-1].artifact_id == "a3"
