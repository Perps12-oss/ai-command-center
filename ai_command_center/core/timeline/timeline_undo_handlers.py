"""Timeline undo handlers for workspace OS operations (Program 3 W3).

Subscribes to TIMELINE_UNDO_REQUEST and routes undo_data to the appropriate
service handlers based on event_type and entity_type.

Undo data structure per event_type:
- entity_create: {entity_id, entity_data} -> delete entity
- entity_delete: {entity_data} -> recreate entity
- relationship_create: {relationship_id, source_id, target_id} -> delete relationship
- relationship_delete: {relationship_data} -> recreate relationship
- workspace_add_entity: {workspace_id, entity_id} -> remove entity from workspace
- workspace_remove_entity: {workspace_id, entity_id} -> add entity back to workspace
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    TIMELINE_UNDO_REQUEST,
    TIMELINE_UNDO_RESULT,
)

if TYPE_CHECKING:
    from ai_command_center.core.entity.entity_service import EntityService
    from ai_command_center.core.relationship.relationship_service import RelationshipService
    from ai_command_center.core.workspace.workspace_service import WorkspaceService


class TimelineUndoHandlers:
    """Routes TIMELINE_UNDO_REQUEST events to appropriate service handlers."""

    def __init__(
        self,
        entity_service: EntityService,
        relationship_service: RelationshipService,
        workspace_service: WorkspaceService,
        bus: Any,
    ) -> None:
        self._entity_service = entity_service
        self._relationship_service = relationship_service
        self._workspace_service = workspace_service
        self._bus = bus
        self._unsubs: list[Any] = []

    def wire(self) -> None:
        """Subscribe to TIMELINE_UNDO_REQUEST topic."""
        self._unsubs.append(
            self._bus.subscribe(TIMELINE_UNDO_REQUEST, self._on_undo_request)
        )

    def unwire(self) -> None:
        """Unsubscribe from TIMELINE_UNDO_REQUEST topic."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    def _on_undo_request(self, event: Event) -> None:
        """Handle TIMELINE_UNDO_REQUEST by routing to appropriate handler."""
        payload = event.payload or {}
        event_type = str(payload.get("event_type", ""))
        undo_data = dict(payload.get("undo_data") or {})

        try:
            if event_type == "entity_create":
                self._undo_entity_create(undo_data)
            elif event_type == "entity_delete":
                self._undo_entity_delete(undo_data)
            elif event_type == "relationship_create":
                self._undo_relationship_create(undo_data)
            elif event_type == "relationship_delete":
                self._undo_relationship_delete(undo_data)
            elif event_type == "workspace_add_entity":
                self._undo_workspace_add_entity(undo_data)
            elif event_type == "workspace_remove_entity":
                self._undo_workspace_remove_entity(undo_data)
            else:
                # Unknown event type - publish failure
                self._publish_result(
                    success=False,
                    error=f"Unknown event type for undo: {event_type}",
                )
                return

            self._publish_result(success=True)

        except Exception as exc:  # noqa: BLE001
            self._publish_result(success=False, error=str(exc))

    def _undo_entity_create(self, undo_data: dict[str, Any]) -> None:
        """Undo entity creation by deleting the entity."""
        entity_id = undo_data.get("entity_id")
        if not entity_id:
            raise ValueError("Missing entity_id in undo_data for entity_create")
        self._entity_service.delete(entity_id)

    def _undo_entity_delete(self, undo_data: dict[str, Any]) -> None:
        """Undo entity deletion by recreating the entity."""
        entity_data = undo_data.get("entity_data")
        if not entity_data:
            raise ValueError("Missing entity_data in undo_data for entity_delete")

        # Recreate entity with original data
        from ai_command_center.core.entity.entity import Entity
        from datetime import datetime
        from uuid import UUID

        entity = Entity(
            id=UUID(entity_data["id"]),
            entity_type=entity_data["entity_type"],
            title=entity_data["title"],
            description=entity_data.get("description", ""),
            created_at=datetime.fromisoformat(entity_data["created_at"]),
            updated_at=datetime.utcnow(),
            schema_version=entity_data.get("schema_version", 1),
            metadata=dict(entity_data.get("metadata", {})),
            relationships=[UUID(r) for r in entity_data.get("relationships", [])],
            embedding_status=entity_data.get("embedding_status", "none"),
            embedding_vector=None,
        )
        self._entity_service._repository.create(entity)  # noqa: SLF001

    def _undo_relationship_create(self, undo_data: dict[str, Any]) -> None:
        """Undo relationship creation by deleting the relationship."""
        relationship_id = undo_data.get("relationship_id")
        if not relationship_id:
            raise ValueError("Missing relationship_id in undo_data for relationship_create")
        self._relationship_service.delete(relationship_id)

    def _undo_relationship_delete(self, undo_data: dict[str, Any]) -> None:
        """Undo relationship deletion by recreating the relationship."""
        from uuid import UUID

        relationship_data = undo_data.get("relationship_data")
        if not relationship_data:
            raise ValueError("Missing relationship_data in undo_data for relationship_delete")

        # Recreate relationship with original data using RelationshipService.create
        from ai_command_center.core.relationship.relationship import RelationshipType

        rel_type_str = relationship_data["relationship_type"]
        rel_type = (
            RelationshipType(rel_type_str)
            if isinstance(rel_type_str, str)
            else rel_type_str
        )
        self._relationship_service.create(
            source_id=UUID(relationship_data["source_id"]),
            target_id=UUID(relationship_data["target_id"]),
            relationship_type=rel_type,
            metadata=dict(relationship_data.get("metadata", {})),
        )

    def _undo_workspace_add_entity(self, undo_data: dict[str, Any]) -> None:
        """Undo adding entity to workspace by removing it."""
        from uuid import UUID

        workspace_id = undo_data.get("workspace_id")
        entity_id = undo_data.get("entity_id")
        if not workspace_id or not entity_id:
            raise ValueError("Missing workspace_id or entity_id in undo_data")
        self._workspace_service.remove_entity(UUID(workspace_id), UUID(entity_id))

    def _undo_workspace_remove_entity(self, undo_data: dict[str, Any]) -> None:
        """Undo removing entity from workspace by adding it back."""
        from uuid import UUID

        workspace_id = undo_data.get("workspace_id")
        entity_id = undo_data.get("entity_id")
        if not workspace_id or not entity_id:
            raise ValueError("Missing workspace_id or entity_id in undo_data")
        self._workspace_service.add_entity(UUID(workspace_id), UUID(entity_id))

    def _publish_result(
        self,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Publish TIMELINE_UNDO_RESULT event."""
        self._bus.publish(
            TIMELINE_UNDO_RESULT,
            {
                "success": success,
                "error": error,
            },
            source="timeline_undo_handlers",
        )


def register_timeline_undo_handlers(
    entity_service: EntityService,
    relationship_service: RelationshipService,
    workspace_service: WorkspaceService,
    bus: Any,
) -> TimelineUndoHandlers:
    """Factory function to create and wire timeline undo handlers."""
    handlers = TimelineUndoHandlers(
        entity_service=entity_service,
        relationship_service=relationship_service,
        workspace_service=workspace_service,
        bus=bus,
    )
    handlers.wire()
    return handlers
