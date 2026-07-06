"""Manifest validator tests."""

from __future__ import annotations

from ai_command_center.domain.orchestration_provider_manifest import OrchestrationProviderManifest
from ai_command_center.domain.runtime_capability import CapabilityKind
from ai_command_center.domain.runtime_provider_manifest import RuntimeProviderManifest
from ai_command_center.provider_sdk.registry import (
    ProviderManifestRegistry,
    validate_orchestration_manifest,
    validate_runtime_manifest,
)


def _runtime(**overrides) -> RuntimeProviderManifest:
    base = dict(
        id="test",
        name="Test",
        version="1.0",
        description="",
        entrypoint="builtin:stub_echo",
        capabilities=(CapabilityKind.CHAT,),
        permissions=("network.outbound",),
        events=("orchestration.receipt", "orchestration.run.snapshot"),
        health_probe="provider.health",
        certification_level="silver",
    )
    base.update(overrides)
    return RuntimeProviderManifest(**base)


def test_validate_runtime_manifest_ok() -> None:
    result = validate_runtime_manifest(_runtime())
    assert result.ok
    assert not result.errors


def test_validate_runtime_missing_capabilities_fails() -> None:
    result = validate_runtime_manifest(_runtime(capabilities=()))
    assert not result.ok
    assert any("capability" in e for e in result.errors)


def test_validate_orchestration_manifest_ok() -> None:
    manifest = OrchestrationProviderManifest(
        id="calendar",
        name="Calendar",
        version="1.0",
        description="",
        intents=("calendar_query",),
        permissions=("calendar.read",),
        events=("orchestration.receipt",),
        health_probe="provider.health",
        certification_level="gold",
    )
    result = validate_orchestration_manifest(manifest)
    assert result.ok


def test_registry_warns_in_dev_mode(monkeypatch) -> None:
    monkeypatch.setenv("ACC_DEV_MODE", "1")
    registry = ProviderManifestRegistry()
    result = registry.register_runtime(_runtime(permissions=()))
    assert result.ok
    assert any("permissions" in w for w in result.warnings)
