"""ExecutionEvent domain — append-only execution timeline stream (ACC UI PR 8)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


def _pairs_to_dict(pairs: tuple[tuple[str, str], ...]) -> dict[str, str]:
    return {str(k): str(v) for k, v in pairs}


def _dict_to_pairs(data: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for key in sorted(data):
        value = data[key]
        if value is None:
            continue
        if isinstance(value, (dict, list, tuple)):
            pairs.append((str(key), json.dumps(value, default=str, sort_keys=True)))
        else:
            pairs.append((str(key), str(value)))
    return tuple(pairs)


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    """Immutable execution timeline event — distinct from frozen TimelineEvent."""

    event_id: str
    trace_id: str
    parent_event_id: str | None
    timestamp: float
    event_type: str
    actor: str
    scope: str
    request_id: str
    payload: tuple[tuple[str, str], ...] = ()
    state_diff: tuple[tuple[str, str], ...] | None = None

    def payload_dict(self) -> dict[str, str]:
        return _pairs_to_dict(self.payload)

    def state_diff_dict(self) -> dict[str, str] | None:
        if self.state_diff is None:
            return None
        return _pairs_to_dict(self.state_diff)

    def to_bus_payload(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "event_id": self.event_id,
            "trace_id": self.trace_id,
            "parent_event_id": self.parent_event_id or "",
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor": self.actor,
            "scope": self.scope,
            "request_id": self.request_id,
            "payload": dict(self.payload),
        }
        if self.state_diff is not None:
            data["state_diff"] = dict(self.state_diff)
        return data

    @classmethod
    def from_bus_payload(cls, payload: dict[str, Any]) -> ExecutionEvent:
        raw_payload = payload.get("payload") or {}
        raw_diff = payload.get("state_diff")
        parent = str(payload.get("parent_event_id", "")).strip() or None
        if isinstance(raw_payload, dict):
            pairs = _dict_to_pairs(raw_payload)
        elif isinstance(raw_payload, (list, tuple)):
            pairs = tuple(
                (str(item[0]), str(item[1]))
                for item in raw_payload
                if isinstance(item, (list, tuple)) and len(item) >= 2
            )
        else:
            pairs = ()
        diff_pairs: tuple[tuple[str, str], ...] | None
        if raw_diff is None:
            diff_pairs = None
        elif isinstance(raw_diff, dict):
            diff_pairs = _dict_to_pairs(raw_diff)
        else:
            diff_pairs = ()
        return cls(
            event_id=str(payload.get("event_id", "")).strip(),
            trace_id=str(payload.get("trace_id", "")).strip(),
            parent_event_id=parent,
            timestamp=float(payload.get("timestamp", 0.0) or 0.0),
            event_type=str(payload.get("event_type", "")).strip(),
            actor=str(payload.get("actor", "")).strip(),
            scope=str(payload.get("scope", "")).strip(),
            request_id=str(payload.get("request_id", "")).strip(),
            payload=pairs,
            state_diff=diff_pairs,
        )


__all__ = ["ExecutionEvent", "_dict_to_pairs"]
