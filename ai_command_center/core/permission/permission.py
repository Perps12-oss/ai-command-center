"""
Permission System Contract - FROZEN ARCHITECTURE SPECIFICATION

This module defines the Permission system for the Workspace Operating System.
Capability permissions control what agents and actions can do.

FROZEN: Phase 0 - Universal Foundation
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class Permission(Enum):
    """
    Capability permissions - what agents/actions can do.
    
    Some agents should not be able to:
    - Delete Files
    - Run Shell Commands
    - Modify Repositories
    
    Design for this now.
    """

    # Read permissions
    READ_ENTITY = "read_entity"
    SEARCH_ENTITY = "search_entity"
    LIST_WORKSPACE = "list_workspace"

    # Write permissions
    CREATE_ENTITY = "create_entity"
    UPDATE_ENTITY = "update_entity"
    DELETE_ENTITY = "delete_entity"

    # Execution permissions
    EXECUTE_ACTION = "execute_action"
    RUN_WORKFLOW = "run_workflow"
    LAUNCH_TOOL = "launch_tool"

    # System permissions
    MODIFY_SETTINGS = "modify_settings"
    MANAGE_WORKSPACE = "manage_workspace"
    INSTALL_PLUGIN = "install_plugin"

    # AI permissions
    USE_AI = "use_ai"
    GENERATE_CONTENT = "generate_content"
    ANALYZE_ENTITY = "analyze_entity"


@dataclass(frozen=True, slots=True)
class PermissionContext:
    """
    Context for permission evaluation.
    """

    entity_id: UUID | None
    entity_type: str | None
    action_id: UUID | None
    actor_type: str  # user, agent, system
    actor_id: UUID | None


# Valid permissions for validation
VALID_PERMISSIONS = {perm.value for perm in Permission}


def validate_permission(permission: str) -> bool:
    """Validate that permission is a recognized Permission."""
    return permission in VALID_PERMISSIONS
