"""Inspectable reference projections for the global inspector system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def _coerce_payload_pairs(payload: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    items: list[tuple[str, str]] = []
    for key, value in payload.items():
        if value is None:
            continue
        if key == "payload" and isinstance(value, Mapping):
            items.extend(_coerce_payload_pairs(value))
            continue
        if key in {"kind", "ref_id", "id", "label"}:
            continue
        items.append((str(key), str(value)))
    return tuple(items)


@dataclass(frozen=True, slots=True)
class InspectableRef:
    """Any ACC object that can be inspected."""

    kind: str = ""
    ref_id: str = ""
    label: str = ""
    payload: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", str(self.kind))
        object.__setattr__(self, "ref_id", str(self.ref_id))
        object.__setattr__(self, "label", str(self.label))
        object.__setattr__(self, "payload", tuple((str(k), str(v)) for k, v in self.payload))

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "InspectableRef":
        """Build a ref from a UI or EventBus payload dict."""
        kind = str(payload.get("kind", "")).strip()
        ref_id = str(payload.get("ref_id") or payload.get("id") or "").strip()
        label = str(payload.get("label", "")).strip()
        if not kind or not ref_id:
            return cls()
        payload_items = _coerce_payload_pairs(payload)
        return cls(kind=kind, ref_id=ref_id, label=label, payload=payload_items)

    def as_dict(self) -> dict[str, str]:
        """Return payload key/value pairs as a plain dict."""
        return dict(self.payload)

    def get(self, key: str, default: str = "") -> str:
        """Look up a payload field by key."""
        return self.as_dict().get(key, default)


__all__ = ["InspectableRef"]
