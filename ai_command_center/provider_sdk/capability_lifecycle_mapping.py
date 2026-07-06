"""Map provider manifests and bus payloads into CapabilityRecord instances."""

from __future__ import annotations

import time

from ai_command_center.domain.capability_lifecycle import (
    CapabilityLifecycleState,
    CapabilityRecord,
    max_lifecycle_state,
)
from ai_command_center.domain.orchestration_provider_manifest import OrchestrationProviderManifest
from ai_command_center.domain.runtime_provider_manifest import RuntimeProviderManifest


def runtime_capability_id(provider_id: str, capability_kind: str) -> str:
    return f"runtime:{provider_id}:{capability_kind}"


def orchestration_capability_id(provider_id: str, intent: str = "") -> str:
    if intent:
        return f"orchestration:{provider_id}:{intent}"
    return f"orchestration:{provider_id}"


def _is_certified(certification_level: str) -> bool:
    return bool(certification_level.strip())


def _is_observable(events: tuple[str, ...], health_probe: str) -> bool:
    if health_probe.strip():
        return True
    observability_markers = {
        "orchestration.receipt",
        "orchestration.run.snapshot",
        "capability.complete",
        "capability.dispatch",
    }
    return any(event in observability_markers for event in events)


def _health_status_from_runtime(health_state: str) -> str:
    normalized = health_state.strip().lower()
    if normalized in {"ready", "healthy"}:
        return "healthy"
    if normalized == "degraded":
        return "degraded"
    return "offline"


def _health_status_from_orchestration(healthy: bool) -> str:
    return "healthy" if healthy else "offline"


def compute_lifecycle_state(
    *,
    discovered: bool,
    loaded: bool,
    certified: bool,
    health_status: str,
    observable: bool,
    callable_: bool,
    trusted: bool,
    exposed: bool,
) -> CapabilityLifecycleState:
    """Derive the highest lifecycle stage satisfied by current signals."""
    stages: list[CapabilityLifecycleState] = []
    if discovered:
        stages.append(CapabilityLifecycleState.DISCOVERED)
    if loaded:
        stages.append(CapabilityLifecycleState.LOADED)
    if certified:
        stages.append(CapabilityLifecycleState.CERTIFIED)
    if health_status == "healthy":
        stages.append(CapabilityLifecycleState.HEALTHY)
    if observable:
        stages.append(CapabilityLifecycleState.OBSERVABLE)
    if callable_ and health_status in {"healthy", "degraded"}:
        stages.append(CapabilityLifecycleState.CALLABLE)
    if trusted:
        stages.append(CapabilityLifecycleState.TRUSTED)
    if exposed:
        stages.append(CapabilityLifecycleState.EXPOSED)
    return max_lifecycle_state(*stages)


def capability_records_from_runtime_manifest(
    manifest: RuntimeProviderManifest,
    *,
    now: float | None = None,
) -> tuple[CapabilityRecord, ...]:
    """Create discovered capability records from a runtime provider manifest."""
    timestamp = time.time() if now is None else now
    certified = _is_certified(manifest.certification_level)
    observable = _is_observable(manifest.events, manifest.health_probe)
    records: list[CapabilityRecord] = []
    for capability in manifest.capabilities:
        kind = capability.value if hasattr(capability, "value") else str(capability)
        lifecycle_state = compute_lifecycle_state(
            discovered=True,
            loaded=False,
            certified=certified,
            health_status="offline",
            observable=observable,
            callable_=manifest.enabled,
            trusted=certified,
            exposed=False,
        )
        records.append(
            CapabilityRecord(
                capability_id=runtime_capability_id(manifest.id, kind),
                provider_id=manifest.id,
                provider_ids=(manifest.id,),
                lifecycle_state=lifecycle_state,
                capability_kind=kind,
                source="runtime",
                certified=certified,
                observable=observable,
                health_status="offline",
                discovered_at=timestamp,
                updated_at=timestamp,
            )
        )
    return tuple(records)


def capability_records_from_orchestration_manifest(
    manifest: OrchestrationProviderManifest,
    *,
    now: float | None = None,
) -> tuple[CapabilityRecord, ...]:
    """Create discovered capability records from an orchestration provider manifest."""
    timestamp = time.time() if now is None else now
    certified = _is_certified(manifest.certification_level)
    observable = _is_observable(manifest.events, manifest.health_probe)
    records: list[CapabilityRecord] = []
    intents = manifest.intents or (manifest.id,)
    for intent in intents:
        lifecycle_state = compute_lifecycle_state(
            discovered=True,
            loaded=False,
            certified=certified,
            health_status="offline",
            observable=observable,
            callable_=manifest.enabled,
            trusted=certified,
            exposed=False,
        )
        records.append(
            CapabilityRecord(
                capability_id=orchestration_capability_id(manifest.id, intent),
                provider_id=manifest.id,
                provider_ids=(manifest.id,),
                lifecycle_state=lifecycle_state,
                capability_kind=intent,
                source="orchestration",
                certified=certified,
                observable=observable,
                health_status="offline",
                discovered_at=timestamp,
                updated_at=timestamp,
            )
        )
    return tuple(records)


