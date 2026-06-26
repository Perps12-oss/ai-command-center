"""
Action Contract - FROZEN ARCHITECTURE SPECIFICATION

This module defines the Action contract for the Workspace Operating System.
All capabilities are actions, enabling UI-independent execution.

FROZEN: Phase 0 - Universal Foundation
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Action:
    """
    Unified execution pipeline - all capabilities are actions.
    
    Actions enable multiple invocation paths:
    - Button → Action
    - Hotkey → Action
    - Command Palette → Action
    - Agent → Action
    - Workflow → Action
    - API → Action
    - Plugin → Action
    
    This is a massive scalability win over direct service calls.
    """

    id: UUID
    name: str  # Human-readable display name
    action_type: str  # Open, Edit, Delete, Launch, Execute, Analyze, etc.

    entity_id: UUID | None  # Target entity (if applicable)
    parameters: dict[str, Any]

    handler: Callable[[dict[str, Any]], Any]  # Execution logic

    # UI integration
    keyboard_shortcut: str | None
    context_menu: bool
    toolbar: bool
    command_palette: bool

    # Permissions
    required_permissions: list[str]

    # AI integration
    ai_executable: bool  # Can AI invoke this action?


# Core action types (built-in)
ACTION_TYPE_OPEN = "open"
ACTION_TYPE_EDIT = "edit"
ACTION_TYPE_DELETE = "delete"
ACTION_TYPE_LAUNCH = "launch"
ACTION_TYPE_EXECUTE = "execute"
ACTION_TYPE_ANALYZE = "analyze"
ACTION_TYPE_SUMMARIZE = "summarize"
ACTION_TYPE_GENERATE = "generate"
ACTION_TYPE_CLONE = "clone"
ACTION_TYPE_EXPORT = "export"
ACTION_TYPE_IMPORT = "import"

# Valid action types for validation
VALID_ACTION_TYPES = {
    ACTION_TYPE_OPEN,
    ACTION_TYPE_EDIT,
    ACTION_TYPE_DELETE,
    ACTION_TYPE_LAUNCH,
    ACTION_TYPE_EXECUTE,
    ACTION_TYPE_ANALYZE,
    ACTION_TYPE_SUMMARIZE,
    ACTION_TYPE_GENERATE,
    ACTION_TYPE_CLONE,
    ACTION_TYPE_EXPORT,
    ACTION_TYPE_IMPORT,
}

# Current schema version
ACTION_SCHEMA_VERSION = 1


def validate_action_type(action_type: str) -> bool:
    """Validate that action_type is a recognized action type."""
    return action_type in VALID_ACTION_TYPES
