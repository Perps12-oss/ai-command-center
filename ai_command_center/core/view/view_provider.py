"""
View Provider Contract - FROZEN ARCHITECTURE SPECIFICATION

Contract for rendering entities into different views. Implementation deferred.

FROZEN: Phase 2 - Workspace OS Integration
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from ai_command_center.core.entity.entity import Entity


@dataclass(frozen=True, slots=True)
class InteractiveElement:
    """Interactive element inside a rendered view."""

    element_type: str  # button, link, input, select
    label: str
    action_id: UUID | None
    parameters: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ViewRenderResult:
    """Result of rendering an entity into a view."""

    view_type: str  # list, card, tree, graph, timeline
    data: dict[str, Any]
    interactive_elements: list[InteractiveElement]


class ViewProvider(ABC):
    """
    View provider contract.
    
    Purpose:
    - Render entities as list views, card views, tree views, graph views, etc.
    - Keep view logic decoupled from entities and UI
    - Enable multiple views for the same data
    
    Implementation is deferred. Only the contract exists now.
    """

    @abstractmethod
    def supports(self, entity_type: str) -> bool:
        """Check if this provider can render the given entity type."""
        pass

    @abstractmethod
    def render(self, entity: Entity) -> ViewRenderResult:
        """Render the entity into a view result."""
        pass

    @abstractmethod
    def get_view_metadata(self) -> dict[str, Any]:
        """Return metadata about this provider (name, version, supported entity types)."""
        pass
