"""EpisodicReflectionService — learn from outcomes without inventing state."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    ORCHESTRATION_RECEIPT,
    ORCHESTRATION_TRUTH_VALIDATED,
)
from ai_command_center.domain.execution_result_type import ExecutionResultType
from ai_command_center.services.base import BaseService
from ai_command_center.core.state_intelligence.state_delta_engine import StateDeltaEngine


class EpisodicReflectionService(BaseService):
    """Post-run reflection: success?, changes?, remember?, relationships?, invalid?"""

    name = "episodic_reflection"

    def __init__(
        self,
        bus,
        *,
        state_delta: StateDeltaEngine | None = None,
    ) -> None:
        super().__init__(bus)
        self._state_delta = state_delta
        self._unsubscribers: list[Callable[[], None]] = []
        self._last_reflections: list[dict[str, Any]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(ORCHESTRATION_RECEIPT, self._on_receipt)
        )
        self._unsubscribers.append(
            self._bus.subscribe(ORCHESTRATION_TRUTH_VALIDATED, self._on_truth)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def reflect(self, receipt: dict[str, Any], *, truth_valid: bool | None = None) -> dict[str, Any]:
        success = bool(receipt.get("success", False))
        result_type = str(
            receipt.get("result_type")
            or (
                ExecutionResultType.SUCCESS.value
                if success
                else ExecutionResultType.FAILED.value
            )
        )
        reflection = {
            "did_succeed": success and (truth_valid is not False),
            "result_type": result_type,
            "what_changed": self._extract_changes(receipt),
            "should_remember": self._should_remember(receipt, success),
            "relationships_created": self._extract_relationships(receipt),
            "invalidated_state": [] if success else [str(receipt.get("intent") or "")],
            "evidence_only": True,
        }
        self._last_reflections.append(reflection)
        if len(self._last_reflections) > 50:
            self._last_reflections = self._last_reflections[-50:]

        if (
            reflection["did_succeed"]
            and self._state_delta is not None
            and result_type != ExecutionResultType.NO_OP.value
        ):
            enriched = dict(receipt)
            enriched["result_type"] = result_type
            self._state_delta.apply_receipt(enriched)

        return reflection

    def recent_reflections(self) -> list[dict[str, Any]]:
        return list(self._last_reflections)

    def _on_receipt(self, event: Event) -> None:
        payload = dict(event.payload)
        # Prefer waiting for truth when available; still reflect on receipt.
        self.reflect(payload)

    def _on_truth(self, event: Event) -> None:
        # Re-assert with truth bit when validation arrives after receipt.
        valid = bool(event.payload.get("valid", event.payload.get("truth_valid", True)))
        receipt = event.payload.get("receipt")
        if isinstance(receipt, dict):
            self.reflect(receipt, truth_valid=valid)

    @staticmethod
    def _extract_changes(receipt: dict[str, Any]) -> list[str]:
        changes: list[str] = []
        facts = receipt.get("facts")
        if isinstance(facts, dict):
            for key, value in facts.items():
                changes.append(f"{key}={value}")
        elif isinstance(facts, (list, tuple)):
            for item in facts:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    changes.append(f"{item[0]}={item[1]}")
                else:
                    changes.append(str(item))
        intent = str(receipt.get("intent") or "")
        if intent:
            changes.insert(0, f"intent={intent}")
        return changes

    @staticmethod
    def _should_remember(receipt: dict[str, Any], success: bool) -> bool:
        if not success:
            return False
        intent = str(receipt.get("intent") or "")
        return intent.startswith("memory.") or intent in {"notes.create", "goals.create"}

    @staticmethod
    def _extract_relationships(receipt: dict[str, Any]) -> list[dict[str, str]]:
        facts = receipt.get("facts")
        mapping = dict(facts) if isinstance(facts, dict) else {}
        if isinstance(facts, (list, tuple)):
            for item in facts:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    mapping[str(item[0])] = item[1]
        from_id = str(mapping.get("from_node_id") or "")
        to_id = str(mapping.get("to_node_id") or "")
        rel = str(mapping.get("relation") or mapping.get("edge_type") or "")
        if from_id and to_id and rel:
            return [{"from": from_id, "to": to_id, "type": rel}]
        return []
