"""OpenTelemetry tracing bridge for EventBus topics."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CAPABILITY_CLASSIFIED,
    CAPABILITY_DISPATCH,
    ORCHESTRATION_INTENT_CLASSIFIED,
    ORCHESTRATION_PROVIDER_SELECTED,
    ORCHESTRATION_RECEIPT,
    ORCHESTRATION_ROUTING_COMPLETED,
    ORCHESTRATION_RUN_SNAPSHOT,
    ORCHESTRATION_TRUTH_VALIDATED,
)
from ai_command_center.services.base import BaseService

_logger = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
        SpanExporter,
    )

    _OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    trace = None  # type: ignore[assignment]
    SpanExporter = object  # type: ignore[assignment,misc]
    _OTEL_AVAILABLE = False


def _init_tracer(span_exporter: Any | None = None) -> Any:
    if not _OTEL_AVAILABLE:
        return None
    provider = TracerProvider(resource=Resource.create({"service.name": "ai-command-center"}))
    if span_exporter is not None:
        provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    return trace.get_tracer("ai_command_center")


def _scope_attributes(payload: dict[str, object]) -> dict[str, str]:
    attrs: dict[str, str] = {}
    workspace_id = str(payload.get("workspace_id", "")).strip()
    if workspace_id:
        attrs["workspace_id"] = workspace_id
    entity_id = str(payload.get("entity_id", "")).strip()
    if not entity_id:
        entity_id = str(payload.get("selected_entity_id", "")).strip()
    if entity_id:
        attrs["entity_id"] = entity_id
    return attrs


class TracingService(BaseService):
    """Maps canonical bus events to OTel spans (no-op when OTel unavailable)."""

    name = "tracing"

    def __init__(
        self,
        bus,
        *,
        enabled: bool = True,
        span_exporter: SpanExporter | None = None,
    ) -> None:
        super().__init__(bus)
        self._enabled = enabled and _OTEL_AVAILABLE
        self._tracer = _init_tracer(span_exporter) if self._enabled else None
        self._spans: dict[str, Any] = {}
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        if not self._enabled:
            _logger.info("tracing: OpenTelemetry unavailable or disabled")
            return
        topics = (
            ORCHESTRATION_INTENT_CLASSIFIED,
            ORCHESTRATION_ROUTING_COMPLETED,
            ORCHESTRATION_PROVIDER_SELECTED,
            ORCHESTRATION_RECEIPT,
            ORCHESTRATION_TRUTH_VALIDATED,
            ORCHESTRATION_RUN_SNAPSHOT,
            CAPABILITY_CLASSIFIED,
            CAPABILITY_DISPATCH,
        )
        for topic in topics:
            self._unsubscribers.append(self._bus.subscribe(topic, self._on_event))

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._spans.clear()

    def _request_id(self, payload: dict[str, object]) -> str:
        return str(payload.get("request_id", "")).strip()

    def _on_event(self, event: Event) -> None:
        if self._tracer is None:
            return
        payload = event.payload
        request_id = self._request_id(payload)
        if not request_id:
            return

        span_name = self._span_name(event.topic)
        attrs = {
            "request_id": request_id,
            **_scope_attributes(payload),
        }
        if event.topic == ORCHESTRATION_INTENT_CLASSIFIED:
            attrs["intent"] = str(payload.get("intent", ""))
            span = self._tracer.start_span(span_name, attributes=attrs)
            self._spans[request_id] = span
            return

        parent = self._spans.get(request_id)
        if parent is not None and trace is not None:
            context = trace.set_span_in_context(parent)
            span = self._tracer.start_span(span_name, context=context)
        else:
            span = self._tracer.start_span(span_name)
        for key, value in attrs.items():
            span.set_attribute(key, value)
        if event.topic in {
            ORCHESTRATION_ROUTING_COMPLETED,
            ORCHESTRATION_PROVIDER_SELECTED,
        }:
            span.set_attribute("intent", str(payload.get("intent", "")))
        if event.topic == ORCHESTRATION_PROVIDER_SELECTED:
            span.set_attribute("provider_id", str(payload.get("provider_id", "")))
        if event.topic == ORCHESTRATION_RUN_SNAPSHOT:
            span.set_attribute("trace_id", format(span.get_span_context().trace_id, "032x"))
            span.set_attribute("span_id", format(span.get_span_context().span_id, "016x"))
            span.end()
            root = self._spans.pop(request_id, None)
            if root is not None:
                root.end()
        else:
            span.end()

    @staticmethod
    def _span_name(topic: str) -> str:
        mapping = {
            ORCHESTRATION_INTENT_CLASSIFIED: "IntentClassification",
            ORCHESTRATION_ROUTING_COMPLETED: "Routing",
            ORCHESTRATION_PROVIDER_SELECTED: "ProviderSelection",
            ORCHESTRATION_RECEIPT: "ExecutionReceipt",
            ORCHESTRATION_TRUTH_VALIDATED: "TruthBoundary",
            ORCHESTRATION_RUN_SNAPSHOT: "Response",
            CAPABILITY_CLASSIFIED: "CapabilityClassification",
            CAPABILITY_DISPATCH: "CapabilityDispatch",
        }
        return mapping.get(topic, topic)
