"""
Entity Service - Phase 1 Implementation

Entity lifecycle management and validation following the frozen Entity contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from ai_command_center.core.entity.entity import (
    Entity,
    ENTITY_SCHEMA_VERSION,
    validate_entity_type,
)
from ai_command_center.core.entity.entity_repository import EntityRepository
from ai_command_center.core.event_bus import (
    Event,
    EVENT_ENTITY_CREATED,
    EVENT_ENTITY_UPDATED,
    EVENT_ENTITY_DELETED,
    EVENT_ENTITY_RELATIONSHIPS_CHANGED,
)


class EntityService:
    """
    Entity lifecycle management.
    
    Responsibilities:
    - Entity creation with validation
    - Entity updates with validation
    - Entity deletion
    - Event publishing for all operations
    """

    def __init__(self, repository: EntityRepository, event_bus: Any) -> None:
        self._repository = repository
        self._event_bus = event_bus

    def create(
        self,
        entity_type: str,
        title: str,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Entity:
        """Create a new entity with validation."""
        if not validate_entity_type(entity_type):
            raise ValueError(f"Invalid entity_type: {entity_type}")
        
        entity = Entity(
            id=uuid4(),
            entity_type=entity_type,
            title=title,
            description=description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            schema_version=ENTITY_SCHEMA_VERSION,
            metadata=metadata or {},
            relationships=[],
            embedding_status="none",
            embedding_vector=None,
        )
        
        created = self._repository.create(entity)
        
        # Publish event
        self._event_bus.publish(
            EVENT_ENTITY_CREATED,
            {
                "entity_id": str(created.id),
                "entity_type": created.entity_type,
                "title": created.title,
            },
            source="entity_service",
        )
        
        return created

    def update(
        self,
        entity_id: UUID,
        title: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Entity:
        """Update an existing entity."""
        entity = self._repository.get(entity_id)
        if entity is None:
            raise ValueError(f"Entity not found: {entity_id}")
        
        updated = Entity(
            id=entity.id,
            entity_type=entity.entity_type,
            title=title if title is not None else entity.title,
            description=description if description is not None else entity.description,
            created_at=entity.created_at,
            updated_at=datetime.utcnow(),
            schema_version=entity.schema_version,
            metadata=metadata if metadata is not None else entity.metadata,
            relationships=entity.relationships,
            embedding_status=entity.embedding_status,
            embedding_vector=entity.embedding_vector,
        )
        
        saved = self._repository.update(updated)
        
        # Publish event
        self._event_bus.publish(
            EVENT_ENTITY_UPDATED,
            {
                "entity_id": str(saved.id),
                "entity_type": saved.entity_type,
                "title": saved.title,
            },
            source="entity_service",
        )
        
        return saved

    def delete(self, entity_id: UUID) -> bool:
        """Delete an entity."""
        deleted = self._repository.delete(entity_id)
        
        if deleted:
            # Publish event
            self._event_bus.publish(
                EVENT_ENTITY_DELETED,
                {"entity_id": str(entity_id)},
                source="entity_service",
            )
        
        return deleted

    def get(self, entity_id: UUID) -> Entity | None:
        """Get entity by ID."""
        return self._repository.get(entity_id)

    def get_by_type(self, entity_type: str) -> list[Entity]:
        """Get all entities of a specific type."""
        return self._repository.get_by_type(entity_type)

    def list_all(self) -> list[Entity]:
        """List all entities."""
        return self._repository.list_all()

    def search(self, query: str, entity_type: str | None = None) -> list[Entity]:
        """Search entities by title or description."""
        return self._repository.search(query, entity_type)

    def add_relationship(self, entity_id: UUID, relationship_id: UUID) -> Entity:
        """Add a relationship to an entity."""
        entity = self._repository.get(entity_id)
        if entity is None:
            raise ValueError(f"Entity not found: {entity_id}")
        
        if relationship_id in entity.relationships:
            return entity  # Already has this relationship
        
        updated_relationships = list(entity.relationships) + [relationship_id]
        
        updated = Entity(
            id=entity.id,
            entity_type=entity.entity_type,
            title=entity.title,
            description=entity.description,
            created_at=entity.created_at,
            updated_at=datetime.utcnow(),
            schema_version=entity.schema_version,
            metadata=entity.metadata,
            relationships=updated_relationships,
            embedding_status=entity.embedding_status,
            embedding_vector=entity.embedding_vector,
        )
        
        saved = self._repository.update(updated)
        
        # Publish event
        self._event_bus.publish(
            EVENT_ENTITY_RELATIONSHIPS_CHANGED,
            {
                "entity_id": str(saved.id),
                "relationship_id": str(relationship_id),
                "action": "added",
            },
            source="entity_service",
        )
        
        return saved

    def remove_relationship(self, entity_id: UUID, relationship_id: UUID) -> Entity:
        """Remove a relationship from an entity."""
        entity = self._repository.get(entity_id)
        if entity is None:
            raise ValueError(f"Entity not found: {entity_id}")
        
        if relationship_id not in entity.relationships:
            return entity  # Doesn't have this relationship
        
        updated_relationships = [r for r in entity.relationships if r != relationship_id]
        
        updated = Entity(
            id=entity.id,
            entity_type=entity.entity_type,
            title=entity.title,
            description=entity.description,
            created_at=entity.created_at,
            updated_at=datetime.utcnow(),
            schema_version=entity.schema_version,
            metadata=entity.metadata,
            relationships=updated_relationships,
            embedding_status=entity.embedding_status,
            embedding_vector=entity.embedding_vector,
        )
        
        saved = self._repository.update(updated)
        
        # Publish event
        self._event_bus.publish(
            EVENT_ENTITY_RELATIONSHIPS_CHANGED,
            {
                "entity_id": str(saved.id),
                "relationship_id": str(relationship_id),
                "action": "removed",
            },
            source="entity_service",
        )
        
        return saved
