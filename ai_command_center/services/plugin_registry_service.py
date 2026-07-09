"""Plugin manifest registry — EventBus catalog and persistent state (Phase 5B+)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    PLUGIN_CATALOG,
    PLUGIN_DISABLE_REQUEST,
    PLUGIN_ENABLE_REQUEST,
    PLUGIN_ERROR,
    PLUGIN_REGISTERED_ENTITY,
    PLUGIN_STATE_CHANGED,
    SERVICE_RESTART_REQUEST,
)
from ai_command_center.core.plugin_manifest import PluginManifest
from ai_command_center.repositories.plugin_manifest_repository import PluginManifestRepository
from ai_command_center.services.base import BaseService

_MANIFESTS_DIR = (
    Path(__file__).resolve().parents[2] / "plugins" / "manifests"
)


class PluginRegistryService(BaseService):
    """Loads manifests, persists enabled/disabled state, and requests service restarts.

    Core plugins cannot be disabled. Extension plugin changes are persisted to SQLite
    and may trigger a `service.restart_request` for the plugin's declared primary service.

    On catalog publish, each plugin is also projected as a Workspace OS resource entity
    via ``plugin.registered.entity`` (Program 4 slice 4).
    """

    name = "plugin_registry"

    def __init__(
        self,
        bus,
        manifests_dir: Path | None = None,
        repo: PluginManifestRepository | None = None,
    ) -> None:
        super().__init__(bus)
        self._manifests_dir = manifests_dir or _MANIFESTS_DIR
        self._repo = repo or PluginManifestRepository()
        self._plugins: dict[str, PluginManifest] = {}
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._load_manifests()
        self._publish_catalog()
        self._unsubscribers.append(
            self._bus.subscribe(PLUGIN_ENABLE_REQUEST, self._on_enable_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(PLUGIN_DISABLE_REQUEST, self._on_disable_request)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _load_manifests(self) -> None:
        persisted = self._repo.load_enabled_states()
        manifests = self._repo.list_manifests(self._manifests_dir)
        self._plugins = {
            manifest.id: (
                manifest
                if manifest.id not in persisted
                else PluginManifest(
                    id=manifest.id,
                    name=manifest.name,
                    version=manifest.version,
                    description=manifest.description,
                    kind=manifest.kind,
                    bus_topics=manifest.bus_topics,
                    enabled=persisted[manifest.id],
                    service=manifest.service,
                )
            )
            for manifest in manifests
        }

    def list_plugins(self) -> list[PluginManifest]:
        return sorted(self._plugins.values(), key=lambda p: p.id)

    def _publish_plugin_entities(self) -> None:
        for plugin in self.list_plugins():
            self._bus.publish(
                PLUGIN_REGISTERED_ENTITY,
                {
                    "plugin_id": plugin.id,
                    "id": plugin.id,
                    "name": plugin.name,
                    "description": plugin.description,
                    "kind": plugin.kind,
                    "enabled": plugin.enabled,
                    "service": plugin.service or "",
                    "version": plugin.version,
                },
                source=self.name,
            )

    def _publish_catalog(self) -> None:
        self._bus.publish(
            PLUGIN_CATALOG,
            {"plugins": [p.to_dict() for p in self.list_plugins()]},
            source=self.name,
        )
        self._publish_plugin_entities()

    def _set_enabled(self, plugin_id: str, enabled: bool) -> None:
        current = self._plugins.get(plugin_id)
        if current is None:
            self._bus.publish(
                PLUGIN_ERROR,
                {"message": f"unknown plugin: {plugin_id}"},
                source=self.name,
            )
            return
        if current.kind == "core" and not enabled:
            self._bus.publish(
                PLUGIN_ERROR,
                {"message": f"core plugin cannot be disabled: {plugin_id}"},
                source=self.name,
            )
            return

        try:
            self._repo.save_enabled_state(plugin_id, enabled)
        except Exception as exc:  # noqa: BLE001
            self._bus.publish(
                PLUGIN_ERROR,
                {"message": f"failed to persist plugin state: {exc}"},
                source=self.name,
            )
            return

        updated = PluginManifest(
            id=current.id,
            name=current.name,
            version=current.version,
            description=current.description,
            kind=current.kind,
            bus_topics=current.bus_topics,
            enabled=enabled,
            service=current.service,
        )
        self._plugins[plugin_id] = updated
        self._bus.publish(
            PLUGIN_STATE_CHANGED,
            {"id": plugin_id, "enabled": enabled, "pending_restart": bool(current.service)},
            source=self.name,
        )
        self._publish_catalog()
        if current.service:
            self._bus.publish(
                SERVICE_RESTART_REQUEST,
                {"service": current.service},
                source=self.name,
            )

    def _on_enable_request(self, event: Event) -> None:
        plugin_id = str(event.payload.get("id", "")).strip()
        if plugin_id:
            self._set_enabled(plugin_id, True)

    def _on_disable_request(self, event: Event) -> None:
        plugin_id = str(event.payload.get("id", "")).strip()
        if plugin_id:
            self._set_enabled(plugin_id, False)
