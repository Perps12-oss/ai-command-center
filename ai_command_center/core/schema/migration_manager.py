"""
Schema Versioning Strategy - FROZEN ARCHITECTURE SPECIFICATION

This module defines the schema versioning strategy for the Workspace Operating System.
Every persisted object carries schema_version with migration support.

FROZEN: Phase 0 - Universal Foundation
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SchemaVersion:
    """Schema version information."""

    version: int
    schema: dict[str, Any]
    description: str


class Migration(ABC):
    """
    Base class for schema migrations.
    
    Each migration defines how to transform data from one schema version to another.
    """

    @abstractmethod
    def from_version(self) -> int:
        """Source schema version."""
        pass

    @abstractmethod
    def to_version(self) -> int:
        """Target schema version."""
        pass

    @abstractmethod
    def migrate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform data from source version to target version."""
        pass


class SchemaRegistry:
    """
    Registry of schema versions and migrations.
    
    Benefits:
    - Backward compatibility
    - Forward compatibility
    - Safe migrations
    - Rollback capability
    """

    def __init__(self) -> None:
        self._schemas: dict[int, SchemaVersion] = {}
        self._migrations: dict[tuple[int, int], Migration] = {}

    def register_schema(self, version: int, schema: dict[str, Any], description: str) -> None:
        """Register schema version."""
        self._schemas[version] = SchemaVersion(
            version=version,
            schema=schema,
            description=description,
        )

    def register_migration(self, migration: Migration) -> None:
        """Register migration between versions."""
        key = (migration.from_version(), migration.to_version())
        self._migrations[key] = migration

    def get_schema(self, version: int) -> SchemaVersion | None:
        """Get schema by version."""
        return self._schemas.get(version)

    def get_migration(self, from_version: int, to_version: int) -> Migration | None:
        """Get migration between versions."""
        return self._migrations.get((from_version, to_version))

    def get_migration_path(self, from_version: int, to_version: int) -> list[int]:
        """
        Get path of intermediate versions for migration.
        
        Returns list of versions to migrate through, e.g., [1, 2, 3] for 1→3.
        """
        if from_version == to_version:
            return []

        if from_version < to_version:
            # Forward migration
            path = []
            current = from_version
            while current < to_version:
                next_version = current + 1
                if (current, next_version) not in self._migrations:
                    # No direct migration, try to find path
                    # For now, return simple incremental path
                    pass
                path.append(next_version)
                current = next_version
            return path
        else:
            # Reverse migration
            path = []
            current = from_version
            while current > to_version:
                next_version = current - 1
                path.append(next_version)
                current = next_version
            return path[::-1]  # Reverse for correct order

    def get_latest_version(self) -> int:
        """Get the latest schema version."""
        if not self._schemas:
            return 1
        return max(self._schemas.keys())
