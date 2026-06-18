"""Plugin manifest registry — EventBus catalog only, no dynamic imports (Phase 5B)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import yaml

from ai_command_center.core.event_bus import Event
from ai_command_center.core.plugin_manifest import PluginManifest
from ai_command_center.services.base import BaseService

_MANIFESTS_DIR = (
    Path(__file__).resolve().parents[2] / "plugins" / "manifests"
)


def _parse_manifest(data: dict) -> PluginManifest | None:
    plugin_id = str(data.get("id", "")).strip()
    if not plugin_id:
        return None
    topics = data.get("bus_topics") or []
    return PluginManifest(
        id=plugin_id,
        name=str(data.get("name", plugin_id)),
        version=str(data.get("version", "1.0")),
        description=str(data.get("description", "")),
        kind=str(data.get("kind", "extension")),
        bus_topics=tuple(str(t) for t in topics),
        enabled=bool(data.get("enabled", True)),
    )


class PluginRegistryService(BaseService):
    name = "plugin_registry"

    def __init__(self, bus, manifests_dir: Path | None = None) -> None:
        super().__init__(bus)
        self._manifests_dir = manifests_dir or _MANIFESTS_DIR
        self._plugins: dict[str, PluginManifest] = {}
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._load_manifests()
        self._publish_catalog()
        self._unsubscribers.append(
            self._bus.subscribe("plugin.enable_request", self._on_enable_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe("plugin.disable_request", self._on_disable_request)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _load_manifests(self) -> None:
        self._plugins.clear()
        if not self._manifests_dir.is_dir():
            return
        for path in sorted(self._manifests_dir.glob("*.yaml")):
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except OSError:
                continue
            manifest = _parse_manifest(raw)
            if manifest is not None:
                self._plugins[manifest.id] = manifest

    def list_plugins(self) -> list[PluginManifest]:
        return sorted(self._plugins.values(), key=lambda p: p.id)

    def _publish_catalog(self) -> None:
        self._bus.publish(
            "plugin.catalog",
            {"plugins": [p.to_dict() for p in self.list_plugins()]},
            source=self.name,
        )

    def _set_enabled(self, plugin_id: str, enabled: bool) -> None:
        current = self._plugins.get(plugin_id)
        if current is None:
            self._bus.publish(
                "plugin.error",
                {"message": f"unknown plugin: {plugin_id}"},
                source=self.name,
            )
            return
        if current.kind == "core" and not enabled:
            self._bus.publish(
                "plugin.error",
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
            "plugin.state_changed",
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
