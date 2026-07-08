"""Decision domain model — contract for DecisionInspector (no persistence)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Decision:
    """A single agent decision requiring or recording user approval."""

    reason: str = ""
    alternatives: tuple[str, ...] = ()
    chosen: str = ""
    affected_files: tuple[str, ...] = ()

    def to_inspect_payload(self, *, ref_id: str = "", label: str = "") -> dict[str, Any]:
        """Build a payload dict suitable for ``InspectableRef.from_payload()``."""
        display = label or self.reason or ref_id or "Decision"
        payload: dict[str, Any] = {
            "kind": "decision",
            "ref_id": ref_id or "decision-stub",
            "label": display,
            "payload": {
                "reason": self.reason,
                "chosen": self.chosen,
            },
        }
        if self.alternatives:
            payload["payload"]["alternatives"] = ", ".join(self.alternatives)
        if self.affected_files:
            payload["payload"]["affected_files"] = ", ".join(self.affected_files)
        return payload


__all__ = ["Decision"]
