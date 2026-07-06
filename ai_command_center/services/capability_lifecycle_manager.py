"""Capability lifecycle manager — in-memory control-plane projection."""

from __future__ import annotations

import time
from collections.abc import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CAPABILITY_DISPATCH,
    CAPABILITY_LIFECYCLE_SNAPSHOT,
    CAPABILITY_PROVIDERS_READY,
    ORCHESTRATION_INTENT_CLASSIFIED,
    ORCHESTRATION_PROVIDER_HEALTH,
    ORCHESTRATION_RECEIPT,
)
from ai_command_center.domain.capability_lifecycle import CapabilityRecord
from ai_command_center.provider_sdk.capability_lifecycle_mapping import (
    apply_orchestration_health,
    capability_record_from_orchestration_health,
    capability_records_from_providers_ready_payload,
)
from ai_command_center.services.base import BaseService


class CapabilityLifecycleManager(BaseService):
    """Maintains capability lifecycle records and publishes snapshot projections."""

    name = "capability_lifecycle"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._records: dict[str, CapabilityRecord] = {}
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        topics = (
            CAPABILITY_PROVIDERS_READY,
            ORCHESTRATION_PROVIDER_HEALTH,
            ORCHESTRATION_INTENT_CLASSIFIED,
            ORCHESTRATION_RECEIPT,
            CAPABILITY_DISPATCH,
        )
        for topic in topics:
            self._unsubscribers.append(self._bus.subscribe(topic, self._on_event))
        self._publish_snapshot()

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def records(self) -> tuple[CapabilityRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda item: item.capability_id))

    def _on_event(self, event: Event) -> None:
        if event.topic == CAPABILITY_PROVIDERS_READY:
            self._on_providers_ready(event.payload)
        elif event.topic == ORCHESTRATION_PROVIDER_HEALTH:
            self._on_provider_health(event.payload)
        elif event.topic == ORCHESTRATION_INTENT_CLASSIFIED:
            self._on_intent_classified(event.payload)
        elif event.topic == ORCHESTRATION_RECEIPT:
            self._on_receipt(event.payload)
        elif event.topic == CAPABILITY_DISPATCH:
            self._on_dispatch(event.payload)

    def _on_providers_ready(self, payload: dict[str, object]) -> None:
        for record in capability_records_from_providers_ready_payload(payload):
            self._records[record.capability_id] = record
        self._publish_snapshot()

    def _on_provider_health(self, payload: dict[str, object]) -> None:
        provider_id = str(payload.get("provider_id", "")).strip()
        if not provider_id:
            return
        updated = False
        matched = False
        for capability_id, record in list(self._records.items()):
            if record.provider_id != provider_id:
                continue
            matched = True
            self._records[capability_id] = apply_orchestration_health(record, payload)
            updated = True
        if not matched:
            record = capability_record_from_orchestration_health(payload)
            self._records[record.capability_id] = record
            updated = True
        if updated:
            self._publish_snapshot()

    def _on_intent_classified(self, payload: dict[str, object]) -> None:
        provider_id = str(payload.get("provider_id", "")).strip()
        if not provider_id:
            return
        self._mark_callable(provider_id)

    def _on_receipt(self, payload: dict[str, object]) -> None:
        provider_id = str(payload.get("provider_id", "")).strip()
        if not provider_id:
            return
        self._mark_trusted(provider_id)

    def _on_dispatch(self, payload: dict[str, object]) -> None:
        provider_id = str(payload.get("provider_id", "")).strip()
        if not provider_id:
            return
        self._mark_callable(provider_id)

    def _mark_callable(self, provider_id: str) -> None:
        now = time.time()
        updated = False
        for capability_id, record in list(self._records.items()):
            if record.provider_id != provider_id:
                continue
            from ai_command_center.domain.capability_lifecycle import CapabilityLifecycleState
            from ai_command_center.provider_sdk.capability_lifecycle_mapping import compute_lifecycle_state

            lifecycle_state = compute_lifecycle_state(
                discovered=True,
                loaded=True,
                certified=record.certified,
                health_status=record.health_status,
                observable=record.observable,
                callable_=True,
                trusted=record.certified,
                exposed=record.lifecycle_state == CapabilityLifecycleState.EXPOSED,
            )
            self._records[capability_id] = CapabilityRecord(
                capability_id=record.capability_id,
                provider_id=record.provider_id,
                provider_ids=record.provider_ids,
                lifecycle_state=lifecycle_state,
                capability_kind=record.capability_kind,
                source=record.source,
                certified=record.certified,
                observable=record.observable,
                health_status=record.health_status,
                last_error=record.last_error,
                discovered_at=record.discovered_at,
                updated_at=now,
            )
            updated = True
        if updated:
            self._publish_snapshot()

    def _mark_trusted(self, provider_id: str) -> None:
        now = time.time()
        updated = False
        for capability_id, record in list(self._records.items()):
            if record.provider_id != provider_id:
                continue
            from ai_command_center.domain.capability_lifecycle import CapabilityLifecycleState
            from ai_command_center.provider_sdk.capability_lifecycle_mapping import compute_lifecycle_state

            lifecycle_state = compute_lifecycle_state(
                discovered=True,
                loaded=True,
                certified=True,
                health_status=record.health_status,
                observable=record.observable,
                callable_=True,
                trusted=True,
                exposed=record.lifecycle_state == CapabilityLifecycleState.EXPOSED,
            )
            self._records[capability_id] = CapabilityRecord(
                capability_id=record.capability_id,
                provider_id=record.provider_id,
                provider_ids=record.provider_ids,
                lifecycle_state=lifecycle_state,
                capability_kind=record.capability_kind,
                source=record.source,
                certified=True,
                observable=record.observable,
                health_status=record.health_status,
                last_error=record.last_error,
                discovered_at=record.discovered_at,
                updated_at=now,
            )
            updated = True
        if updated:
            self._publish_snapshot()

    def _publish_snapshot(self) -> None:
        records = [record.to_dict() for record in self.records()]
        self._bus.publish(
            CAPABILITY_LIFECYCLE_SNAPSHOT,
            {"capability_lifecycle": records},
            source=self.name,
        )
