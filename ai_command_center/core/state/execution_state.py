"""ExecutionState — active execution context reducer for the inspector panel.

Subscribes to execution.query.result and maintains the current execution
context snapshot surfaced to the ExecutionInspector via AppState.

This module is imported by app_state.py as part of the reducer chain.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import EXECUTION_QUERY_RESULT


@dataclass(frozen=True, slots=True)
class SpanItem:
    """Single trace span projection."""

    span_id: str = ""
    parent_id: str = ""
    name: str = ""
    kind: str = "internal"
    status: str = "ok"
    duration_ms: float = 0.0
    started_at: float = 0.0
    attributes: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class ArtifactItem:
    """Artifact stub for inspector artifacts tab."""

    artifact_id: str = ""
    kind: str = "text"
    label: str = ""
    size_bytes: int = 0
    created_at: float = 0.0
    mime_type: str = ""


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Active execution context snapshot for the inspector panel."""

    request_id: str = ""
    provider_id: str = ""
    model: str = ""
    status: str = "idle"
    intent: str = ""
    query: str = ""
    response_source: str = ""
    truth_valid: bool = False
    truth_detail: str = ""
    trace_spans: tuple[SpanItem, ...] = ()
    artifacts: tuple[ArtifactItem, ...] = ()
    metrics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # metrics must be immutable-friendly — convert to tuple of pairs
        object.__setattr__(self, "metrics", dict(self.metrics))


def _parse_spans(raw: list[Any]) -> tuple[SpanItem, ...]:
    items: list[SpanItem] = []
    for s in raw:
        if not isinstance(s, dict):
            continue
        attrs = tuple(
            (str(k), str(v))
            for k, v in (s.get("attributes") or {}).items()
        )
        items.append(SpanItem(
            span_id=str(s.get("span_id", "")),
            parent_id=str(s.get("parent_id", "")),
            name=str(s.get("name", "")),
            kind=str(s.get("kind", "internal")),
            status=str(s.get("status", "ok")),
            duration_ms=float(s.get("duration_ms", 0.0)),
            started_at=float(s.get("started_at", 0.0)),
            attributes=attrs,
        ))
    return tuple(items)


def _parse_artifacts(raw: list[Any]) -> tuple[ArtifactItem, ...]:
    items: list[ArtifactItem] = []
    for a in raw:
        if not isinstance(a, dict):
            continue
        items.append(ArtifactItem(
            artifact_id=str(a.get("artifact_id", "")),
            kind=str(a.get("kind", "text")),
            label=str(a.get("label", "")),
            size_bytes=int(a.get("size_bytes", 0)),
            created_at=float(a.get("created_at", 0.0)),
            mime_type=str(a.get("mime_type", "")),
        ))
    return tuple(items)


def reduce_execution_query_result(
    execution_context: ExecutionContext,
    event: Event,
) -> ExecutionContext:
    """Pure reducer for EXECUTION_QUERY_RESULT."""
    if event.topic != EXECUTION_QUERY_RESULT:
        return execution_context
    p = event.payload
    return ExecutionContext(
        request_id=str(p.get("request_id", "")),
        provider_id=str(p.get("provider_id", "")),
        model=str(p.get("model", "")),
        status=str(p.get("status", "idle")),
        intent=str(p.get("intent", "")),
        query=str(p.get("query", "")),
        response_source=str(p.get("response_source", "")),
        truth_valid=bool(p.get("truth_valid", False)),
        truth_detail=str(p.get("truth_detail", "")),
        trace_spans=_parse_spans(p.get("trace_spans") or []),
        artifacts=_parse_artifacts(p.get("artifacts") or []),
        metrics=dict(p.get("metrics") or {}),
    )
