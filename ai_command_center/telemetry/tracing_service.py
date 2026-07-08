"""OpenTelemetry tracing bridge for EventBus topics."""

from __future__ import annotations

import logging
import socket
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

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


def _otlp_endpoint_reachable(endpoint: str, *, timeout_s: float = 0.5) -> bool:
    """Best-effort probe so we do not spam retries when no collector is running."""
    raw = endpoint.strip()
    if not raw:
        return False
    parsed = urlparse(raw if "://" in raw else f"http://{raw}")
    host = parsed.hostname or "127.0.0.1"
    if parsed.port is not None:
        port = parsed.port
    elif parsed.scheme == "https":
        port = 443
    else:
        port = 4318
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def _reset_tracer_provider() -> None:
    if not _OTEL_AVAILABLE or trace is None:
        return
    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()
    from opentelemetry.trace import _TRACER_PROVIDER_SET_ONCE

    _TRACER_PROVIDER_SET_ONCE._done = False


def _init_tracer(
    span_exporter: Any | None = None,
    *,
    otel_endpoint: str = "",
) -> Any:
    if not _OTEL_AVAILABLE:
        return None
    _reset_tracer_provider()
    provider = TracerProvider(resource=Resource.create({"service.name": "ai-command-center"}))
    if span_exporter is not None:
        provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    elif otel_endpoint.strip():
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            endpoint = otel_endpoint.rstrip("/")
            if not endpoint.endswith("/v1/traces"):
                endpoint = f"{endpoint}/v1/traces"
            exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception:
            _logger.warning("tracing: OTLP exporter unavailable; using console exporter")
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
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
        otel_endpoint: str = "",
        span_exporter: SpanExporter | None = None,
    ) -> None:
        super().__init__(bus)
        if (
            enabled
            and span_exporter is None
            and otel_endpoint.strip()
            and not _otlp_endpoint_reachable(otel_endpoint)
        ):
            _logger.warning(
                "tracing: OTLP endpoint %s unreachable; tracing disabled "
                "(start a collector or disable otel_enabled in Settings)",
                otel_endpoint.strip(),
            )
            enabled = False
        self._enabled = enabled and _OTEL_AVAILABLE
        self._tracer = (
            _init_tracer(span_exporter, otel_endpoint=otel_endpoint)
            if self._enabled
            else None
        )
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
        for span in self._spans.values():
            span.end()
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
