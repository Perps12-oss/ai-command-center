"""
Timeline Service - Phase 1 Implementation

Timeline event management for audit, undo, analytics, and debugging.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from ai_command_center.core.timeline.timeline_event import (
    TimelineEvent,
    TIMELINE_EVENT_SCHEMA_VERSION,
)
from ai_command_center.core.timeline.timeline_repository import TimelineRepository
from ai_command_center.core.event_bus import (
    Event,
    EVENT_TIMELINE_EVENT,
)


class TimelineService:
    """
    Timeline event management.
    
    Responsibilities:
    - Record events to timeline
    - Query timeline for audit/debugging
    - Undo support via reversible events
    - Event publishing for timeline operations
    - Subscribe to external timeline record requests via EventBus
    """

    def __init__(self, repository: TimelineRepository, event_bus: Any) -> None:
        self._repository = repository
        self._event_bus = event_bus
        self._unsubscribe: Callable[[], None] | None = None

    def start(self) -> None:
        """Subscribe to external timeline events."""
        if self._unsubscribe is None:
            self._unsubscribe = self._event_bus.subscribe(
                EVENT_TIMELINE_EVENT, self._on_timeline_event
            )

    def stop(self) -> None:
        """Unsubscribe from external timeline events."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def _on_timeline_event(self, event: Event) -> None:
        """Persist an externally published timeline event."""
        # Ignore our own publication loop.
        if event.source == "timeline_service":
            return
        payload = event.payload
        entity_id = None
        raw_entity_id = payload.get("entity_id")
        if raw_entity_id:
            try:
                entity_id = UUID(raw_entity_id)
            except ValueError:
                pass
        self.record(
            event_type=payload.get("event_type", "timeline.event"),
            entity_id=entity_id,
            entity_type=payload.get("entity_type"),
            payload=payload.get("payload") or {},
        )

    def record(
        self,
        event_type: str,
        entity_id: UUID | None = None,
        entity_type: str | None = None,
        payload: dict[str, Any] | None = None,
        user_id: str | None = None,
        reversible: bool = False,
        undo_data: dict[str, Any] | None = None,
    ) -> TimelineEvent:
        """Record a timeline event."""
        timeline_event = TimelineEvent(
            id=uuid4(),
            event_type=event_type,
            entity_id=entity_id,
            entity_type=entity_type,
            payload=payload or {},
            timestamp=datetime.utcnow(),
            user_id=user_id,
            reversible=reversible,
            undo_data=undo_data,
            schema_version=TIMELINE_EVENT_SCHEMA_VERSION,
        )
        
        self._repository.create(timeline_event)
        
        # Publish event
        self._event_bus.publish(
            EVENT_TIMELINE_EVENT,
            {
                "timeline_event_id": str(timeline_event.id),
                "event_type": timeline_event.event_type,
                "entity_id": str(timeline_event.entity_id) if timeline_event.entity_id else None,
                "reversible": timeline_event.reversible,
            },
            source="timeline_service",
        )
        
        return timeline_event

    def get(self, event_id: UUID) -> TimelineEvent | None:
        """Get timeline event by ID."""
        return self._repository.get(event_id)

    def get_by_entity(self, entity_id: UUID, limit: int = 100) -> list[TimelineEvent]:
        """Get timeline events for a specific entity."""
        return self._repository.get_by_entity(entity_id, limit)

    def get_by_type(self, event_type: str, limit: int = 100) -> list[TimelineEvent]:
        """Get timeline events by event type."""
        return self._repository.get_by_type(event_type, limit)

    def get_recent(self, limit: int = 50) -> list[TimelineEvent]:
        """Get recent timeline events."""
        return self._repository.get_recent(limit)

    def get_reversible(self, limit: int = 50) -> list[TimelineEvent]:
        """Get reversible timeline events (for undo)."""
        return self._repository.get_reversible(limit)

    def undo(self, event_id: UUID) -> bool:
        """
        Undo a reversible timeline event.
        
        This is a placeholder - actual undo logic depends on the event type
        and would be implemented by the relevant service.
        """
        event = self._repository.get(event_id)
        if event is None:
            return False
        
        if not event.reversible:
            return False
        
        # Placeholder: undo logic would be implemented by event handlers
        # For now, we just delete the event from timeline
        self._repository.delete(event_id)
        return True

    def delete_old_events(self, days: int = 30) -> int:
        """Delete timeline events older than specified days."""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return self._repository.delete_old_events(cutoff_date)

    def list_all(self) -> list[TimelineEvent]:
        """List all timeline events."""
        return self._repository.list_all()
