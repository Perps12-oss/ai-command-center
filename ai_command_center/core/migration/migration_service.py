"""
Migration Service Contract - FROZEN ARCHITECTURE SPECIFICATION

Contract for import, export, upgrade, transform, and restore operations.
Implementation can remain minimal initially.

FROZEN: Phase 2 - Workspace OS Integration
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MigrationResult:
    """Result of a migration operation."""

    success: bool
    entities_migrated: int
    errors: list[str]

    # Optional metadata
    migrated_ids: list[UUID] = None  # type: ignore[assignment]
    source_version: int | None = None
    target_version: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "migrated_ids", self.migrated_ids or [])


class MigrationService(ABC):
    """
    Migration service contract.
    
    Responsibilities:
    - Import data from external sources
    - Export entities to external formats
    - Upgrade schema versions
    - Transform entities
    - Restore snapshots
    """

    @abstractmethod
    def import_data(self, source: str, format: str) -> MigrationResult:
        """Import data from source in the specified format."""
        pass

    @abstractmethod
    def export_data(self, entities: list[UUID], format: str) -> bytes:
        """Export entities to the specified format."""
        pass

    @abstractmethod
    def upgrade_schema(
        self, from_version: int, to_version: int
    ) -> MigrationResult:
        """Upgrade schema from one version to another."""
        pass

    @abstractmethod
    def transform_data(
        self, transform: str, entities: list[UUID]
    ) -> MigrationResult:
        """Apply a named transform to a set of entities."""
        pass

    @abstractmethod
    def restore_snapshot(self, snapshot_id: UUID) -> MigrationResult:
        """Restore system state from a snapshot."""
        pass
