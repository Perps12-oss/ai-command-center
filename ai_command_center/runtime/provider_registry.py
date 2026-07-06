"""Registry of Agent Runtime Interface providers."""

from __future__ import annotations

from pathlib import Path

from ai_command_center.core.event_bus import EventBus
from ai_command_center.domain.runtime_capability import CapabilityKind
from ai_command_center.repositories.runtime_provider_manifest_repository import (
    RuntimeProviderManifestRepository,
)
from ai_command_center.runtime.agent_runtime_provider import AgentRuntimeProvider
from ai_command_center.runtime.providers.native_provider import NativeRuntimeProvider
from ai_command_center.runtime.providers.qwenpaw_health import QwenPawSidecarHealthState
from ai_command_center.runtime.runtime_plugin_loader import (
    instantiate_provider,
    load_manifests,
)

_DEFAULT_MANIFESTS_DIR = (
    Path(__file__).resolve().parents[2] / "plugins" / "runtime_manifests"
)


class RuntimeProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, AgentRuntimeProvider] = {}

    def register(self, provider: AgentRuntimeProvider) -> None:
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> AgentRuntimeProvider | None:
        return self._providers.get(provider_id)

    def list_ids(self) -> list[str]:
        return sorted(self._providers)

    def clear_providers(self, *, keep: set[str] | None = None) -> None:
        if keep:
            self._providers = {
                provider_id: provider
                for provider_id, provider in self._providers.items()
                if provider_id in keep
            }
            return
        self._providers.clear()

    def resolve_for_kind(self, kind: CapabilityKind, provider_id: str) -> AgentRuntimeProvider | None:
        provider = self.get(provider_id)
        if provider is None:
            return None
        if not provider.supports(kind):
            return None
        return provider


def build_runtime_registry_from_manifests(
    bus: EventBus | None = None,
    manifests_dir: Path | None = None,
    *,
    repo: RuntimeProviderManifestRepository | None = None,
    qwenpaw_health: QwenPawSidecarHealthState | None = None,
) -> RuntimeProviderRegistry:
    """Build a runtime registry from YAML manifests (native always registered first)."""
    registry = RuntimeProviderRegistry()
    registry.register(NativeRuntimeProvider())

    directory = manifests_dir or _DEFAULT_MANIFESTS_DIR
    repository = repo or RuntimeProviderManifestRepository()
    for manifest in load_manifests(directory, repo=repository):
        if manifest.id == "native":
            continue
        if not manifest.enabled:
            continue
        registry.register(
            instantiate_provider(
                manifest,
                bus=bus,
                qwenpaw_health=qwenpaw_health,
            )
        )
    return registry


def build_default_runtime_registry(
    bus: EventBus | None = None,
    *,
    qwenpaw_health: QwenPawSidecarHealthState | None = None,
) -> RuntimeProviderRegistry:
    """Backward-compatible alias — loads default runtime manifests."""
    return build_runtime_registry_from_manifests(
        bus,
        qwenpaw_health=qwenpaw_health,
    )
