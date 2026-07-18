"""Domain snapshot for model selection, tool runs, and artifact feeds."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from ai_command_center.core.state.artifact_state import ArtifactCatalogItem
from ai_command_center.core.state.model_state import ModelSelectionSnapshot
from ai_command_center.core.state.tool_state import ToolRunItem


@dataclass(frozen=True, slots=True)
class ModelArtifactSnapshot:
    """Consolidated immutable projection of model, tool, and artifact state."""

    model_selection: ModelSelectionSnapshot = field(default_factory=ModelSelectionSnapshot)
    recent_tool_runs: tuple[ToolRunItem, ...] = ()
    recent_artifacts: tuple[ArtifactCatalogItem, ...] = ()
    revision: int = 0

    @classmethod
    def from_components(
        cls,
        *,
        model_selection: ModelSelectionSnapshot,
        recent_tool_runs: tuple[ToolRunItem, ...],
        recent_artifacts: tuple[ArtifactCatalogItem, ...],
        revision: int,
    ) -> "ModelArtifactSnapshot":
        return cls(
            model_selection=model_selection,
            recent_tool_runs=recent_tool_runs,
            recent_artifacts=recent_artifacts,
            revision=revision,
        )

    def with_revision(self, revision: int) -> "ModelArtifactSnapshot":
        return replace(self, revision=revision)
