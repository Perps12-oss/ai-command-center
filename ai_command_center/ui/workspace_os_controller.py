"""UI bridge for Workspace OS — EventBus only, no direct service access."""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    UI_CREATE_CARD,
    UI_CREATE_RESOURCE,
    UI_CREATE_WORKSPACE,
    UI_INSPECTOR_CLOSE,
    UI_INSPECTOR_OPEN,
    UI_LAUNCH_RESOURCE,
    UI_OPEN_CHAT,
    UI_SEARCH_WORKSPACE_OS,
)


class WorkspaceOsUIController:
    """Publishes Workspace OS UI intents to the EventBus."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    def open_inspector(self) -> None:
        self._bus.publish(UI_INSPECTOR_OPEN, {}, source="ui")

    def close_inspector(self) -> None:
        self._bus.publish(UI_INSPECTOR_CLOSE, {}, source="ui")

    def create_workspace(self, title: str, description: str = "") -> None:
        self._bus.publish(
            UI_CREATE_WORKSPACE,
            {"title": title, "description": description},
            source="ui",
        )

    def create_card(self, workspace_id: str, title: str, description: str = "") -> None:
        self._bus.publish(
            UI_CREATE_CARD,
            {"workspace_id": workspace_id, "title": title, "description": description},
            source="ui",
        )

    def create_resource(
        self,
        card_id: str,
        title: str,
        resource_type: str,
        value: str,
        description: str = "",
    ) -> None:
        self._bus.publish(
            UI_CREATE_RESOURCE,
            {
                "card_id": card_id,
                "title": title,
                "resource_type": resource_type,
                "value": value,
                "description": description,
            },
            source="ui",
        )

    def launch_resource(self, resource_id: str, resource_type: str, value: str) -> None:
        self._bus.publish(
            UI_LAUNCH_RESOURCE,
            {
                "resource_id": resource_id,
                "resource_type": resource_type,
                "value": value,
            },
            source="ui",
        )

    def open_chat(self, entity_id: str, entity_type: str, title: str) -> None:
        self._bus.publish(
            UI_OPEN_CHAT,
            {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "title": title,
            },
            source="ui",
        )

    def search(self, query: str) -> None:
        self._bus.publish(
            UI_SEARCH_WORKSPACE_OS,
            {"query": query},
            source="ui",
        )
