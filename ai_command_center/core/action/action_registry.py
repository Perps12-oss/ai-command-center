"""
Action Registry - Phase 1 Implementation

Central registry for all actions following the frozen Action contract.
"""

from __future__ import annotations

from typing import Any, Callable
from uuid import UUID, uuid4

from ai_command_center.core.action.action import (
    Action,
    ACTION_SCHEMA_VERSION,
    validate_action_type,
)
from ai_command_center.core.event_bus import (
    Event,
    EVENT_ACTION_REGISTERED,
    EVENT_ACTION_INVOKED,
    EVENT_ACTION_COMPLETED,
    EVENT_ACTION_FAILED,
)


class ActionRegistry:
    """
    Central registry for all actions.
    
    Actions enable multiple invocation paths:
    - Button → Action
    - Hotkey → Action
    - Command Palette → Action
    - Agent → Action
    - Workflow → Action
    - API → Action
    - Plugin → Action
    """

    def __init__(self, event_bus: Any) -> None:
        self._event_bus = event_bus
        self._actions: dict[UUID, Action] = {}
        self._actions_by_type: dict[str, list[Action]] = {}

    def register(
        self,
        action_type: str,
        handler: Callable[[dict[str, Any]], Any],
        name: str = "",
        entity_id: UUID | None = None,
        parameters: dict[str, Any] | None = None,
        keyboard_shortcut: str | None = None,
        context_menu: bool = False,
        toolbar: bool = False,
        command_palette: bool = False,
        required_permissions: list[str] | None = None,
        ai_executable: bool = False,
    ) -> Action:
        """Register a new action."""
        if not validate_action_type(action_type):
            raise ValueError(f"Invalid action_type: {action_type}")
        if not name:
            name = action_type
        action = Action(
            id=uuid4(),
            name=name,
            action_type=action_type,
            entity_id=entity_id,
            parameters=parameters or {},
            handler=handler,
            keyboard_shortcut=keyboard_shortcut,
            context_menu=context_menu,
            toolbar=toolbar,
            command_palette=command_palette,
            required_permissions=required_permissions or [],
            ai_executable=ai_executable,
        )
        
        self._actions[action.id] = action
        
        if action_type not in self._actions_by_type:
            self._actions_by_type[action_type] = []
        self._actions_by_type[action_type].append(action)
        
        # Publish event
        self._event_bus.publish(
            EVENT_ACTION_REGISTERED,
            {
                "action_id": str(action.id),
                "action_type": action.action_type,
                "entity_id": str(action.entity_id) if action.entity_id else None,
            },
            source="action_registry",
        )
        
        return action

    def invoke(self, action_id: UUID, parameters: dict[str, Any] | None = None) -> Any:
        """Invoke an action by ID."""
        action = self._actions.get(action_id)
        if action is None:
            raise ValueError(f"Action not found: {action_id}")
        
        # Publish invocation event
        self._event_bus.publish(
            EVENT_ACTION_INVOKED,
            {
                "action_id": str(action.id),
                "action_type": action.action_type,
                "entity_id": str(action.entity_id) if action.entity_id else None,
            },
            source="action_registry",
        )
        
        try:
            # Merge parameters
            merged_params = {**action.parameters, **(parameters or {})}
            result = action.handler(merged_params)
            
            # Publish completion event
            self._event_bus.publish(
                EVENT_ACTION_COMPLETED,
                {
                    "action_id": str(action.id),
                    "action_type": action.action_type,
                    "success": True,
                },
                source="action_registry",
            )
            
            return result
        except Exception as e:
            # Publish failure event
            self._event_bus.publish(
                EVENT_ACTION_FAILED,
                {
                    "action_id": str(action.id),
                    "action_type": action.action_type,
                    "error": str(e),
                },
                source="action_registry",
            )
            raise

    def get(self, action_id: UUID) -> Action | None:
        """Get action by ID."""
        return self._actions.get(action_id)

    def get_by_type(self, action_type: str) -> list[Action]:
        """Get all actions of a specific type."""
        return self._actions_by_type.get(action_type, [])

    def get_by_entity(self, entity_id: UUID) -> list[Action]:
        """Get all actions for a specific entity."""
        return [action for action in self._actions.values() if action.entity_id == entity_id]

    def get_command_palette_actions(self) -> list[Action]:
        """Get all actions that should appear in command palette."""
        return [action for action in self._actions.values() if action.command_palette]

    def get_context_menu_actions(self, entity_id: UUID) -> list[Action]:
        """Get all actions that should appear in context menu for an entity."""
        return [
            action for action in self._actions.values()
            if action.context_menu and action.entity_id == entity_id
        ]

    def get_toolbar_actions(self) -> list[Action]:
        """Get all actions that should appear in toolbar."""
        return [action for action in self._actions.values() if action.toolbar]

    def get_ai_executable_actions(self) -> list[Action]:
        """Get all actions that AI can execute."""
        return [action for action in self._actions.values() if action.ai_executable]

    def list_all(self) -> list[Action]:
        """List all registered actions."""
        return list(self._actions.values())

    def unregister(self, action_id: UUID) -> bool:
        """Unregister an action."""
        action = self._actions.pop(action_id, None)
        if action:
            # Remove from type index
            if action.action_type in self._actions_by_type:
                self._actions_by_type[action.action_type] = [
                    a for a in self._actions_by_type[action.action_type] if a.id != action_id
                ]
            return True
        return False
