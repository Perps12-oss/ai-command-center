"""
Workspace OS Service - Phase 2 Integration Wrapper

Lifecycle wrapper that exposes all Phase 1 Workspace OS services through a single
BaseService-compatible registration. This allows the ServiceManager to orchestrate
the new services without modifying the existing service architecture.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_command_center.core.event_bus import EVENT_TIMELINE_EVENT
from ai_command_center.core.permission.permission_client import PermissionClient
from ai_command_center.services.base import BaseService

if TYPE_CHECKING:
    from ai_command_center.core.action.action_registry import ActionRegistry
    from ai_command_center.core.ai.capability_registry_service import (
        AICapabilityRegistryService,
    )
    from ai_command_center.core.entity.entity_service import EntityService
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.core.feature.feature_registry import FeatureRegistry
    from ai_command_center.core.observability.observability_service import (
        ObservabilityService,
    )
    from ai_command_center.core.permission.permission_service import PermissionService
    from ai_command_center.core.relationship.relationship_service import RelationshipService
    from ai_command_center.core.search.command_palette_service import CommandPaletteService
    from ai_command_center.core.search.search_provider import SearchProvider
    from ai_command_center.core.snapshot.snapshot_service import SnapshotService
    from ai_command_center.core.timeline.timeline_service import TimelineService
    from ai_command_center.core.workspace.workspace_service import WorkspaceService


class WorkspaceOsService(BaseService):
    """
    Lifecycle wrapper and composition root for Workspace OS services.

    Public attributes expose the underlying Phase 1 services so UI and other
    services can use them without breaking the BaseService registration model.
    """

    name = "workspace_os"

    def __init__(
        self,
        bus: EventBus,
        entity_service: EntityService,
        relationship_service: RelationshipService,
        workspace_service: WorkspaceService,
        action_registry: ActionRegistry,
        timeline_service: TimelineService,
        permission_service: PermissionService,
        observability_service: ObservabilityService,
        snapshot_service: SnapshotService,
        feature_registry: FeatureRegistry,
        ai_capability_registry_service: AICapabilityRegistryService,
        command_palette_service: CommandPaletteService,
        search_provider: SearchProvider,
    ) -> None:
        super().__init__(bus)

        self.entity_service = entity_service
        self.relationship_service = relationship_service
        self.workspace_service = workspace_service
        self.action_registry = action_registry
        self.timeline_service = timeline_service
        self.permission_service = permission_service
        self._permission_client = PermissionClient(bus)
        self.observability_service = observability_service
        self.snapshot_service = snapshot_service
        self.feature_registry = feature_registry
        self.ai_capability_registry_service = ai_capability_registry_service
        self.command_palette_service = command_palette_service
        self.search_provider = search_provider

        self._enabled = True

    @property
    def enabled(self) -> bool:
        """Whether the Workspace OS service layer is enabled."""
        return self._enabled

    def _on_load(self) -> None:
        """
        Load hook: orchestrate feature flag enablement, action registration, and
        UI command subscriptions.

        WorkspaceOsService does not own action logic; it only orchestrates the
        registration of built-in actions by delegating to workspace_os_actions.
        """
        from ai_command_center.core.events.topics import (
            UI_CREATE_CARD,
            UI_CREATE_RESOURCE,
            UI_CREATE_WORKSPACE,
            UI_DELETE_RESOURCE,
            UI_LAUNCH_RESOURCE,
            UI_RENAME_WORKSPACE,
            UI_SEARCH_WORKSPACE_OS,
            UI_UPDATE_RESOURCE,
        )
        from ai_command_center.core.feature.feature import (
            Feature,
            FeatureStage,
        )
        from ai_command_center.core.workspace_os_actions import (
            register_workspace_os_actions,
        )

        self.feature_registry.register(
            feature=Feature.FEATURE_WORKSPACES,
            enabled=True,
            stage=FeatureStage.EXPERIMENTAL,
            metadata={"track": "workspace_os_phase2"},
        )
        register_workspace_os_actions(self.action_registry)
        self.timeline_service.start()
        self.permission_service.start()

        self._unsubs = [
            self._bus.subscribe(UI_CREATE_WORKSPACE, self._on_create_workspace),
            self._bus.subscribe(UI_CREATE_CARD, self._on_create_card),
            self._bus.subscribe(UI_CREATE_RESOURCE, self._on_create_resource),
            self._bus.subscribe(UI_UPDATE_RESOURCE, self._on_update_resource),
            self._bus.subscribe(UI_DELETE_RESOURCE, self._on_delete_resource),
            self._bus.subscribe(UI_LAUNCH_RESOURCE, self._on_launch_resource),
            self._bus.subscribe(UI_RENAME_WORKSPACE, self._on_rename_workspace),
            self._bus.subscribe(UI_SEARCH_WORKSPACE_OS, self._on_search),
        ]

    def _on_unload(self) -> None:
        """Unsubscribe from UI command topics on shutdown."""
        for unsub in getattr(self, "_unsubs", []):
            unsub()
        self._unsubs.clear()
        self.timeline_service.stop()
        self.permission_service.stop()
        self._permission_client.close()

    def _on_create_workspace(self, event: Any) -> None:
        """Handle UI_CREATE_WORKSPACE event."""
        payload = event.payload
        workspace = self.workspace_service.create(
            title=payload["title"],
            description=payload.get("description", ""),
        )
        self.timeline_service.record(
            event_type="Created Workspace",
            entity_id=workspace.id,
            entity_type="workspace",
            payload={"title": workspace.title},
        )

    def _on_create_card(self, event: Any) -> None:
        """Handle UI_CREATE_CARD event."""
        from uuid import UUID

        payload = event.payload
        card = self.entity_service.create(
            entity_type="card",
            title=payload["title"],
            description=payload.get("description", ""),
        )
        self.workspace_service.add_entity(
            workspace_id=UUID(payload["workspace_id"]),
            entity_id=card.id,
        )
        self.timeline_service.record(
            event_type="Created Card",
            entity_id=card.id,
            entity_type="card",
            payload={"title": card.title, "workspace_id": payload["workspace_id"]},
        )

    def _on_create_resource(self, event: Any) -> None:
        """Handle UI_CREATE_RESOURCE event."""
        from uuid import UUID

        from ai_command_center.core.entity.entity import (
            ENTITY_TYPE_RESOURCE,
            RESOURCE_TYPE_COMMAND,
            RESOURCE_TYPE_FOLDER,
            RESOURCE_TYPE_URL,
        )

        payload = event.payload
        resource_type = payload["resource_type"]
        value_key = {
            RESOURCE_TYPE_URL: "url",
            RESOURCE_TYPE_FOLDER: "path",
            RESOURCE_TYPE_COMMAND: "command",
        }.get(resource_type, "value")

        resource = self.entity_service.create(
            entity_type=ENTITY_TYPE_RESOURCE,
            title=payload["title"],
            description=payload.get("description", ""),
            metadata={
                "resource_type": resource_type,
                value_key: payload["value"],
            },
        )
        from ai_command_center.core.relationship.relationship import RelationshipType

        self.relationship_service.create(
            source_id=UUID(payload["card_id"]),
            target_id=resource.id,
            relationship_type=RelationshipType.CONTAINS,
        )
        self.timeline_service.record(
            event_type="Created Resource",
            entity_id=resource.id,
            entity_type="resource",
            payload={"title": resource.title, "resource_type": resource_type},
        )

    def _on_rename_workspace(self, event: Any) -> None:
        """Handle UI_RENAME_WORKSPACE event."""
        from uuid import UUID

        payload = event.payload
        workspace_id = UUID(payload["workspace_id"])
        title = payload["title"]
        updated = self.workspace_service.get(workspace_id)
        if updated is None:
            raise ValueError(f"Workspace not found: {workspace_id}")
        old_title = updated.title
        self.entity_service.update(
            entity_id=workspace_id,
            title=title,
            metadata=updated.metadata,
        )
        self.timeline_service.record(
            event_type="Renamed Workspace",
            entity_id=workspace_id,
            entity_type="workspace",
            payload={"old_title": old_title, "new_title": title},
        )

    def _on_update_resource(self, event: Any) -> None:
        """Handle UI_UPDATE_RESOURCE event."""
        from uuid import UUID

        from ai_command_center.core.entity.entity import (
            RESOURCE_TYPE_COMMAND,
            RESOURCE_TYPE_FOLDER,
            RESOURCE_TYPE_URL,
        )

        payload = event.payload
        resource_id = UUID(payload["resource_id"])
        resource_type = payload["resource_type"]
        value_key = {
            RESOURCE_TYPE_URL: "url",
            RESOURCE_TYPE_FOLDER: "path",
            RESOURCE_TYPE_COMMAND: "command",
        }.get(resource_type, "value")
        resource = self.entity_service.get(resource_id)
        if resource is None:
            raise ValueError(f"Resource not found: {resource_id}")
        metadata = {**dict(resource.metadata), "resource_type": resource_type, value_key: payload["value"]}
        self.entity_service.update(
            entity_id=resource_id,
            title=payload["title"],
            description=payload.get("description", ""),
            metadata=metadata,
        )
        self.timeline_service.record(
            event_type="Updated Resource",
            entity_id=resource_id,
            entity_type="resource",
            payload={"title": payload["title"], "resource_type": resource_type},
        )

    def _on_delete_resource(self, event: Any) -> None:
        """Handle UI_DELETE_RESOURCE event."""
        from uuid import UUID

        payload = event.payload
        resource_id = UUID(payload["resource_id"])
        resource = self.entity_service.get(resource_id)
        if resource is None:
            raise ValueError(f"Resource not found: {resource_id}")
        self.entity_service.delete(resource_id)
        card_id = payload.get("card_id")
        if card_id:
            self.relationship_service.delete_between(
                source_id=UUID(card_id),
                target_id=resource_id,
            )
        self.timeline_service.record(
            event_type="Deleted Resource",
            entity_id=resource_id,
            entity_type="resource",
            payload={"title": resource.title},
        )

    def _on_launch_resource(self, event: Any) -> None:
        """Handle UI_LAUNCH_RESOURCE event."""
        from uuid import UUID

        from ai_command_center.core.entity.entity import (
            RESOURCE_TYPE_COMMAND,
            RESOURCE_TYPE_FOLDER,
        )
        from ai_command_center.core.permission.permission import (
            Permission,
            PermissionContext,
        )

        payload = event.payload
        resource_type = payload["resource_type"]
        value = payload["value"]
        resource_id = UUID(payload["resource_id"])

        permission = (
            Permission.LAUNCH_TOOL.value
            if resource_type == RESOURCE_TYPE_COMMAND
            else Permission.EXECUTE_ACTION.value
        )
        context = PermissionContext(
            entity_id=resource_id,
            entity_type="resource",
            action_id=None,
            actor_type="user",
            actor_id=None,
        )
        if not self._permission_client.check(permission, context):
            self._bus.publish(
                EVENT_TIMELINE_EVENT,
                {
                    "event_type": "Permission Denied",
                    "entity_id": str(resource_id),
                    "entity_type": "resource",
                    "payload": {
                        "permission": permission,
                        "resource_type": resource_type,
                        "reason": "launch_resource",
                    },
                },
                source=self.name,
            )
            return

        action_name = {
            RESOURCE_TYPE_FOLDER: "Open Folder",
            RESOURCE_TYPE_COMMAND: "Execute Command",
        }.get(resource_type, "Launch URL")  # URL and default to Launch URL

        actions = [
            a for a in self.action_registry.get_by_type("launch") if a.name == action_name
        ]
        if not actions:
            raise ValueError(f"Launch action not found for resource type: {resource_type}")

        params = {"url": value, "path": value, "command": value}
        self.action_registry.invoke(actions[0].id, parameters=params)

        self.timeline_service.record(
            event_type=action_name,
            entity_id=resource_id,
            entity_type="resource",
        )

    def _on_search(self, event: Any) -> None:
        """Handle UI_SEARCH_WORKSPACE_OS event."""
        query = event.payload["query"]
        results = self.entity_service.search(query)
        # Publish search results for future UI consumption; inspector currently
        # refreshes via entity events.
        from ai_command_center.core.event_bus import EVENT_SEARCH_RESULTS

        self._bus.publish(
            EVENT_SEARCH_RESULTS,
            {"query": query, "count": len(results)},
            source=self.name,
        )
