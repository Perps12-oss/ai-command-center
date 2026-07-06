"""TracingService — passive OTel spans from orchestration bus events."""

from __future__ import annotations

import pytest

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    ORCHESTRATION_INTENT_CLASSIFIED,
    ORCHESTRATION_PROVIDER_SELECTED,
    ORCHESTRATION_ROUTING_COMPLETED,
)
from ai_command_center.services.orchestration_service import OrchestrationService
from ai_command_center.telemetry.tracing_service import TracingService
from tests.orchestration.conftest import build_registry, publish_chat

pytest.importorskip("opentelemetry.sdk.trace.export.in_memory_span_exporter")

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


@pytest.fixture
def span_exporter() -> InMemorySpanExporter:
    return InMemorySpanExporter()


def _span_names(exporter: InMemorySpanExporter) -> list[str]:
    return [span.name for span in exporter.get_finished_spans()]


def test_orchestration_emits_routing_and_provider_selection_spans(
    bus: EventBus,
    span_exporter: InMemorySpanExporter,
) -> None:
    tracing = TracingService(bus, enabled=True, span_exporter=span_exporter)
    orchestration = OrchestrationService(bus, provider_registry=build_registry())
    tracing.start()
    orchestration.start()

    publish_chat(bus, "What time is it?", request_id="req-trace-orch")

    orchestration.stop()
    tracing.stop()

    names = _span_names(span_exporter)
    assert "IntentClassification" in names
    assert "Routing" in names
    assert "ProviderSelection" in names
    assert names.index("Routing") < names.index("ProviderSelection")


def test_orchestration_routing_events_published(bus: EventBus) -> None:
    routing: list[dict[str, object]] = []
    selected: list[dict[str, object]] = []
    bus.subscribe(
        ORCHESTRATION_ROUTING_COMPLETED,
        lambda event: routing.append(dict(event.payload)),
    )
    bus.subscribe(
        ORCHESTRATION_PROVIDER_SELECTED,
        lambda event: selected.append(dict(event.payload)),
    )

    orchestration = OrchestrationService(bus, provider_registry=build_registry())
    orchestration.start()
    publish_chat(
        bus,
        "What time is it?",
        request_id="req-bus-orch",
        workspace_id="ws-1",
        entity_id="ent-1",
    )
    orchestration.stop()

    assert len(routing) == 1
    assert routing[0]["request_id"] == "req-bus-orch"
    assert routing[0]["provider_id"] == "system_facts"
    assert routing[0]["workspace_id"] == "ws-1"
    assert routing[0]["entity_id"] == "ent-1"

    assert len(selected) == 1
    assert selected[0]["provider_id"] == "system_facts"


def test_orchestration_scope_attributes_on_spans(
    bus: EventBus,
    span_exporter: InMemorySpanExporter,
) -> None:
    tracing = TracingService(bus, enabled=True, span_exporter=span_exporter)
    orchestration = OrchestrationService(bus, provider_registry=build_registry())
    tracing.start()
    orchestration.start()

    publish_chat(
        bus,
        "Open Outlook",
        request_id="req-scope",
        workspace_id="ws-scope",
        selected_entity_id="ent-scope",
    )

    orchestration.stop()
    tracing.stop()

    routing_spans = [
        span
        for span in span_exporter.get_finished_spans()
        if span.name == "Routing"
    ]
    assert len(routing_spans) == 1
    attrs = dict(routing_spans[0].attributes or {})
    assert attrs.get("workspace_id") == "ws-scope"
    assert attrs.get("entity_id") == "ent-scope"


def test_intent_classified_alone_does_not_emit_routing_spans(
    bus: EventBus,
    span_exporter: InMemorySpanExporter,
) -> None:
    tracing = TracingService(bus, enabled=True, span_exporter=span_exporter)
    tracing.start()

    bus.publish(
        ORCHESTRATION_INTENT_CLASSIFIED,
        {
            "request_id": "req-defer",
            "intent": "unhandled",
            "query": "tell me a joke",
        },
        source="test",
    )
    tracing.stop()

    names = _span_names(span_exporter)
    assert names == ["IntentClassification"]
