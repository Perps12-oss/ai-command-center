"""
Relationship Service - Phase 1 Implementation

Relationship lifecycle management and graph queries following the frozen Relationship contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from ai_command_center.core.relationship.relationship import (
    Relationship,
    RelationshipType,
    validate_relationship_type,
)
from ai_command_center.core.relationship.relationship_repository import RelationshipRepository
from ai_command_center.core.event_bus import (
    EVENT_RELATIONSHIP_CREATED,
    EVENT_RELATIONSHIP_DELETED,
)


class RelationshipService:
    """
    Relationship lifecycle management and graph queries.
    
    Responsibilities:
    - Relationship creation with validation
    - Relationship deletion
    - Graph queries (traversal, paths)
    - Event publishing for all operations
    """

    def __init__(self, repository: RelationshipRepository, event_bus: Any) -> None:
        self._repository = repository
        self._event_bus = event_bus

    def create(
        self,
        source_id: UUID,
        target_id: UUID,
        relationship_type: RelationshipType,
        metadata: dict[str, Any] | None = None,
    ) -> Relationship:
        """Create a new relationship with validation."""
        if not validate_relationship_type(relationship_type.value):
            raise ValueError(f"Invalid relationship_type: {relationship_type}")
        
        relationship = Relationship(
            id=uuid4(),
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            created_at=datetime.utcnow(),
            metadata=metadata or {},
        )
        
        created = self._repository.create(relationship)
        
        # Publish event
        self._event_bus.publish(
            EVENT_RELATIONSHIP_CREATED,
            {
                "relationship_id": str(created.id),
                "source_id": str(created.source_id),
                "target_id": str(created.target_id),
                "relationship_type": created.relationship_type.value,
            },
            source="relationship_service",
        )
        
        return created

    def delete(self, relationship_id: UUID) -> bool:
        """Delete a relationship by ID."""
        deleted = self._repository.delete(relationship_id)
        
        if deleted:
            # Publish event
            self._event_bus.publish(
                EVENT_RELATIONSHIP_DELETED,
                {"relationship_id": str(relationship_id)},
                source="relationship_service",
            )
        
        return deleted

    def delete_between(self, source_id: UUID, target_id: UUID) -> int:
        """Delete all relationships between two entities."""
        count = self._repository.delete_between(source_id, target_id)
        
        if count > 0:
            # Publish event
            self._event_bus.publish(
                EVENT_RELATIONSHIP_DELETED,
                {
                    "source_id": str(source_id),
                    "target_id": str(target_id),
                    "count": count,
                },
                source="relationship_service",
            )
        
        return count

    def get(self, relationship_id: UUID) -> Relationship | None:
        """Get relationship by ID."""
        return self._repository.get(relationship_id)

    def get_by_source(self, source_id: UUID) -> list[Relationship]:
        """Get all relationships where source_id is the source."""
        return self._repository.get_by_source(source_id)

    def get_by_target(self, target_id: UUID) -> list[Relationship]:
        """Get all relationships where target_id is the target."""
        return self._repository.get_by_target(target_id)

    def get_by_type(self, relationship_type: RelationshipType) -> list[Relationship]:
        """Get all relationships of a specific type."""
        return self._repository.get_by_type(relationship_type)

    def get_between(self, source_id: UUID, target_id: UUID) -> list[Relationship]:
        """Get all relationships between two entities."""
        return self._repository.get_between(source_id, target_id)

    def list_all(self) -> list[Relationship]:
        """List all relationships."""
        return self._repository.list_all()

    def get_related_entities(self, entity_id: UUID, relationship_type: RelationshipType | None = None) -> list[UUID]:
        """
        Get all entities related to the given entity.
        
        Returns list of target entity IDs.
        """
        if relationship_type:
            relationships = self._repository.get_by_type(relationship_type)
        else:
            relationships = self._repository.get_by_source(entity_id)
        
        return [r.target_id for r in relationships if r.source_id == entity_id]

    def traverse(self, entity_id: UUID, max_depth: int = 3) -> dict[UUID, set[UUID]]:
        """
        Traverse relationships from an entity.
        
        Returns a dictionary mapping depth to set of entity IDs at that depth.
        """
        result: dict[int, set[UUID]] = {0: {entity_id}}
        visited: set[UUID] = {entity_id}
        current_level = {entity_id}
        
        for depth in range(1, max_depth + 1):
            next_level: set[UUID] = set()
            
            for current_id in current_level:
                relationships = self._repository.get_by_source(current_id)
                for rel in relationships:
                    if rel.target_id not in visited:
                        next_level.add(rel.target_id)
                        visited.add(rel.target_id)
            
            if not next_level:
                break
            
            result[depth] = next_level
            current_level = next_level
        
        return {k: v for k, v in result.items() if v}

    def find_path(self, source_id: UUID, target_id: UUID, max_depth: int = 5) -> list[UUID] | None:
        """
        Find shortest path between two entities using BFS.
        
        Returns list of entity IDs in the path, or None if no path exists.
        """
        from collections import deque
        
        queue = deque([(source_id, [source_id])])
        visited = {source_id}
        
        while queue:
            current_id, path = queue.popleft()
            
            if current_id == target_id:
                return path
            
            if len(path) >= max_depth:
                continue
            
            relationships = self._repository.get_by_source(current_id)
            for rel in relationships:
                if rel.target_id not in visited:
                    visited.add(rel.target_id)
                    queue.append((rel.target_id, path + [rel.target_id]))
        
        return None
