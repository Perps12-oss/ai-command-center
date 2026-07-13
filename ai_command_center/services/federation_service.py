"""FederationService — EventBus integration for cross-workspace federation.

Subscribes to federation request topics and routes them through the
FederatedWorldModel query surface. Publishes results and conflict events.

Architecture contract:
- Extends BaseService for lifecycle management.
- No UI access. No direct repository access outside of FederatedWorldModel.
- All inter-service communication via EventBus.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import (
    FEDERATION_CONFLICT_DETECTED,
    FEDERATION_QUERY_REQUEST,
    FEDERATION_QUERY_RESULT,
    FEDERATION_SYNC_COMPLETED,
    FEDERATION_SYNC_STARTED,
    FEDERATION_WORKSPACE_REGISTERED,
    FEDERATION_WORKSPACE_UNREGISTERED,
)
from ai_command_center.core.world_model.federation.federated_world_model import FederatedWorldModel
from ai_command_center.core.world_model.federation.workspace_registry import WorkspaceRegistry
from ai_command_center.domain.federation import WorkspaceDescriptor
from ai_command_center.services.base import BaseService

logger = logging.getLogger(__name__)


class FederationService(BaseService):
    """Manages cross-workspace federation lifecycle and query dispatch.

    Event flow:
        FEDERATION_QUERY_REQUEST
            → FederatedWorldModel.query_nodes()
            → FEDERATION_QUERY_RESULT

        FEDERATION_WORKSPACE_REGISTERED (external trigger)
            → registry.register()
            → federated_model.add_workspace()
            → FEDERATION_SYNC_STARTED
            → FEDERATION_SYNC_COMPLETED

        FEDERATION_WORKSPACE_UNREGISTERED
            → registry.unregister()
            → federated_model.remove_workspace()
    """

    name = "federation_service"

    def __init__(
        self,
        bus: EventBus,
        registry: WorkspaceRegistry,
        federated_model: FederatedWorldModel,
    ) -> None:
        super().__init__(bus)
        self._registry = registry
        self._federated = federated_model
        self._unsubs: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubs = [
            self._bus.subscribe(FEDERATION_QUERY_REQUEST, self._on_query_request),
            self._bus.subscribe(FEDERATION_WORKSPACE_REGISTERED, self._on_register_workspace),
            self._bus.subscribe(FEDERATION_WORKSPACE_UNREGISTERED, self._on_unregister_workspace),
        ]
        self._restore_registered_workspaces()

    def _on_unload(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    def _restore_registered_workspaces(self) -> None:
        """Re-attach all previously registered workspaces on startup."""
        from ai_command_center.core.world_model.federation.federated_world_model import open_secondary_repo

        for descriptor in self._registry.list_all():
            try:
                repo = open_secondary_repo(descriptor.db_path)
                self._federated.add_workspace(descriptor, repo)
                logger.info(
                    "Federation: restored workspace %s (%s)",
                    descriptor.workspace_id, descriptor.name,
                )
            except Exception as exc:
                logger.warning(
                    "Federation: could not restore workspace %s: %s",
                    descriptor.workspace_id, exc,
                )

    def _on_query_request(self, event: Event) -> None:
        p = event.payload
        request_id = str(p.get("request_id") or "")
        query = str(p.get("query") or "")
        node_type = str(p.get("node_type") or "")
        limit = int(p.get("limit") or 100)
        workspace_ids: list[str] | None = p.get("workspace_ids")

        try:
            result = self._federated.query_nodes(
                query=query,
                node_type=node_type,
                limit=limit,
                workspace_ids=workspace_ids,
            )
            self._bus.publish(
                FEDERATION_QUERY_RESULT,
                {
                    "request_id": request_id,
                    "result": result.to_payload(),
                    "error": None,
                },
                source=self.name,
            )

            for conflict in self._federated.detect_conflicts():
                self._bus.publish(
                    FEDERATION_CONFLICT_DETECTED,
                    conflict,
                    source=self.name,
                )

        except Exception as exc:
            logger.error("Federation query failed: %s", exc)
            self._bus.publish(
                FEDERATION_QUERY_RESULT,
                {"request_id": request_id, "result": None, "error": str(exc)},
                source=self.name,
            )

    def _on_register_workspace(self, event: Event) -> None:
        from ai_command_center.core.world_model.federation.federated_world_model import open_secondary_repo

        p = event.payload
        try:
            descriptor = WorkspaceDescriptor.from_payload(p)
        except (KeyError, ValueError) as exc:
            logger.error("Federation: invalid workspace descriptor: %s", exc)
            return

        self._registry.register(descriptor)

        self._bus.publish(
            FEDERATION_SYNC_STARTED,
            {"workspace_id": descriptor.workspace_id},
            source=self.name,
        )

        try:
            repo = open_secondary_repo(descriptor.db_path)
            self._federated.add_workspace(descriptor, repo)
            sync_records = [
                r for r in self._federated.get_sync_status()
                if r.workspace_id == descriptor.workspace_id
            ]
            node_count = sync_records[0].node_count if sync_records else 0
            self._bus.publish(
                FEDERATION_SYNC_COMPLETED,
                {
                    "workspace_id": descriptor.workspace_id,
                    "node_count": node_count,
                    "error": None,
                },
                source=self.name,
            )
            logger.info("Federation: registered workspace %s", descriptor.workspace_id)
        except Exception as exc:
            logger.error("Federation: could not open workspace %s: %s", descriptor.workspace_id, exc)
            self._bus.publish(
                FEDERATION_SYNC_COMPLETED,
                {
                    "workspace_id": descriptor.workspace_id,
                    "node_count": 0,
                    "error": str(exc),
                },
                source=self.name,
            )

    def _on_unregister_workspace(self, event: Event) -> None:
        workspace_id = str(event.payload.get("workspace_id") or "")
        if not workspace_id:
            return
        removed_from_registry = self._registry.unregister(workspace_id)
        removed_from_model = self._federated.remove_workspace(workspace_id)
        logger.info(
            "Federation: unregistered workspace %s (registry=%s, model=%s)",
            workspace_id, removed_from_registry, removed_from_model,
        )
