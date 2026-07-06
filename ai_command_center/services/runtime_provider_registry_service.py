"""Runtime provider registry service — manifest-driven provider discovery (ARI Phase 5)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CAPABILITY_PROVIDERS_READY,
    PLUGIN_STATE_CHANGED,
)
from ai_command_center.domain.capability_provider_settings import (
    register_discovered_providers,
)
from ai_command_center.domain.runtime_provider_manifest import RuntimeProviderManifest
from ai_command_center.repositories.runtime_provider_manifest_repository import (
    RuntimeProviderManifestRepository,
)
from ai_command_center.runtime.provider_registry import RuntimeProviderRegistry
from ai_command_center.runtime.providers.native_provider import NativeRuntimeProvider
from ai_command_center.runtime.providers.qwenpaw_health import QwenPawSidecarHealthState
from ai_command_center.runtime.runtime_plugin_loader import (
    instantiate_provider,
    load_manifests,
)
from ai_command_center.services.base import BaseService

_MANIFESTS_DIR = (
    Path(__file__).resolve().parents[2] / "plugins" / "runtime_manifests"
)

_NATIVE_ID = "native"


class RuntimeProviderRegistryService(BaseService):
    """Loads runtime provider manifests and populates a shared registry.

    Provider reload on ``plugin.state_changed`` is supported for runtime_provider
    manifests; native is always registered and cannot be disabled.
    """

    name = "runtime_provider_registry"

    def __init__(
        self,
        bus,
        *,
        registry: RuntimeProviderRegistry,
        manifests_dir: Path | None = None,
        repo: RuntimeProviderManifestRepository | None = None,
        qwenpaw_health: QwenPawSidecarHealthState | None = None,
    ) -> None:
        super().__init__(bus)
        self._registry = registry
        self._manifests_dir = manifests_dir or _MANIFESTS_DIR
        self._repo = repo or RuntimeProviderManifestRepository()
        self._qwenpaw_health = qwenpaw_health or QwenPawSidecarHealthState()
        self._manifests: dict[str, RuntimeProviderManifest] = {}
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._reload_providers()
        self._unsubscribers.append(
            self._bus.subscribe(PLUGIN_STATE_CHANGED, self._on_plugin_state_changed)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def list_manifests(self) -> list[RuntimeProviderManifest]:
        return sorted(self._manifests.values(), key=lambda m: m.id)

    def _reload_providers(self) -> None:
        self._registry.clear_providers()
        self._registry.register(NativeRuntimeProvider())

        manifests = load_manifests(self._manifests_dir, repo=self._repo)
        self._manifests = {m.id: m for m in manifests}

        for manifest in manifests:
            if manifest.id == _NATIVE_ID:
                continue
            if not manifest.enabled:
                continue
            provider = instantiate_provider(
                manifest,
                bus=self._bus,
                qwenpaw_health=self._qwenpaw_health,
            )
            self._registry.register(provider)

        self._publish_providers_ready()

    def _publish_providers_ready(self) -> None:
        providers: list[dict[str, object]] = []
        for provider_id in self._registry.list_ids():
            provider = self._registry.get(provider_id)
            if provider is None:
                continue
            health = provider.health()
            manifest = self._manifests.get(provider_id)
            providers.append(
                {
                    "id": provider_id,
                    "name": manifest.name if manifest else provider_id,
                    "version": manifest.version if manifest else "",
                    "description": manifest.description if manifest else "",
                    "capabilities": (
                        [c.value for c in manifest.capabilities]
                        if manifest
                        else []
                    ),
                    "enabled": manifest.enabled if manifest else True,
                    "kind": manifest.kind if manifest else "builtin",
                    "health_state": health.state.value,
                    "health_detail": health.detail,
                }
            )
        self._bus.publish(
            CAPABILITY_PROVIDERS_READY,
            {"providers": providers},
            source=self.name,
        )
        register_discovered_providers(
            [str(p["id"]) for p in providers if str(p.get("id", "")) != _NATIVE_ID]
        )

    def _on_plugin_state_changed(self, event: Event) -> None:
        provider_id = str(event.payload.get("id", "")).strip()
        if not provider_id or provider_id == _NATIVE_ID:
            return
        if provider_id not in self._manifests:
            return
        self._reload_providers()
