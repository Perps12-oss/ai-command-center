"""UI_NAVIGATE must not block the publisher on Telemetry SQLite I/O."""

from __future__ import annotations

import sqlite3
import threading
import time

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import UI_NAVIGATE
from ai_command_center.repositories.database_bootstrap_repository import (
    DatabaseBootstrapRepository,
)
from ai_command_center.repositories.telemetry_repository import TelemetryRepository
from ai_command_center.services.telemetry_service import TelemetryService


class _SlowRepo(TelemetryRepository):
    def __init__(self, conn: sqlite3.Connection, gate: threading.Event) -> None:
        super().__init__(conn)
        self._gate = gate
        self.inserts = 0

    def insert(self, event: str, payload, *, timestamp: str | None = None) -> None:  # type: ignore[override]
        # Block until the test releases — sync path would freeze the publisher.
        self._gate.wait(timeout=2.0)
        self.inserts += 1
        return super().insert(event, payload, timestamp=timestamp)


def test_ui_navigate_handler_returns_before_sqlite() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    DatabaseBootstrapRepository().apply(conn)
    gate = threading.Event()
    bus = EventBus()
    service = TelemetryService(bus, _SlowRepo(conn, gate))
    service.start()
    try:
        started = time.perf_counter()
        bus.publish(UI_NAVIGATE, {"view": "memory"}, source="ui")
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        assert elapsed_ms < 50.0, f"publisher blocked {elapsed_ms:.1f}ms on telemetry"
        gate.set()
        deadline = time.time() + 2.0
        while service._repo.inserts == 0 and time.time() < deadline:  # type: ignore[attr-defined]
            time.sleep(0.01)
        assert service._repo.inserts >= 1  # type: ignore[attr-defined]
    finally:
        gate.set()
        service.stop()
