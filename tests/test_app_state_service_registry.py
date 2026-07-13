"""Blueprint Phase 9 — verify ServiceRegistrySnapshot AppState projection.

Covers:
  - The four previously dropped service lifecycle topics are now consumed.
  - Per-service state history and milestone counters are recorded.
  - Cross-service health trend is populated.
  - Existing flat services tuple is preserved for backward compatibility.
"""

from __future__ import annotations

import unittest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    SERVICE_ERROR,
    SERVICE_READY,
    SERVICE_STARTED,
    SERVICE_STATE_CHANGED,
    SERVICE_STOPPED,
)
from ai_command_center.domain.service_registry_snapshot import (
    _MAX_HEALTH_TREND,
    _MAX_SERVICE_HISTORY,
)


class AppStateServiceRegistryTest(unittest.TestCase):

    def setUp(self) -> None:
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self) -> None:
        self.store.close()

    def _publish(self, topic: str, payload: dict) -> None:
        self.bus.publish(topic, payload, source="test")

    def test_service_state_changed_projects_services_and_registry(self) -> None:
        self._publish(
            SERVICE_STATE_CHANGED,
            {"name": "ollama", "state": "ready", "detail": "ready"},
        )
        snap = self.store.snapshot
        self.assertEqual(len(snap.services), 1)
        self.assertEqual(snap.services[0].name, "ollama")
        self.assertEqual(snap.services[0].state, "ready")
        self.assertEqual(snap.service_registry.total_services, 1)
        entry = snap.service_registry.entries[0]
        self.assertEqual(entry.name, "ollama")
        self.assertEqual(entry.state, "ready")
        self.assertEqual(len(entry.history), 1)
        self.assertEqual(entry.history[0].state, "ready")

    def test_lifecycle_topics_are_consumed(self) -> None:
        self._publish(SERVICE_STARTED, {"service": "notes"})
        self._publish(SERVICE_READY, {"service": "notes"})
        self._publish(SERVICE_STOPPED, {"service": "notes"})
        self._publish(SERVICE_ERROR, {"service": "chat", "detail": "boom"})
        snap = self.store.snapshot
        self.assertEqual(snap.service_registry.total_services, 2)
        notes = next(e for e in snap.service_registry.entries if e.name == "notes")
        chat = next(e for e in snap.service_registry.entries if e.name == "chat")
        self.assertEqual(notes.state, "stopped")
        self.assertEqual(notes.started_count, 1)
        self.assertEqual(notes.ready_count, 1)
        self.assertEqual(notes.stopped_count, 1)
        self.assertEqual(chat.state, "error")
        self.assertEqual(chat.error_count, 1)
        self.assertEqual(chat.detail, "boom")
        self.assertEqual(snap.service_registry.started_count, 1)
        self.assertEqual(snap.service_registry.ready_count, 1)
        self.assertEqual(snap.service_registry.stopped_count, 1)
        self.assertEqual(snap.service_registry.error_count, 1)

    def test_service_registry_tracks_per_service_history(self) -> None:
        for state in ("starting", "ready", "degraded", "error"):
            self._publish(
                SERVICE_STATE_CHANGED,
                {"name": "svc", "state": state, "detail": state},
            )
        entry = self.store.snapshot.service_registry.entries[0]
        self.assertEqual(len(entry.history), 4)
        self.assertEqual(entry.history[0].state, "error")
        self.assertEqual(entry.history[-1].state, "starting")

    def test_service_registry_health_trend(self) -> None:
        self._publish(SERVICE_STATE_CHANGED, {"name": "a", "state": "ready"})
        self._publish(SERVICE_STATE_CHANGED, {"name": "b", "state": "error"})
        trend = self.store.snapshot.service_registry.health_trend
        self.assertEqual(len(trend), 2)
        self.assertEqual(trend[0][0], "b")
        self.assertEqual(trend[0][1], "error")
        self.assertEqual(trend[1][0], "a")
        self.assertEqual(trend[1][1], "ready")

    def test_service_history_capped(self) -> None:
        for i in range(_MAX_SERVICE_HISTORY + 5):
            self._publish(
                SERVICE_STATE_CHANGED,
                {"name": "svc", "state": f"state-{i}", "detail": ""},
            )
        entry = self.store.snapshot.service_registry.entries[0]
        self.assertEqual(len(entry.history), _MAX_SERVICE_HISTORY)
        # Most recent transition is the last one published.
        self.assertEqual(entry.history[0].state, f"state-{_MAX_SERVICE_HISTORY + 4}")

    def test_health_trend_capped(self) -> None:
        for i in range(_MAX_HEALTH_TREND + 5):
            self._publish(
                SERVICE_STATE_CHANGED,
                {"name": "svc", "state": f"state-{i}", "detail": ""},
            )
        trend = self.store.snapshot.service_registry.health_trend
        self.assertEqual(len(trend), _MAX_HEALTH_TREND)

    def test_existing_services_field_preserved(self) -> None:
        self._publish(SERVICE_READY, {"service": "notes"})
        snap = self.store.snapshot
        self.assertEqual(len(snap.services), 1)
        self.assertEqual(snap.services[0].name, "notes")
        self.assertEqual(snap.services[0].state, "ready")

    def test_service_registry_payload_roundtrip(self) -> None:
        self._publish(SERVICE_STATE_CHANGED, {"name": "x", "state": "ready"})
        self._publish(SERVICE_ERROR, {"service": "y", "detail": "fail"})
        payload = self.store.snapshot.service_registry.to_payload()
        self.assertEqual(payload["started_count"], 0)
        self.assertEqual(payload["ready_count"], 0)
        self.assertEqual(payload["stopped_count"], 0)
        self.assertEqual(payload["error_count"], 1)
        self.assertEqual(len(payload["entries"]), 2)
        self.assertEqual(len(payload["health_trend"]), 2)


if __name__ == "__main__":
    unittest.main()
