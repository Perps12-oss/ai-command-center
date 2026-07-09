"""Bridge external/MCP capabilities into the planner catalog via EventBus."""

from __future__ import annotations

from collections.abc import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    EXTERNAL_CAPABILITY_CATALOG_UPDATED,
    EXTERNAL_CAPABILITY_REGISTER,
    EXTERNAL_CAPABILITY_REGISTERED,
    EXTERNAL_CAPABILITY_UNREGISTER,
)
from ai_command_center.domain.external_capability_manifest import ExternalCapabilityManifest
from ai_command_center.services.base import BaseService


class ExternalCapabilityBridgeService(BaseService):
    """Registers external capability manifests; catalog aggregates via bus events."""

    name = "external_capability_bridge"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._manifests: dict[str, ExternalCapabilityManifest] = {}
        self._unsubscribers: list[Callable[[], None]] = []

    def list_manifests(self) -> list[ExternalCapabilityManifest]:
        return [m for m in self._manifests.values() if m.enabled]

    def get_manifest(self, capability_id: str) -> ExternalCapabilityManifest | None:
        return self._manifests.get(capability_id)

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(EXTERNAL_CAPABILITY_REGISTER, self._on_register)
        )
        self._unsubscribers.append(
            self._bus.subscribe(EXTERNAL_CAPABILITY_UNREGISTER, self._on_unregister)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._manifests.clear()

    def _publish_catalog_updated(self) -> None:
        manifests = [m.to_dict() for m in self.list_manifests()]
        self._bus.publish(
            EXTERNAL_CAPABILITY_CATALOG_UPDATED,
            {"manifests": manifests, "count": len(manifests)},
            source=self.name,
        )

    def _on_register(self, event: Event) -> None:
        raw = event.payload.get("manifest")
        if not isinstance(raw, dict):
            capability_id = str(event.payload.get("capability_id", "")).strip()
            if not capability_id:
                return
            manifest = ExternalCapabilityManifest(
                capability_id=capability_id,
                name=str(event.payload.get("name", capability_id)),
                description=str(event.payload.get("description", "")),
                provider_id=str(event.payload.get("provider_id", "mcp")),
                risk=str(event.payload.get("risk", "medium")),
                kind=str(event.payload.get("kind", "mcp")),
                parameters=dict(event.payload.get("parameters") or {}),
                enabled=bool(event.payload.get("enabled", True)),
            )
        else:
            manifest = ExternalCapabilityManifest.from_dict(raw)

        if not manifest.capability_id:
            return

        self._manifests[manifest.capability_id] = manifest
        self._bus.publish(
            EXTERNAL_CAPABILITY_REGISTERED,
            {"manifest": manifest.to_dict()},
            source=self.name,
        )
        self._publish_catalog_updated()

    def _on_unregister(self, event: Event) -> None:
        capability_id = str(event.payload.get("capability_id", "")).strip()
        if not capability_id or capability_id not in self._manifests:
            return
        del self._manifests[capability_id]
        self._publish_catalog_updated()
