"""Plugin manifest registry — EventBus catalog only, no dynamic imports (Phase 5B)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    PLUGIN_CATALOG,
    PLUGIN_DISABLE_REQUEST,
    PLUGIN_ENABLE_REQUEST,
    PLUGIN_ERROR,
    PLUGIN_STATE_CHANGED,
)
from ai_command_center.core.plugin_manifest import PluginManifest
from ai_command_center.repositories.plugin_manifest_repository import PluginManifestRepository
from ai_command_center.services.base import BaseService

_MANIFESTS_DIR = (
    Path(__file__).resolve().parents[2] / "plugins" / "manifests"
)


class PluginRegistryService(BaseService):
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
        self._plugins = {
            manifest.id: manifest
            for manifest in self._repo.list_manifests(self._manifests_dir)
        }

    def list_plugins(self) -> list[PluginManifest]:
        return sorted(self._plugins.values(), key=lambda p: p.id)

    def _publish_catalog(self) -> None:
        self._bus.publish(
            PLUGIN_CATALOG,
            {"plugins": [p.to_dict() for p in self.list_plugins()]},
            source=self.name,
        )

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
        updated = PluginManifest(
            id=current.id,
            name=current.name,
            version=current.version,
            description=current.description,
            kind=current.kind,
            bus_topics=current.bus_topics,
            enabled=enabled,
        )
        self._plugins[plugin_id] = updated
        self._bus.publish(
            PLUGIN_STATE_CHANGED,
            {"id": plugin_id, "enabled": enabled},
            source=self.name,
        )
        self._publish_catalog()

    def _on_enable_request(self, event: Event) -> None:
        plugin_id = str(event.payload.get("id", "")).strip()
        if plugin_id:
            self._set_enabled(plugin_id, True)

    def _on_disable_request(self, event: Event) -> None:
        plugin_id = str(event.payload.get("id", "")).strip()
        if plugin_id:
            self._set_enabled(plugin_id, False)
