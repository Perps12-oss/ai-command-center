"""Domain snapshot for workspace/entity selection projection."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from ai_command_center.core.state.inspector_state import InspectorState


@dataclass(frozen=True, slots=True)
class WorkspaceEntityItem:
    """Typed projection of a workspace OS entity."""

    entity_id: str = ""
    entity_type: str = ""
    title: str = ""
    metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class WorkspaceEntitySnapshot:
    """Consolidated immutable projection of workspace + entity selection."""

    active_workspace_id: str = ""
    active_workspace_title: str = ""
    selected_entity_id: str = ""
    selected_entity_type: str = ""
    selected_entity_title: str = ""
    workspace_entities: tuple[WorkspaceEntityItem, ...] = ()
    inspector: InspectorState = field(default_factory=InspectorState)
    revision: int = 0

    @classmethod
    def from_components(
        cls,
        *,
        active_workspace_id: str,
        active_workspace_title: str,
        selected_entity_id: str,
        selected_entity_type: str,
        selected_entity_title: str,
        workspace_entities: tuple[WorkspaceEntityItem, ...],
        inspector: InspectorState,
        revision: int,
    ) -> "WorkspaceEntitySnapshot":
        return cls(
            active_workspace_id=active_workspace_id,
            active_workspace_title=active_workspace_title,
            selected_entity_id=selected_entity_id,
            selected_entity_type=selected_entity_type,
            selected_entity_title=selected_entity_title,
            workspace_entities=workspace_entities,
            inspector=inspector,
            revision=revision,
        )

    def with_revision(self, revision: int) -> "WorkspaceEntitySnapshot":
        return replace(self, revision=revision)

