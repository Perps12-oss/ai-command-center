"""StateDeltaEngine — transform execution receipts into World Model state changes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ai_command_center.core.events.topics import RUNTIME_ACTION_REQUEST
from ai_command_center.domain.execution_result_type import ExecutionResultType
from ai_command_center.domain.world_model import MutationType
from ai_command_center.services.base import BaseService


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class StateDeltaEngine(BaseService):
    """Receipts → state deltas (entity properties / edges), not artifact spam."""

    name = "state_delta"

    def __init__(self, bus) -> None:
        super().__init__(bus)

    def _on_load(self) -> None:
        return

    def _on_unload(self) -> None:
        return

    def deltas_from_receipt(self, receipt: dict[str, Any]) -> list[dict[str, Any]]:
        """Compute state-change mutations from a receipt payload."""
        result_type = str(
            receipt.get("result_type") or ExecutionResultType.SUCCESS.value
        )
        if result_type == ExecutionResultType.NO_OP.value:
            return []
        if not receipt.get("success", False) and result_type == ExecutionResultType.FAILED.value:
            return []

        facts = dict(receipt.get("facts") or {})
        intent = str(receipt.get("intent") or receipt.get("capability") or "")
        request_id = str(receipt.get("request_id") or "")
        now = _utcnow()
        deltas: list[dict[str, Any]] = []

        # Prefer typed reality updates over raw execution_run dumps.
        if intent in {"memory.store", "memory_remember"} or facts.get("memory_id"):
            mem_id = str(facts.get("memory_id") or facts.get("id") or f"memory:{uuid.uuid4().hex[:8]}")
            deltas.append(
                self._node_delta(
                    node_id=mem_id if mem_id.startswith("memory:") else f"memory:{mem_id}",
                    node_type="memory",
                    attributes={
                        "label": facts.get("label") or facts.get("body") or intent,
                        "content": facts.get("content") or facts.get("body") or "",
                        "status": "ACTIVE",
                        "confidence": 0.9,
                        "verified_at": now,
                        "source": "execution_receipt",
                        "workspace_id": facts.get("workspace_id") or "",
                    },
                )
            )
        elif intent in {"notes.create", "note_new"} or facts.get("path"):
            path = str(facts.get("path") or facts.get("output") or "note")
            deltas.append(
                self._node_delta(
                    node_id=f"note:{path}",
                    node_type="note",
                    attributes={
                        "title": path,
                        "path": path,
                        "status": "ACTIVE",
                        "confidence": 0.9,
                        "verified_at": now,
                        "source": "execution_receipt",
                    },
                )
            )
        elif intent in {"applications.launch", "launch_application"}:
            app = str(facts.get("application") or facts.get("app") or "app")
            deltas.append(
                self._node_delta(
                    node_id=f"application:{app}",
                    node_type="application",
                    attributes={
                        "name": app,
                        "status": "OPEN",
                        "confidence": 0.85,
                        "verified_at": now,
                        "source": "execution_receipt",
                    },
                )
            )
        elif intent == "navigate":
            view = str(facts.get("view") or "home")
            deltas.append(
                self._node_delta(
                    node_id="workspace:focus",
                    node_type="workspace",
                    attributes={
                        "focused_view": view,
                        "status": "ACTIVE",
                        "confidence": 1.0,
                        "verified_at": now,
                        "source": "execution_receipt",
                    },
                )
            )

        # Graph-native relationship when both ends known.
        from_id = str(facts.get("from_node_id") or "")
        to_id = str(facts.get("to_node_id") or "")
        rel_type = str(facts.get("relation") or facts.get("edge_type") or "")
        if from_id and to_id and rel_type:
            deltas.append(
                self._edge_delta(
                    from_node_id=from_id,
                    to_node_id=to_id,
                    edge_type=rel_type,
                    attributes={
                        "status": "active",
                        "confidence": float(facts.get("confidence") or 0.8),
                        "verified_at": now,
                        "source": "execution_receipt",
                    },
                )
            )

        # Compact run marker (not a full artifact dump).
        if request_id and deltas:
            deltas.append(
                self._node_delta(
                    node_id=f"execution_run:{request_id[:16]}",
                    node_type="execution_run",
                    attributes={
                        "request_id": request_id,
                        "intent": intent,
                        "status": "COMPLETE",
                        "result_type": result_type,
                        "verified_at": now,
                        "source": "execution_receipt",
                    },
                )
            )
        return deltas

    def publish_deltas(
        self,
        deltas: list[dict[str, Any]],
        *,
        correlation: dict[str, Any] | None = None,
    ) -> int:
        count = 0
        corr = correlation or {}
        for delta in deltas:
            mutation_id = uuid.uuid4().hex
            mutation = {
                "id": mutation_id,
                "type": delta["type"],
                "correlation": corr,
                "payload": delta.get("payload") or {},
            }
            self._bus.publish(
                RUNTIME_ACTION_REQUEST,
                {
                    "action_id": mutation_id,
                    "tier": "write",
                    "auto_approve": True,
                    "summary": f"State delta {delta['type']}",
                    "mutation": mutation,
                    "correlation": corr,
                    "source_engine": self.name,
                },
                source=self.name,
            )
            count += 1
        return count

    def apply_receipt(
        self,
        receipt: dict[str, Any],
        *,
        correlation: dict[str, Any] | None = None,
    ) -> int:
        return self.publish_deltas(
            self.deltas_from_receipt(receipt),
            correlation=correlation,
        )

    @staticmethod
    def _node_delta(
        *,
        node_id: str,
        node_type: str,
        attributes: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "type": MutationType.CREATE_NODE.value,
            "payload": {
                "node": {
                    "id": node_id,
                    "type": node_type,
                    "attributes": attributes,
                }
            },
        }

    @staticmethod
    def _edge_delta(
        *,
        from_node_id: str,
        to_node_id: str,
        edge_type: str,
        attributes: dict[str, Any],
    ) -> dict[str, Any]:
        edge_id = f"edge:{from_node_id}:{edge_type}:{to_node_id}"
        return {
            "type": MutationType.CREATE_EDGE.value,
            "payload": {
                "edge": {
                    "id": edge_id,
                    "from_node_id": from_node_id,
                    "to_node_id": to_node_id,
                    "type": edge_type,
                    "attributes": attributes,
                }
            },
        }
