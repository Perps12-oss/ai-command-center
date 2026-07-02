"""
Workspace Service - Phase 1 Implementation

Workspace lifecycle management for operating environments.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from ai_command_center.core.entity.entity import (
    Entity,
    ENTITY_TYPE_WORKSPACE,
)
from ai_command_center.core.entity.entity_service import EntityService
from ai_command_center.core.event_bus import (
    EVENT_WORKSPACE_CREATED,
    EVENT_WORKSPACE_ACTIVATED,
    EVENT_WORKSPACE_DEACTIVATED,
    EVENT_WORKSPACE_LAYOUT_CHANGED,
)


class WorkspaceService:
    """
    Workspace lifecycle management.
    
    Responsibilities:
    - Create workspaces
    - Activate/deactivate workspaces
    - Manage workspace layout
    - Event publishing for workspace operations
    """

    def __init__(self, entity_service: EntityService, event_bus: Any) -> None:
        self._entity_service = entity_service
        self._event_bus = event_bus
        self._active_workspace_id: UUID | None = None

    def create(
        self,
        title: str,
        description: str = "",
        entities: list[UUID] | None = None,
        layout: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
        agents: list[UUID] | None = None,
        views: list[str] | None = None,
    ) -> Entity:
        """Create a new workspace."""
        metadata: dict[str, Any] = {
            "entities": [str(e) for e in (entities or [])],
            "layout": layout or {},
            "settings": settings or {},
            "agents": [str(a) for a in (agents or [])],
            "views": views or [],
        }
        
        workspace = self._entity_service.create(
            entity_type=ENTITY_TYPE_WORKSPACE,
            title=title,
            description=description,
            metadata=metadata,
        )
        
        # Publish event
        self._event_bus.publish(
            EVENT_WORKSPACE_CREATED,
            {
                "workspace_id": str(workspace.id),
                "title": workspace.title,
            },
            source="workspace_service",
        )
        
        return workspace

    def activate(self, workspace_id: UUID) -> Entity:
        """Activate a workspace."""
        workspace = self._entity_service.get(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")
        
        self._active_workspace_id = workspace_id
        
        # Publish event
        self._event_bus.publish(
            EVENT_WORKSPACE_ACTIVATED,
            {
                "workspace_id": str(workspace.id),
                "title": workspace.title,
            },
            source="workspace_service",
        )
        
        return workspace

    def deactivate(self) -> None:
        """Deactivate the current workspace."""
        if self._active_workspace_id:
            self._event_bus.publish(
                EVENT_WORKSPACE_DEACTIVATED,
                {"workspace_id": str(self._active_workspace_id)},
                source="workspace_service",
            )
            self._active_workspace_id = None

    def get_active(self) -> Entity | None:
        """Get the currently active workspace."""
        if self._active_workspace_id is None:
            return None
        return self._entity_service.get(self._active_workspace_id)

    def update_layout(self, workspace_id: UUID, layout: dict[str, Any]) -> Entity:
        """Update workspace layout."""
        workspace = self._entity_service.get(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")
        
        updated_metadata = {**workspace.metadata, "layout": layout}
        updated = self._entity_service.update(
            entity_id=workspace_id,
            metadata=updated_metadata,
        )
        
        # Publish event
        self._event_bus.publish(
            EVENT_WORKSPACE_LAYOUT_CHANGED,
            {
                "workspace_id": str(workspace_id),
            },
            source="workspace_service",
        )
        
        return updated

    def get_all(self) -> list[Entity]:
        """Get all workspaces."""
        return self._entity_service.get_by_type(ENTITY_TYPE_WORKSPACE)

    def get(self, workspace_id: UUID) -> Entity | None:
        """Get workspace by ID."""
        return self._entity_service.get(workspace_id)

    def delete(self, workspace_id: UUID) -> bool:
        """Delete a workspace."""
        if self._active_workspace_id == workspace_id:
            self.deactivate()
        
        return self._entity_service.delete(workspace_id)

    def add_entity(self, workspace_id: UUID, entity_id: UUID) -> Entity:
        """Add an entity to a workspace."""
        workspace = self._entity_service.get(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")
        
        entities = [UUID(e) for e in workspace.metadata.get("entities", [])]
        if entity_id not in entities:
            entities.append(entity_id)
        
        updated_metadata = {**workspace.metadata, "entities": [str(e) for e in entities]}
        return self._entity_service.update(
            entity_id=workspace_id,
            metadata=updated_metadata,
        )

    def remove_entity(self, workspace_id: UUID, entity_id: UUID) -> Entity:
        """Remove an entity from a workspace."""
        workspace = self._entity_service.get(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")
        
        entities = [UUID(e) for e in workspace.metadata.get("entities", [])]
        entities = [e for e in entities if e != entity_id]
        
        updated_metadata = {**workspace.metadata, "entities": [str(e) for e in entities]}
        return self._entity_service.update(
            entity_id=workspace_id,
            metadata=updated_metadata,
        )
