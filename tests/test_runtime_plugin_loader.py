"""Tests for ARI Phase 5 runtime plugin manifests and dynamic provider registry."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import CAPABILITY_PROVIDERS_READY
from ai_command_center.domain.runtime_capability import (
    CapabilityKind,
    RuntimeInvocationRequest,
)
from ai_command_center.domain.runtime_provider_manifest import RuntimeProviderManifest
from ai_command_center.repositories.runtime_provider_manifest_repository import (
    RuntimeProviderManifestRepository,
)
from ai_command_center.runtime.provider_registry import (
    RuntimeProviderRegistry,
    build_runtime_registry_from_manifests,
)
from ai_command_center.runtime.runtime_plugin_loader import (
    ManifestValidationError,
    instantiate_provider,
    load_manifests,
    validate_manifest,
)
from ai_command_center.services.runtime_provider_registry_service import (
    RuntimeProviderRegistryService,
)


def _valid_manifest(**overrides: object) -> RuntimeProviderManifest:
    base = {
        "id": "stub_echo",
        "name": "Stub Echo",
        "version": "1.0",
        "description": "test",
        "entrypoint": "builtin:stub_echo",
        "capabilities": (CapabilityKind.CHAT,),
        "enabled": True,
    }
    base.update(overrides)
    return RuntimeProviderManifest(**base)


def test_validate_manifest_rejects_unknown_entrypoint() -> None:
    manifest = _valid_manifest(entrypoint="import:evil.module")
    with pytest.raises(ManifestValidationError, match="allowlisted"):
        validate_manifest(manifest)


def test_validate_manifest_requires_capabilities() -> None:
    manifest = _valid_manifest(capabilities=())
    with pytest.raises(ManifestValidationError, match="capability"):
        validate_manifest(manifest)


def test_repository_rejects_manifest_without_capabilities(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        "id: bad\nentrypoint: builtin:stub_echo\ncapabilities: []\n",
        encoding="utf-8",
    )
    repo = RuntimeProviderManifestRepository()
    assert repo.list_manifests(tmp_path) == []


def test_load_manifests_applies_enabled_flag(tmp_path: Path) -> None:
    enabled = tmp_path / "enabled.yaml"
    enabled.write_text(
        "\n".join(
            [
                "id: stub_echo",
                "entrypoint: builtin:stub_echo",
                "capabilities: [chat]",
                "enabled: true",
            ]
        ),
        encoding="utf-8",
    )
    disabled = tmp_path / "disabled.yaml"
    disabled.write_text(
        "\n".join(
            [
                "id: other",
                "entrypoint: builtin:stub_echo",
                "capabilities: [chat]",
                "enabled: false",
            ]
        ),
        encoding="utf-8",
    )
    manifests = load_manifests(tmp_path)
    by_id = {m.id: m for m in manifests}
    assert by_id["stub_echo"].enabled is True
    assert by_id["other"].enabled is False


def test_build_registry_registers_native_and_enabled_providers(tmp_path: Path) -> None:
    (tmp_path / "native.yaml").write_text(
        "\n".join(
            [
                "id: native",
                "entrypoint: builtin:native",
                "capabilities: [chat]",
                "kind: core",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "stub_echo.yaml").write_text(
        "\n".join(
            [
                "id: stub_echo",
                "entrypoint: builtin:stub_echo",
                "capabilities: [chat]",
                "enabled: true",
            ]
        ),
        encoding="utf-8",
    )
    bus = EventBus()
    registry = build_runtime_registry_from_manifests(bus, tmp_path)
    assert registry.list_ids() == ["native", "stub_echo"]
    stub = registry.get("stub_echo")
    assert stub is not None
    assert stub.supports(CapabilityKind.CHAT)


def test_stub_provider_instantiation_and_invoke() -> None:
    bus = EventBus()
    completed: list[dict] = []
    bus.subscribe("capability.complete", lambda e: completed.append(dict(e.payload)))
    provider = instantiate_provider(_valid_manifest(), bus=bus)
    assert provider.provider_id == "stub_echo"
    provider.invoke(
        RuntimeInvocationRequest(
            request_id="r1",
            kind=CapabilityKind.CHAT,
            provider_id="stub_echo",
            query="hello",
        )
    )
    assert len(completed) == 1
    assert completed[0]["text"] == "echo:hello"


def test_runtime_provider_registry_service_publishes_ready_event() -> None:
    bus = EventBus()
    registry = RuntimeProviderRegistry()
    ready: list[dict] = []
    bus.subscribe(CAPABILITY_PROVIDERS_READY, lambda e: ready.append(dict(e.payload)))

    with tempfile.TemporaryDirectory() as tmp:
        manifests_dir = Path(tmp)
        (manifests_dir / "qwenpaw.yaml").write_text(
            "\n".join(
                [
                    "id: qwenpaw",
                    "entrypoint: builtin:qwenpaw",
                    "capabilities: [planning]",
                    "enabled: true",
                ]
            ),
            encoding="utf-8",
        )
        service = RuntimeProviderRegistryService(
            bus,
            registry=registry,
            manifests_dir=manifests_dir,
        )
        service.start()
        try:
            assert "native" in registry.list_ids()
            assert "qwenpaw" in registry.list_ids()
            assert len(ready) == 1
            provider_ids = [p["id"] for p in ready[0]["providers"]]
            assert "native" in provider_ids
            assert "qwenpaw" in provider_ids
            for provider in ready[0]["providers"]:
                assert "health_state" in provider
        finally:
            service.stop()


def test_invalid_entrypoint_not_instantiated(tmp_path: Path) -> None:
    (tmp_path / "evil.yaml").write_text(
        "id: evil\nentrypoint: evil:module\ncapabilities: [chat]\n",
        encoding="utf-8",
    )
    manifests = load_manifests(tmp_path)
    assert manifests == []
