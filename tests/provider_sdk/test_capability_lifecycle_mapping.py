"""Capability lifecycle domain and mapping tests."""

from __future__ import annotations

from ai_command_center.domain.capability_lifecycle import (
    CapabilityLifecycleState,
    CapabilityRecord,
    max_lifecycle_state,
)
from ai_command_center.domain.orchestration_provider_manifest import OrchestrationProviderManifest
from ai_command_center.domain.runtime_capability import CapabilityKind
from ai_command_center.domain.runtime_provider_manifest import RuntimeProviderManifest
from ai_command_center.provider_sdk.capability_lifecycle_mapping import (
    apply_orchestration_health,
    capability_record_from_orchestration_health,
    capability_records_from_orchestration_manifest,
    capability_records_from_providers_ready_payload,
    capability_records_from_runtime_manifest,
    compute_lifecycle_state,
    orchestration_capability_id,
    runtime_capability_id,
)


def test_runtime_capability_id_format() -> None:
    assert runtime_capability_id("native", "chat") == "runtime:native:chat"


def test_orchestration_capability_id_format() -> None:
    assert orchestration_capability_id("system_facts", "time_query") == (
        "orchestration:system_facts:time_query"
    )


def test_compute_lifecycle_state_progression() -> None:
    state = compute_lifecycle_state(
        discovered=True,
        loaded=True,
        certified=True,
        health_status="healthy",
        observable=True,
        callable_=True,
        trusted=True,
        exposed=True,
    )
    assert state == CapabilityLifecycleState.EXPOSED


def test_max_lifecycle_state_prefers_highest() -> None:
    assert max_lifecycle_state(
        CapabilityLifecycleState.LOADED,
        CapabilityLifecycleState.HEALTHY,
    ) == CapabilityLifecycleState.HEALTHY


def test_capability_record_round_trip() -> None:
    record = CapabilityRecord(
        capability_id="runtime:native:chat",
        provider_id="native",
        lifecycle_state=CapabilityLifecycleState.LOADED,
        capability_kind="chat",
        source="runtime",
        health_status="healthy",
    )
    restored = CapabilityRecord.from_dict(record.to_dict())
    assert restored == record


def test_capability_records_from_runtime_manifest() -> None:
    manifest = RuntimeProviderManifest(
        id="stub_echo",
        name="Stub Echo",
        version="1.0",
        description="",
        entrypoint="builtin:stub_echo",
        capabilities=(CapabilityKind.CHAT, CapabilityKind.CODING),
        certification_level="silver",
        events=("orchestration.receipt",),
        health_probe="provider.health",
    )
    records = capability_records_from_runtime_manifest(manifest, now=100.0)
    assert len(records) == 2
    assert records[0].capability_id == "runtime:stub_echo:chat"
    assert records[0].certified is True
    assert records[0].observable is True
    assert records[0].discovered_at == 100.0


def test_capability_records_from_orchestration_manifest() -> None:
    manifest = OrchestrationProviderManifest(
        id="system_facts",
        name="System Facts",
        version="1.0",
        description="",
        intents=("time_query",),
        certification_level="gold",
        events=("orchestration.receipt",),
        health_probe="provider.health",
    )
    records = capability_records_from_orchestration_manifest(manifest, now=42.0)
    assert len(records) == 1
    assert records[0].capability_id == orchestration_capability_id("system_facts", "time_query")
    assert records[0].source == "orchestration"


def test_capability_records_from_providers_ready_payload() -> None:
    records = capability_records_from_providers_ready_payload(
        {
            "providers": [
                {
                    "id": "native",
                    "capabilities": ["chat"],
                    "health_state": "ready",
                    "enabled": True,
                    "health_detail": "",
                }
            ]
        },
        now=10.0,
    )
    assert len(records) == 1
    assert records[0].lifecycle_state == CapabilityLifecycleState.EXPOSED
    assert records[0].health_status == "healthy"


def test_apply_orchestration_health_updates_record() -> None:
    record = CapabilityRecord(
        capability_id=orchestration_capability_id("system_facts"),
        provider_id="system_facts",
        lifecycle_state=CapabilityLifecycleState.LOADED,
        source="orchestration",
        health_status="offline",
    )
    updated = apply_orchestration_health(
        record,
        {"provider_id": "system_facts", "healthy": True, "detail": ""},
        now=99.0,
    )
    assert updated.health_status == "healthy"
    assert updated.updated_at == 99.0


def test_capability_record_from_orchestration_health() -> None:
    record = capability_record_from_orchestration_health(
        {"provider_id": "calendar", "healthy": False, "detail": "offline"},
        now=5.0,
    )
    assert record.provider_id == "calendar"
    assert record.health_status == "offline"
    assert record.last_error == "offline"
