"""Shared fixtures for telemetry tests."""

from __future__ import annotations

import pytest

from ai_command_center.core.event_bus import EventBus

pytest.importorskip("opentelemetry.sdk.trace.export.in_memory_span_exporter")

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


@pytest.fixture(autouse=True)
def _reset_otel_state() -> None:
    from ai_command_center.telemetry.tracing_service import _reset_tracer_provider

    _reset_tracer_provider()
    yield
    _reset_tracer_provider()


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
def span_exporter() -> InMemorySpanExporter:
    return InMemorySpanExporter()
