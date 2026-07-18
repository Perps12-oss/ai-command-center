"""Catalog fingerprint must not invalidate on model/tool-only revisions."""

from __future__ import annotations

from ai_command_center.core.app_state import AppState, ArtifactCatalogItem, ToolRunItem
from ai_command_center.core.state.model_state import ModelSelectionSnapshot
from ai_command_center.domain.model_artifact_snapshot import ModelArtifactSnapshot
from ai_command_center.ui.shell.state_applier import StateApplierMixin


class _Harness(StateApplierMixin):
    pass


def _artifacts() -> tuple[ArtifactCatalogItem, ...]:
    return (
        ArtifactCatalogItem(
            artifact_id="a1",
            kind="text",
            label="Note",
            content="hello",
        ),
    )


def test_catalog_fingerprint_ignores_model_and_tool_revision() -> None:
    arts = _artifacts()
    base = AppState(
        recent_artifacts=arts,
        model_artifact=ModelArtifactSnapshot(
            model_selection=ModelSelectionSnapshot(provider="ollama", model="m1"),
            recent_tool_runs=(),
            recent_artifacts=arts,
            revision=1,
        ),
    )
    bumped = AppState(
        recent_artifacts=arts,
        model_artifact=ModelArtifactSnapshot(
            model_selection=ModelSelectionSnapshot(provider="ollama", model="m2"),
            recent_tool_runs=(
                ToolRunItem(invoke_id="t1", tool="shell", status="completed"),
            ),
            recent_artifacts=arts,
            revision=99,
        ),
    )
    h = _Harness()
    assert h._catalog_fingerprint(base) == h._catalog_fingerprint(bumped)


def test_catalog_fingerprint_tracks_recent_artifacts_only() -> None:
    arts_a = _artifacts()
    arts_b = (
        ArtifactCatalogItem(
            artifact_id="a2",
            kind="text",
            label="Other",
            content="world",
        ),
    )
    snap_a = AppState(
        recent_artifacts=arts_a,
        model_artifact=ModelArtifactSnapshot(
            recent_artifacts=arts_a,
            revision=1,
        ),
    )
    snap_b = AppState(
        recent_artifacts=arts_b,
        model_artifact=ModelArtifactSnapshot(
            recent_artifacts=arts_b,
            revision=1,
        ),
    )
    h = _Harness()
    assert h._catalog_fingerprint(snap_a) != h._catalog_fingerprint(snap_b)
