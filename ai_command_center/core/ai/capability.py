"""
AI Capability Registry Contract - FROZEN ARCHITECTURE SPECIFICATION

This module defines the AI capability registry for the Workspace Operating System.
Centralized AI capability management replaces entity.ai_capabilities list.

FROZEN: Phase 0 - Universal Foundation
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AICapability:
    """
    AI capability - infrastructure, not feature.
    
    Benefits over entity.ai_capabilities list:
    - Plugin extensibility
    - Versioning
    - Feature flags
    - Permission checks
    - Cleaner separation
    """

    id: UUID
    capability_type: str  # Summarize, Explain, Categorize, Organize, Generate

    # Supported entity types
    supported_entity_types: list[str]

    # Execution
    handler: Callable[[UUID, dict[str, Any]], Any]

    # Permissions
    required_permissions: list[str]

    # UI integration
    context_menu: bool
    command_palette: bool


# Built-in AI capabilities
CAPABILITY_SUMMARIZE = "summarize"
CAPABILITY_EXPLAIN = "explain"
CAPABILITY_CATEGORIZE = "categorize"
CAPABILITY_ORGANIZE = "organize"
CAPABILITY_GENERATE = "generate"
CAPABILITY_REVIEW = "review"
CAPABILITY_REFACTOR = "refactor"

# Valid capability types for validation
VALID_CAPABILITY_TYPES = {
    CAPABILITY_SUMMARIZE,
    CAPABILITY_EXPLAIN,
    CAPABILITY_CATEGORIZE,
    CAPABILITY_ORGANIZE,
    CAPABILITY_GENERATE,
    CAPABILITY_REVIEW,
    CAPABILITY_REFACTOR,
}


def validate_capability_type(capability_type: str) -> bool:
    """Validate that capability_type is a recognized AI capability."""
    return capability_type in VALID_CAPABILITY_TYPES


class CapabilityRegistry:
    """
    Central registry for AI capabilities.
    
    Benefits:
    - Plugin extensibility
    - Versioning
    - Feature flags
    - Permission checks
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, list[AICapability]] = {}
        self._entity_type_capabilities: dict[str, list[AICapability]] = {}

    def register_capability(
        self,
        entity_type: str,
        capability: AICapability
    ) -> None:
        """Register AI capability for entity type."""
        if capability.capability_type not in self._capabilities:
            self._capabilities[capability.capability_type] = []
        self._capabilities[capability.capability_type].append(capability)

        if entity_type not in self._entity_type_capabilities:
            self._entity_type_capabilities[entity_type] = []
        self._entity_type_capabilities[entity_type].append(capability)

    def get_capabilities(self, entity_type: str) -> list[AICapability]:
        """Get available capabilities for entity type."""
        return self._entity_type_capabilities.get(entity_type, [])

    def invoke_capability(
        self,
        entity_id: UUID,
        capability_type: str,
        parameters: dict[str, Any]
    ) -> Any:
        """Invoke AI capability on entity."""
        capabilities = self._capabilities.get(capability_type, [])
        for capability in capabilities:
            if entity_id in [cap.id for cap in capabilities]:  # Simplified check
                return capability.handler(entity_id, parameters)
        raise ValueError(f"Capability {capability_type} not found for entity {entity_id}")
