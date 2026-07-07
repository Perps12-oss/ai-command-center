"""Artifact domain model tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ai_command_center.domain.artifact import Artifact, ArtifactType


def test_artifact_type_coerce() -> None:
    assert ArtifactType.coerce("CODE") == ArtifactType.CODE
    assert ArtifactType.coerce("unknown").value == "text"


def test_artifact_round_trip_dict() -> None:
    artifact = Artifact(
        artifact_id="art-1",
        kind=ArtifactType.PDF,
        label="report.pdf",
        size_bytes=4096,
        content_ref="file://report.pdf",
        execution_id="exec-1",
        mime_type="application/pdf",
        created_at=1.0,
        updated_at=2.0,
    )
    restored = Artifact.from_dict(artifact.to_dict())
    assert restored == artifact

    with pytest.raises(FrozenInstanceError):
        artifact.label = "mutated"  # type: ignore[misc]
