"""
Entity Contract - FROZEN ARCHITECTURE SPECIFICATION

This module defines the universal Entity contract for the Workspace Operating System.
All first-class objects in the system inherit from this contract.

FROZEN: Phase 0 - Universal Foundation
EXTENDED: Phase 2 - Workspace OS Integration (added launchable resource entity types)
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Entity:
    """
    Universal entity contract - all first-class objects in the system.
    
    Disciplined Entity Types (first-class only):
    - Workspace
    - Collection
    - Card
    - Agent
    - Workflow
    - Prompt
    - Project
    - Resource (URL, Folder, File, Command via resource_type metadata)
    - Task
    - Knowledge Object
    - Tag Entity
    
    Configuration (NOT entities):
    - Theme
    - Animation
    - Window Position
    - Layout
    - Settings
    """

    id: UUID
    entity_type: str  # Workspace, Agent, Workflow, Prompt, Card, Project, File, etc.

    title: str
    description: str

    created_at: datetime
    updated_at: datetime

    # Schema versioning
    schema_version: int

    # Extensible storage
    metadata: dict[str, Any]

    # Relationships (evolution from string tags)
    relationships: list[UUID]  # Relationship IDs

    # Search infrastructure (future-proof)
    embedding_status: str = "none"  # none, pending, ready
    embedding_vector: bytes | None = None


# Disciplined entity type constants
ENTITY_TYPE_WORKSPACE = "workspace"
ENTITY_TYPE_COLLECTION = "collection"
ENTITY_TYPE_CARD = "card"
ENTITY_TYPE_AGENT = "agent"
ENTITY_TYPE_WORKFLOW = "workflow"
ENTITY_TYPE_PROMPT = "prompt"
ENTITY_TYPE_PROJECT = "project"
ENTITY_TYPE_FILE = "file"
ENTITY_TYPE_RESOURCE = "resource"
ENTITY_TYPE_TASK = "task"
ENTITY_TYPE_KNOWLEDGE_OBJECT = "knowledge_object"
ENTITY_TYPE_TAG = "tag"

# Resource subtypes stored in metadata["resource_type"]
RESOURCE_TYPE_URL = "url"
RESOURCE_TYPE_FOLDER = "folder"
RESOURCE_TYPE_FILE = "file"
RESOURCE_TYPE_COMMAND = "command"

VALID_RESOURCE_TYPES = {
    RESOURCE_TYPE_URL,
    RESOURCE_TYPE_FOLDER,
    RESOURCE_TYPE_FILE,
    RESOURCE_TYPE_COMMAND,
}

# Valid entity types for validation
VALID_ENTITY_TYPES = {
    ENTITY_TYPE_WORKSPACE,
    ENTITY_TYPE_COLLECTION,
    ENTITY_TYPE_CARD,
    ENTITY_TYPE_AGENT,
    ENTITY_TYPE_WORKFLOW,
    ENTITY_TYPE_PROMPT,
    ENTITY_TYPE_PROJECT,
    ENTITY_TYPE_FILE,
    ENTITY_TYPE_RESOURCE,
    ENTITY_TYPE_TASK,
    ENTITY_TYPE_KNOWLEDGE_OBJECT,
    ENTITY_TYPE_TAG,
}


def validate_resource_type(resource_type: str) -> bool:
    """Validate that resource_type is a recognized resource subtype."""
    return resource_type in VALID_RESOURCE_TYPES

# Current schema version
ENTITY_SCHEMA_VERSION = 1


def validate_entity_type(entity_type: str) -> bool:
    """Validate that entity_type is a recognized first-class entity type."""
    return entity_type in VALID_ENTITY_TYPES
