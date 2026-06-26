"""
Command Palette Service - Phase 1 Implementation

Universal command palette for Search Everything, Create Anything, Run Anything, Open Anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from ai_command_center.core.event_bus import (
    Event,
    EVENT_COMMAND_PALETTE_OPENED,
    EVENT_COMMAND_PALETTE_SEARCH,
    EVENT_COMMAND_PALETTE_ITEM_SELECTED,
)


@dataclass(frozen=True, slots=True)
class CommandPaletteItem:
    """Universal command palette item."""

    id: UUID
    type: str  # action, entity, search, workspace

    label: str
    description: str

    # Action invocation
    action_id: UUID | None
    entity_id: UUID | None

    # Search integration
    search_query: str | None

    # Keyboard shortcut
    shortcut: str | None

    # AI integration
    ai_generated: bool


class CommandPaletteService:
    """
    Universal command palette service.
    
    Responsibilities:
    - Index items (actions, entities, workspaces)
    - Fuzzy search
    - Invoke selected items
    - Event publishing for palette operations
    """

    def __init__(self, event_bus: Any) -> None:
        self._event_bus = event_bus
        self._items: list[CommandPaletteItem] = []

    def register_item(self, item: CommandPaletteItem) -> None:
        """Register an item in the command palette."""
        self._items.append(item)

    def search(self, query: str, limit: int = 20) -> list[CommandPaletteItem]:
        """
        Search command palette items.
        
        Placeholder: fuzzy search will be implemented with RapidFuzz in Phase 1.
        For now, use simple substring matching.
        """
        query_lower = query.lower()
        
        results = []
        for item in self._items:
            if query_lower in item.label.lower() or query_lower in item.description.lower():
                results.append(item)
                if len(results) >= limit:
                    break
        
        # Publish search event
        self._event_bus.publish(
            EVENT_COMMAND_PALETTE_SEARCH,
            {"query": query, "result_count": len(results)},
            source="command_palette_service",
        )
        
        return results

    def invoke(self, item_id: UUID, parameters: dict[str, Any] | None = None) -> Any:
        """
        Invoke a command palette item.
        
        This delegates to the appropriate handler (action registry, entity service, etc.).
        """
        item = next((i for i in self._items if i.id == item_id), None)
        if item is None:
            raise ValueError(f"Item not found: {item_id}")
        
        # Publish selection event
        self._event_bus.publish(
            EVENT_COMMAND_PALETTE_ITEM_SELECTED,
            {
                "item_id": str(item.id),
                "item_type": item.type,
                "label": item.label,
            },
            source="command_palette_service",
        )
        
        # Placeholder: actual invocation logic depends on item type
        # This will be implemented when integrating with ActionRegistry and EntityService
        return {"item_id": str(item.id), "invoked": True}

    def open(self) -> None:
        """Open the command palette."""
        self._event_bus.publish(
            EVENT_COMMAND_PALETTE_OPENED,
            {},
            source="command_palette_service",
        )

    def get_items_by_type(self, item_type: str) -> list[CommandPaletteItem]:
        """Get all items of a specific type."""
        return [item for item in self._items if item.type == item_type]

    def list_all(self) -> list[CommandPaletteItem]:
        """List all command palette items."""
        return self._items.copy()
