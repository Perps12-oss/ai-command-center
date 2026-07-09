"""Settings ↔ tracing configuration tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import ORCHESTRATION_INTENT_CLASSIFIED
from ai_command_center.db.connection import connect, init_database
from ai_command_center.repositories.settings_repository import SettingsRepository
from ai_command_center.services.settings_service import SettingsService
from ai_command_center.telemetry.tracing_service import TracingService, _otlp_endpoint_reachable
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def test_settings_snapshot_round_trips_otel_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "settings.db"
        db = connect(db_path)
        init_database(db)
        try:
            bus = EventBus()
            service = SettingsService(bus, SettingsRepository(db))
            service.load()
            service.set("otel_enabled", "true")
            service.set("otel_endpoint", "http://collector:4318")
            snap = service.get_snapshot()
            assert snap.otel_enabled is True
            assert snap.otel_endpoint == "http://collector:4318"
        finally:
            db.close()


def test_tracing_disabled_via_settings(span_exporter: InMemorySpanExporter) -> None:
    bus = EventBus()
    tracing = TracingService(bus, enabled=False, span_exporter=span_exporter)
    tracing.start()
    bus.publish(
        ORCHESTRATION_INTENT_CLASSIFIED,
        {"request_id": "req-disabled", "intent": "chat", "query": "hello"},
        source="test",
    )
    tracing.stop()
    assert len(span_exporter.get_finished_spans()) == 0


def test_unreachable_otlp_endpoint_disables_tracing() -> None:
    assert _otlp_endpoint_reachable("http://127.0.0.1:1") is False
    bus = EventBus()
    tracing = TracingService(
        bus,
        enabled=True,
        otel_endpoint="http://127.0.0.1:1",
    )
    assert tracing._enabled is False
    tracing.start()
    bus.publish(
        ORCHESTRATION_INTENT_CLASSIFIED,
        {"request_id": "req-no-collector", "intent": "chat", "query": "hello"},
        source="test",
    )
    tracing.stop()
