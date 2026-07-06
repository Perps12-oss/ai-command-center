"""Runtime provider plugin loader — manifest validation and allowlisted instantiation."""

from __future__ import annotations

from pathlib import Path

from ai_command_center.core.event_bus import EventBus
from ai_command_center.domain.runtime_provider_manifest import RuntimeProviderManifest
from ai_command_center.repositories.runtime_provider_manifest_repository import (
    RuntimeProviderManifestRepository,
)
from ai_command_center.runtime.agent_runtime_provider import AgentRuntimeProvider
from ai_command_center.runtime.providers.native_provider import NativeRuntimeProvider
from ai_command_center.runtime.providers.qwenpaw_health import QwenPawSidecarHealthState
from ai_command_center.runtime.providers.qwenpaw_sidecar_provider import (
    QwenPawSidecarProvider,
)
from ai_command_center.runtime.providers.stub_echo_provider import StubEchoProvider

ALLOWED_ENTRYPOINTS: frozenset[str] = frozenset(
    {
        "builtin:native",
        "builtin:qwenpaw",
        "builtin:stub_echo",
    }
)

_BUILTIN_FACTORIES: dict[str, str] = {
    "builtin:native": "native",
    "builtin:qwenpaw": "qwenpaw",
    "builtin:stub_echo": "stub_echo",
}


class ManifestValidationError(ValueError):
    """Raised when a runtime provider manifest fails validation."""


def validate_manifest(manifest: RuntimeProviderManifest) -> None:
    """Validate a runtime provider manifest; raise ManifestValidationError on failure."""
    if not manifest.id:
        raise ManifestValidationError("manifest id is required")
    if manifest.entrypoint not in ALLOWED_ENTRYPOINTS:
        raise ManifestValidationError(
            f"entrypoint {manifest.entrypoint!r} is not allowlisted"
        )
    if not manifest.capabilities:
        raise ManifestValidationError("at least one capability is required")


def load_manifests(
    manifests_dir: Path,
    *,
    repo: RuntimeProviderManifestRepository | None = None,
) -> list[RuntimeProviderManifest]:
    """Load and validate runtime provider manifests from a directory."""
    repository = repo or RuntimeProviderManifestRepository()
    persisted = repository.load_enabled_states()
    result: list[RuntimeProviderManifest] = []
    for manifest in repository.list_manifests(manifests_dir):
        try:
            validate_manifest(manifest)
        except ManifestValidationError:
            continue
        enabled = (
            persisted[manifest.id] if manifest.id in persisted else manifest.enabled
        )
        if manifest.kind == "core":
            enabled = True
        result.append(
            RuntimeProviderManifest(
                id=manifest.id,
                name=manifest.name,
                version=manifest.version,
                description=manifest.description,
                entrypoint=manifest.entrypoint,
                capabilities=manifest.capabilities,
                enabled=enabled,
                kind=manifest.kind,
            )
        )
    return result


def instantiate_provider(
    manifest: RuntimeProviderManifest,
    *,
    bus: EventBus | None = None,
    qwenpaw_health: QwenPawSidecarHealthState | None = None,
) -> AgentRuntimeProvider:
    """Instantiate a provider from an allowlisted builtin entrypoint."""
    validate_manifest(manifest)
    if manifest.entrypoint == "builtin:native":
        return NativeRuntimeProvider()
    if manifest.entrypoint == "builtin:qwenpaw":
        return QwenPawSidecarProvider(
            bus=bus, health_state=qwenpaw_health or QwenPawSidecarHealthState()
        )
    if manifest.entrypoint == "builtin:stub_echo":
        return StubEchoProvider(bus=bus)
    raise ManifestValidationError(
        f"no factory for entrypoint {manifest.entrypoint!r}"
    )
