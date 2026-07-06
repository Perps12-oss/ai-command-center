"""CapabilityLifecycleManager integration tests."""

from __future__ import annotations

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CAPABILITY_LIFECYCLE_SNAPSHOT,
    CAPABILITY_PROVIDERS_READY,
    ORCHESTRATION_PROVIDER_HEALTH,
)
from ai_command_center.domain.capability_lifecycle import CapabilityLifecycleState
from ai_command_center.services.capability_lifecycle_manager import CapabilityLifecycleManager


def test_providers_ready_and_health_publish_lifecycle_snapshot(bus: EventBus) -> None:
    manager = CapabilityLifecycleManager(bus)
    snapshots: list[dict[str, object]] = []
    bus.subscribe(
        CAPABILITY_LIFECYCLE_SNAPSHOT,
        lambda event: snapshots.append(dict(event.payload)),
    )

    manager.start()
    bus.publish(
        CAPABILITY_PROVIDERS_READY,
        {
            "providers": [
                {
                    "id": "native",
                    "name": "Native",
                    "capabilities": ["chat"],
                    "health_state": "ready",
                    "enabled": True,
                    "health_detail": "",
                }
            ]
        },
        source="test",
    )
    bus.publish(
        ORCHESTRATION_PROVIDER_HEALTH,
        {
            "provider_id": "system_facts",
            "healthy": True,
            "detail": "ok",
            "display_name": "System Facts",
        },
        source="test",
    )
    manager.stop()

    assert snapshots
    final = snapshots[-1]
    records = final.get("capability_lifecycle") or []
    assert isinstance(records, list)
    assert len(records) >= 2
    native = next(item for item in records if item["provider_id"] == "native")
    assert native["health_status"] == "healthy"
    assert native["lifecycle_state"] == CapabilityLifecycleState.EXPOSED.value
    orchestration = next(item for item in records if item["provider_id"] == "system_facts")
    assert orchestration["source"] == "orchestration"
    assert orchestration["health_status"] == "healthy"


def test_app_state_projects_capability_lifecycle_snapshot(bus: EventBus) -> None:
    manager = CapabilityLifecycleManager(bus)
    store = AppStateStore(bus)

    manager.start()
    bus.publish(
        CAPABILITY_PROVIDERS_READY,
        {
            "providers": [
                {
                    "id": "native",
                    "capabilities": ["chat"],
                    "health_state": "ready",
                    "enabled": True,
                }
            ]
        },
        source="test",
    )
    bus.publish(
        ORCHESTRATION_PROVIDER_HEALTH,
        {"provider_id": "system_facts", "healthy": True, "detail": ""},
        source="test",
    )
    manager.stop()
    store.close()

    state = store.snapshot
    assert state.capability_lifecycle
    provider_ids = {record.provider_id for record in state.capability_lifecycle}
    assert "native" in provider_ids
    assert "system_facts" in provider_ids