def capability_records_from_providers_ready_payload(
    payload: dict[str, object],
    *,
    now: float | None = None,
) -> tuple[CapabilityRecord, ...]:
    """Normalize capability.providers.ready provider entries into lifecycle records."""
    timestamp = time.time() if now is None else now
    providers = payload.get("providers") or []
    records: list[CapabilityRecord] = []
    if not isinstance(providers, list):
        return ()
    for item in providers:
        if not isinstance(item, dict):
            continue
        provider_id = str(item.get("id", "")).strip()
        if not provider_id:
            continue
        health_status = _health_status_from_runtime(str(item.get("health_state", "")))
        enabled = bool(item.get("enabled", True))
        capabilities = item.get("capabilities") or []
        if not capabilities:
            capabilities = [provider_id]
        for capability in capabilities:
            kind = str(capability)
            lifecycle_state = compute_lifecycle_state(
                discovered=True,
                loaded=True,
                certified=False,
                health_status=health_status,
                observable=True,
                callable_=enabled,
                trusted=False,
                exposed=True,
            )
            records.append(
                CapabilityRecord(
                    capability_id=runtime_capability_id(provider_id, kind),
                    provider_id=provider_id,
                    provider_ids=(provider_id,),
                    lifecycle_state=lifecycle_state,
                    capability_kind=kind,
                    source="runtime",
                    certified=False,
                    observable=True,
                    health_status=health_status,
                    last_error=str(item.get("health_detail", "")),
                    discovered_at=timestamp,
                    updated_at=timestamp,
                )
            )
    return tuple(records)


def apply_orchestration_health(
    record: CapabilityRecord,
    payload: dict[str, object],
    *,
    now: float | None = None,
) -> CapabilityRecord:
    """Merge orchestration.provider.health into an existing capability record."""
    timestamp = time.time() if now is None else now
    provider_id = str(payload.get("provider_id", "")).strip()
    if provider_id and provider_id != record.provider_id:
        return record
    health_status = _health_status_from_orchestration(bool(payload.get("healthy", False)))
    detail = str(payload.get("detail", ""))
    lifecycle_state = compute_lifecycle_state(
        discovered=True,
        loaded=True,
        certified=record.certified,
        health_status=health_status,
        observable=record.observable,
        callable_=health_status in {"healthy", "degraded"},
        trusted=record.certified,
        exposed=record.lifecycle_state == CapabilityLifecycleState.EXPOSED,
    )
    return CapabilityRecord(
        capability_id=record.capability_id,
        provider_id=record.provider_id,
        provider_ids=record.provider_ids,
        lifecycle_state=lifecycle_state,
        capability_kind=record.capability_kind,
        source=record.source,
        certified=record.certified,
        observable=record.observable,
        health_status=health_status,
        last_error=detail if health_status != "healthy" else "",
        discovered_at=record.discovered_at or timestamp,
        updated_at=timestamp,
    )


def capability_record_from_orchestration_health(
    payload: dict[str, object],
    *,
    now: float | None = None,
) -> CapabilityRecord:
    """Create or refresh an orchestration capability record from a health event."""
    timestamp = time.time() if now is None else now
    provider_id = str(payload.get("provider_id", "")).strip()
    health_status = _health_status_from_orchestration(bool(payload.get("healthy", False)))
    detail = str(payload.get("detail", ""))
    lifecycle_state = compute_lifecycle_state(
        discovered=True,
        loaded=True,
        certified=False,
        health_status=health_status,
        observable=True,
        callable_=health_status in {"healthy", "degraded"},
        trusted=False,
        exposed=True,
    )
    return CapabilityRecord(
        capability_id=orchestration_capability_id(provider_id),
        provider_id=provider_id,
        provider_ids=(provider_id,),
        lifecycle_state=lifecycle_state,
        capability_kind=provider_id,
        source="orchestration",
        certified=False,
        observable=True,
        health_status=health_status,
        last_error=detail if health_status != "healthy" else "",
        discovered_at=timestamp,
        updated_at=timestamp,
    )
