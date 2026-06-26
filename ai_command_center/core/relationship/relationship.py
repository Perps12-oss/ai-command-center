"""
Relationship Contract - FROZEN ARCHITECTURE SPECIFICATION

This module defines the Relationship contract and governed RelationshipType enum
for the Workspace Operating System.

FROZEN: Phase 0 - Universal Foundation
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class RelationshipType(Enum):
    """
    Controlled vocabulary for relationship types.
    
    This enum prevents relationship type fragmentation (e.g., CONTAINS vs Contains vs contains).
    All relationships must use these governed types.
    """

    # Containment
    CONTAINS = "contains"
    PART_OF = "part_of"

    # Usage
    USES = "uses"
    DEPENDS_ON = "depends_on"

    # Execution
    EXECUTES = "executes"
    TRIGGERS = "triggers"

    # Generation
    GENERATED = "generated"
    DERIVED_FROM = "derived_from"

    # Reference
    REFERENCES = "references"
    RELATED_TO = "related_to"

    # Knowledge
    HAS_TAG = "has_tag"
    LINKS_TO = "links_to"

    # Ownership
    OWNS = "owns"
    MANAGES = "manages"


@dataclass(frozen=True, slots=True)
class Relationship:
    """
    First-class entity-to-entity connections with governed types.
    
    Relationships are stored as first-class objects, not embedded in entities.
    This enables graph queries, traversal, and relationship-level metadata.
    """

    id: UUID
    source_id: UUID
    target_id: UUID
    relationship_type: RelationshipType

    created_at: datetime
    metadata: dict[str, Any]


# Current schema version
RELATIONSHIP_SCHEMA_VERSION = 1


def validate_relationship_type(relationship_type: str) -> bool:
    """Validate that relationship_type is a governed RelationshipType."""
    try:
        RelationshipType(relationship_type)
        return True
    except ValueError:
        return False
