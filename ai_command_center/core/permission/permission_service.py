"""
Permission Service - Phase 1 Implementation

Permission checking and management following the frozen Permission contract.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from ai_command_center.core.permission.permission import (
    Permission,
    PermissionContext,
    validate_permission,
)
from ai_command_center.core.event_bus import (
    EVENT_PERMISSION_CHECK,
    EVENT_PERMISSION_DENIED,
)


class PermissionService:
    """
    Permission checking and management.
    
    Responsibilities:
    - Check permissions for actions
    - Grant/revoke permissions (for agents)
    - Event publishing for permission checks
    """

    def __init__(self, event_bus: Any) -> None:
        self._event_bus = event_bus
        # Default permissions for different actor types
        self._default_permissions: dict[str, set[str]] = {
            "user": {perm.value for perm in Permission},  # Users have all permissions
            "agent": {
                Permission.READ_ENTITY.value,
                Permission.SEARCH_ENTITY.value,
                Permission.USE_AI.value,
                Permission.ANALYZE_ENTITY.value,
            },  # Agents have limited permissions by default
            "system": {perm.value for perm in Permission},  # System has all permissions
        }
        # Agent-specific permissions (agent_id -> set of permissions)
        self._agent_permissions: dict[UUID, set[str]] = {}

    def check(
        self,
        permission: str,
        context: PermissionContext,
    ) -> bool:
        """Check if an actor has a specific permission."""
        if not validate_permission(permission):
            raise ValueError(f"Invalid permission: {permission}")
        
        # Publish check event
        self._event_bus.publish(
            EVENT_PERMISSION_CHECK,
            {
                "permission": permission,
                "entity_id": str(context.entity_id) if context.entity_id else None,
                "entity_type": context.entity_type,
                "action_id": str(context.action_id) if context.action_id else None,
                "actor_type": context.actor_type,
                "actor_id": str(context.actor_id) if context.actor_id else None,
            },
            source="permission_service",
        )
        
        # Get permissions for the actor
        if context.actor_type == "agent" and context.actor_id:
            actor_perms = self._agent_permissions.get(context.actor_id)
            if actor_perms is not None:
                has_permission = permission in actor_perms
            else:
                # Use default agent permissions
                has_permission = permission in self._default_permissions.get("agent", set())
        else:
            # Use default permissions for actor type
            has_permission = permission in self._default_permissions.get(context.actor_type, set())
        
        if not has_permission:
            # Publish denied event
            self._event_bus.publish(
                EVENT_PERMISSION_DENIED,
                {
                    "permission": permission,
                    "entity_id": str(context.entity_id) if context.entity_id else None,
                    "actor_type": context.actor_type,
                    "actor_id": str(context.actor_id) if context.actor_id else None,
                },
                source="permission_service",
            )
        
        return has_permission

    def grant(self, agent_id: UUID, permission: str) -> bool:
        """Grant a permission to an agent."""
        if not validate_permission(permission):
            raise ValueError(f"Invalid permission: {permission}")
        
        if agent_id not in self._agent_permissions:
            self._agent_permissions[agent_id] = set()
        
        self._agent_permissions[agent_id].add(permission)
        return True

    def revoke(self, agent_id: UUID, permission: str) -> bool:
        """Revoke a permission from an agent."""
        if agent_id not in self._agent_permissions:
            return False
        
        if permission in self._agent_permissions[agent_id]:
            self._agent_permissions[agent_id].remove(permission)
            return True
        return False

    def get_agent_permissions(self, agent_id: UUID) -> set[str]:
        """Get all permissions for an agent."""
        if agent_id in self._agent_permissions:
            return self._agent_permissions[agent_id].copy()
        return self._default_permissions.get("agent", set()).copy()

    def set_agent_permissions(self, agent_id: UUID, permissions: list[str]) -> None:
        """Set all permissions for an agent."""
        for perm in permissions:
            if not validate_permission(perm):
                raise ValueError(f"Invalid permission: {perm}")
        
        self._agent_permissions[agent_id] = set(permissions)
