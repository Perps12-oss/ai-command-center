"""TraceSpan domain model — tree-based execution trace.

Used by the execution detail view and inspector trace tab.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class TraceSpan:
    """A single span in an execution trace tree.

    Spans form a tree via parent_id → span_id relationships.
    """

    span_id: str = ""
    parent_id: str = ""
    name: str = ""
    kind: str = "internal"      # "internal" | "client" | "server" | "producer" | "consumer"
    status: str = "ok"          # "ok" | "error" | "unset"
    started_at: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    attributes: dict = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    error_message: str = ""
    children: list["TraceSpan"] = field(default_factory=list)

    @property
    def is_root(self) -> bool:
        return not self.parent_id

    @property
    def is_error(self) -> bool:
        return self.status == "error" or bool(self.error_message)

    @classmethod
    def from_dict(cls, d: dict) -> "TraceSpan":
        return cls(
            span_id=str(d.get("span_id", "")),
            parent_id=str(d.get("parent_id", "")),
            name=str(d.get("name", "")),
            kind=str(d.get("kind", "internal")),
            status=str(d.get("status", "ok")),
            started_at=float(d.get("started_at", time.time())),
            duration_ms=float(d.get("duration_ms", 0.0)),
            attributes=dict(d.get("attributes") or {}),
            events=list(d.get("events") or []),
            error_message=str(d.get("error_message", "")),
        )


def build_span_tree(spans: list[TraceSpan]) -> list[TraceSpan]:
    """Build a forest (list of root spans) from a flat span list."""
    by_id: dict[str, TraceSpan] = {s.span_id: s for s in spans}
    roots: list[TraceSpan] = []
    for span in spans:
        if span.parent_id and span.parent_id in by_id:
            by_id[span.parent_id].children.append(span)
        else:
            roots.append(span)
    return roots
