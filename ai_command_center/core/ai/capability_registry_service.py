"""
AI Capability Registry Service - Phase 1 Implementation

Centralized AI capability management service following the frozen AICapability contract.
"""

from __future__ import annotations

from typing import Any, Callable
from uuid import UUID, uuid4

from ai_command_center.core.ai.capability import (
    AICapability,
    CapabilityRegistry,
    validate_capability_type,
)


class AICapabilityRegistryService:
    """
    AI capability management service.
    
    Responsibilities:
    - Register AI capabilities for entity types
    - Get capabilities for entity types
    - Invoke AI capabilities on entities
    - Permission checks for capability invocation
    """

    def __init__(self, permission_service: Any) -> None:
        self._permission_service = permission_service
        self._registry = CapabilityRegistry()

    def register_capability(
        self,
        entity_type: str,
        capability_type: str,
        handler: Callable[[UUID, dict[str, Any]], Any],
        supported_entity_types: list[str] | None = None,
        required_permissions: list[str] | None = None,
        context_menu: bool = False,
        command_palette: bool = False,
    ) -> AICapability:
        """Register an AI capability for an entity type."""
        if not validate_capability_type(capability_type):
            raise ValueError(f"Invalid capability_type: {capability_type}")
        
        capability = AICapability(
            id=uuid4(),
            capability_type=capability_type,
            supported_entity_types=supported_entity_types or [entity_type],
            handler=handler,
            required_permissions=required_permissions or [],
            context_menu=context_menu,
            command_palette=command_palette,
        )
        
        self._registry.register_capability(entity_type, capability)
        return capability

    def get_capabilities(self, entity_type: str) -> list[AICapability]:
        """Get available AI capabilities for an entity type."""
        return self._registry.get_capabilities(entity_type)

    def invoke_capability(
        self,
        entity_id: UUID,
        capability_type: str,
        parameters: dict[str, Any] | None = None,
        actor_type: str = "user",
        actor_id: UUID | None = None,
    ) -> Any:
        """
        Invoke an AI capability on an entity.
        
        Checks permissions before invocation.
        """
        from ai_command_center.core.permission.permission import PermissionContext
        
        # Get the capability
        capabilities = self._registry._capabilities.get(capability_type, [])
        if not capabilities:
            raise ValueError(f"Capability {capability_type} not found")
        
        capability = capabilities[0]  # Use first matching capability
        
        # Check permissions
        for perm in capability.required_permissions:
            context = PermissionContext(
                entity_id=entity_id,
                entity_type=None,
                action_id=None,
                actor_type=actor_type,
                actor_id=actor_id,
            )
            if not self._permission_service.check(perm, context):
                raise PermissionError(f"Permission denied: {perm}")
        
        # Invoke the capability
        return self._registry.invoke_capability(entity_id, capability_type, parameters or {})

    def list_all_capabilities(self) -> dict[str, list[AICapability]]:
        """List all registered capabilities by type."""
        return self._registry._capabilities.copy()
