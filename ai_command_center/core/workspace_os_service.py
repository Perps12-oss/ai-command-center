"""

Workspace OS Service - Phase 2 Integration Wrapper



Lifecycle wrapper that exposes all Phase 1 Workspace OS services through a single

BaseService-compatible registration. UI commands are orchestrated via EventBus

request/result topics (Program 3 W3); no direct service-to-service calls in handlers.

"""



from __future__ import annotations



import uuid

from typing import TYPE_CHECKING, Any



from ai_command_center.core.entity.entity_bus_handlers import RESOURCE_VALUE_KEYS

from ai_command_center.core.events.topics import (

    ACTION_INVOKE_REQUEST,

    ACTION_INVOKE_RESULT,

    ENTITY_CREATE_REQUEST,

    ENTITY_CREATE_RESULT,

    ENTITY_SEARCH_REQUEST,

    ENTITY_SEARCH_RESULT,

    RELATIONSHIP_CREATE_REQUEST,

    RELATIONSHIP_CREATE_RESULT,

    SEARCH_RESULTS,

    TIMELINE_RECORD_REQUEST,

    TIMELINE_RECORD_RESULT,

    UI_CREATE_CARD,

    UI_CREATE_RESOURCE,

    UI_CREATE_WORKSPACE,

    UI_LAUNCH_RESOURCE,

    UI_SEARCH_WORKSPACE_OS,

    WORKSPACE_ADD_ENTITY_REQUEST,

    WORKSPACE_ADD_ENTITY_RESULT,

    WORKSPACE_CREATE_REQUEST,

    WORKSPACE_CREATE_RESULT,

)

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



    Public attributes expose the underlying Phase 1 services for tests and

    composition roots. Event handlers publish bus requests only.

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

        self.observability_service = observability_service

        self.snapshot_service = snapshot_service

        self.feature_registry = feature_registry

        self.ai_capability_registry_service = ai_capability_registry_service

        self.command_palette_service = command_palette_service

        self.search_provider = search_provider



        self._enabled = True

        self._pending: dict[str, dict[str, object]] = {}



    @property

    def enabled(self) -> bool:

        """Whether the Workspace OS service layer is enabled."""

        return self._enabled



    def _request_result(self, request_id: str) -> dict[str, object]:

        return self._pending.setdefault(request_id, {})



    def _publish_request(self, topic: str, request_id: str, payload: dict[str, object]) -> None:

        self._bus.publish(topic, {"request_id": request_id, **payload}, source=self.name)



    def _await_result(self, request_id: str) -> dict[str, object]:

        return dict(self._pending.pop(request_id, {}))



    def _on_load(self) -> None:

        """

        Load hook: orchestrate feature flag enablement, action registration, and

        UI command subscriptions.



        WorkspaceOsService does not own action logic; it only orchestrates the

        registration of built-in actions by delegating to workspace_os_actions.

        """

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

        # PermissionService bus handlers are wired once in service_factory.



        self._unsubs = [

            self._bus.subscribe(ENTITY_CREATE_RESULT, self._on_entity_create_result),

            self._bus.subscribe(ENTITY_SEARCH_RESULT, self._on_entity_search_result),

            self._bus.subscribe(

                RELATIONSHIP_CREATE_RESULT, self._on_relationship_create_result

            ),

            self._bus.subscribe(WORKSPACE_CREATE_RESULT, self._on_workspace_create_result),

            self._bus.subscribe(

                WORKSPACE_ADD_ENTITY_RESULT, self._on_workspace_add_entity_result

            ),

            self._bus.subscribe(ACTION_INVOKE_RESULT, self._on_action_invoke_result),

            self._bus.subscribe(TIMELINE_RECORD_RESULT, self._on_timeline_record_result),

            self._bus.subscribe(UI_CREATE_WORKSPACE, self._on_create_workspace),

            self._bus.subscribe(UI_CREATE_CARD, self._on_create_card),

            self._bus.subscribe(UI_CREATE_RESOURCE, self._on_create_resource),

            self._bus.subscribe(UI_LAUNCH_RESOURCE, self._on_launch_resource),

            self._bus.subscribe(UI_SEARCH_WORKSPACE_OS, self._on_search),

        ]



    def _store_result(self, event: Any) -> None:

        request_id = str(event.payload.get("request_id", ""))

        if request_id:

            self._request_result(request_id).update(dict(event.payload))



    def _on_entity_create_result(self, event: Any) -> None:

        self._store_result(event)



    def _on_entity_search_result(self, event: Any) -> None:

        self._store_result(event)



    def _on_relationship_create_result(self, event: Any) -> None:

        self._store_result(event)



    def _on_workspace_create_result(self, event: Any) -> None:

        self._store_result(event)



    def _on_workspace_add_entity_result(self, event: Any) -> None:

        self._store_result(event)



    def _on_action_invoke_result(self, event: Any) -> None:

        self._store_result(event)



    def _on_timeline_record_result(self, event: Any) -> None:

        self._store_result(event)



    def _on_unload(self) -> None:

        """Unsubscribe from UI command topics on shutdown."""

        for unsub in getattr(self, "_unsubs", []):

            unsub()

        self._unsubs.clear()

        self._pending.clear()



    def _on_create_workspace(self, event: Any) -> None:

        """Handle UI_CREATE_WORKSPACE event via workspace.create.request."""

        payload = event.payload

        request_id = uuid.uuid4().hex

        self._pending[request_id] = {}

        self._publish_request(

            WORKSPACE_CREATE_REQUEST,

            request_id,

            {

                "title": payload["title"],

                "description": payload.get("description", ""),

            },

        )

        result = self._await_result(request_id)

        if result.get("error"):

            raise ValueError(str(result["error"]))



    def _on_create_card(self, event: Any) -> None:

        """Handle UI_CREATE_CARD: entity.create.request → workspace.add_entity.request."""

        payload = event.payload

        request_id = uuid.uuid4().hex

        self._pending[request_id] = {}

        self._publish_request(

            ENTITY_CREATE_REQUEST,

            request_id,

            {

                "entity_type": "card",

                "title": payload["title"],

                "description": payload.get("description", ""),

                "metadata": {"workspace_id": payload["workspace_id"]},

            },

        )

        create_result = self._await_result(request_id)

        if create_result.get("error"):

            raise ValueError(str(create_result["error"]))

        entity_id = str(create_result.get("entity_id", ""))



        add_request_id = uuid.uuid4().hex

        self._pending[add_request_id] = {}

        self._publish_request(

            WORKSPACE_ADD_ENTITY_REQUEST,

            add_request_id,

            {

                "workspace_id": payload["workspace_id"],

                "entity_id": entity_id,

            },

        )

        add_result = self._await_result(add_request_id)

        if add_result.get("error"):

            raise ValueError(str(add_result["error"]))



    def _on_create_resource(self, event: Any) -> None:

        """Handle UI_CREATE_RESOURCE via entity + relationship bus requests."""

        from ai_command_center.core.entity.entity import (

            ENTITY_TYPE_RESOURCE,

        )

        from ai_command_center.core.relationship.relationship import RelationshipType



        payload = event.payload

        resource_type = payload["resource_type"]

        value_key = RESOURCE_VALUE_KEYS.get(resource_type, "value")



        request_id = uuid.uuid4().hex

        self._pending[request_id] = {}

        self._publish_request(

            ENTITY_CREATE_REQUEST,

            request_id,

            {

                "entity_type": ENTITY_TYPE_RESOURCE,

                "title": payload["title"],

                "description": payload.get("description", ""),

                "metadata": {

                    "resource_type": resource_type,

                    value_key: payload["value"],

                    "card_id": payload["card_id"],

                },

            },

        )

        create_result = self._await_result(request_id)

        if create_result.get("error"):

            raise ValueError(str(create_result["error"]))



        rel_request_id = uuid.uuid4().hex

        self._pending[rel_request_id] = {}

        self._publish_request(

            RELATIONSHIP_CREATE_REQUEST,

            rel_request_id,

            {

                "source_id": payload["card_id"],

                "target_id": str(create_result.get("entity_id", "")),

                "relationship_type": RelationshipType.CONTAINS.value,

            },

        )

        rel_result = self._await_result(rel_request_id)

        if rel_result.get("error"):

            raise ValueError(str(rel_result["error"]))



    def _on_launch_resource(self, event: Any) -> None:

        """Handle UI_LAUNCH_RESOURCE via action.invoke.request + timeline.record.request."""

        from ai_command_center.core.entity.entity import (

            RESOURCE_TYPE_COMMAND,

            RESOURCE_TYPE_FOLDER,

        )



        payload = event.payload

        resource_type = payload["resource_type"]

        value = payload["value"]

        resource_id = payload["resource_id"]



        action_name = {

            RESOURCE_TYPE_FOLDER: "Open Folder",

            RESOURCE_TYPE_COMMAND: "Execute Command",

        }.get(resource_type, "Launch URL")



        invoke_request_id = uuid.uuid4().hex

        self._pending[invoke_request_id] = {}

        self._publish_request(

            ACTION_INVOKE_REQUEST,

            invoke_request_id,

            {

                "action_type": "launch",

                "action_name": action_name,

                "parameters": {"url": value, "path": value, "command": value},

            },

        )

        invoke_result = self._await_result(invoke_request_id)

        if invoke_result.get("error"):

            raise ValueError(str(invoke_result["error"]))



        timeline_request_id = uuid.uuid4().hex

        self._pending[timeline_request_id] = {}

        self._publish_request(

            TIMELINE_RECORD_REQUEST,

            timeline_request_id,

            {

                "event_type": action_name,

                "entity_id": resource_id,

                "entity_type": "resource",

            },

        )

        self._await_result(timeline_request_id)



    def _on_search(self, event: Any) -> None:

        """Handle UI_SEARCH_WORKSPACE_OS via entity.search.request."""

        query = event.payload["query"]

        request_id = uuid.uuid4().hex

        self._pending[request_id] = {}

        self._publish_request(ENTITY_SEARCH_REQUEST, request_id, {"query": query})

        result = self._await_result(request_id)

        self._bus.publish(

            SEARCH_RESULTS,

            {"query": query, "count": result.get("count", 0)},

            source=self.name,

        )

