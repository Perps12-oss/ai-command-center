"""Execution Intent Registry — in-flight plans/runs/goals as planning input.

Not a separate subsystem: tracks Intent so projections see Reality + Intent.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    EXECUTION_RUN_REQUEST,
    EXECUTION_RUN_STARTED,
    GOAL_SUBMIT_REQUEST,
    PLAN_FAILED,
    PLAN_GENERATED,
    PLAN_REQUEST,
)
from ai_command_center.services.base import BaseService


@dataclass(slots=True)
class IntentRecord:
    """A pending or active execution intent."""

    intent_id: str
    kind: str  # pending_plan | active_run | scheduled_goal
    text: str = ""
    capability: str = ""
    workspace_id: str = ""
    status: str = "pending"
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "kind": self.kind,
            "text": self.text,
            "capability": self.capability,
            "workspace_id": self.workspace_id,
            "status": self.status,
            "attributes": dict(self.attributes),
        }


class ExecutionIntentRegistry(BaseService):
    """Tracks active runs, pending plans, and submitted goals for query."""

    name = "execution_intent_registry"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._intents: dict[str, IntentRecord] = {}
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        topics = (
            (GOAL_SUBMIT_REQUEST, self._on_goal_submit),
            (PLAN_REQUEST, self._on_plan_request),
            (PLAN_GENERATED, self._on_plan_generated),
            (PLAN_FAILED, self._on_plan_terminal),
            (EXECUTION_RUN_REQUEST, self._on_run_request),
            (EXECUTION_RUN_STARTED, self._on_run_started),
            (EXECUTION_RUN_COMPLETE, self._on_run_terminal),
            (EXECUTION_RUN_FAILED, self._on_run_terminal),
        )
        for topic, handler in topics:
            self._unsubscribers.append(self._bus.subscribe(topic, handler))

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._intents.clear()

    def list_active(self, *, workspace_id: str = "") -> list[IntentRecord]:
        out = [
            r
            for r in self._intents.values()
            if r.status in {"pending", "active", "planning"}
        ]
        if workspace_id:
            out = [r for r in out if not r.workspace_id or r.workspace_id == workspace_id]
        return out

    def to_projection_dicts(self, *, workspace_id: str = "") -> list[dict[str, Any]]:
        return [r.to_dict() for r in self.list_active(workspace_id=workspace_id)]

    def has_matching_intent(self, text: str, *, workspace_id: str = "") -> IntentRecord | None:
        needle = text.strip().lower()
        if not needle:
            return None
        for record in self.list_active(workspace_id=workspace_id):
            if record.text.strip().lower() == needle:
                return record
            if needle in record.text.lower() or record.text.lower() in needle:
                return record
        return None

    def _upsert(
        self,
        intent_id: str,
        *,
        kind: str,
        text: str = "",
        capability: str = "",
        workspace_id: str = "",
        status: str = "pending",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        existing = self._intents.get(intent_id)
        if existing is not None:
            existing.kind = kind or existing.kind
            existing.text = text or existing.text
            existing.capability = capability or existing.capability
            existing.workspace_id = workspace_id or existing.workspace_id
            existing.status = status
            if attributes:
                existing.attributes.update(attributes)
            return
        self._intents[intent_id] = IntentRecord(
            intent_id=intent_id,
            kind=kind,
            text=text,
            capability=capability,
            workspace_id=workspace_id,
            status=status,
            attributes=dict(attributes or {}),
        )

    def _on_goal_submit(self, event: Event) -> None:
        rid = str(event.payload.get("request_id") or event.payload.get("goal_id") or "")
        if not rid:
            return
        self._upsert(
            rid,
            kind="scheduled_goal",
            text=str(event.payload.get("text") or event.payload.get("goal") or ""),
            capability=str(event.payload.get("capability") or "goal"),
            workspace_id=str(event.payload.get("workspace_id") or ""),
            status="pending",
        )

    def _on_plan_request(self, event: Event) -> None:
        rid = str(event.payload.get("request_id") or "")
        if not rid:
            return
        self._upsert(
            rid,
            kind="pending_plan",
            text=str(event.payload.get("goal") or event.payload.get("text") or ""),
            workspace_id=str(event.payload.get("workspace_id") or ""),
            status="planning",
        )

    def _on_plan_generated(self, event: Event) -> None:
        rid = str(event.payload.get("request_id") or "")
        if not rid:
            return
        self._upsert(
            rid,
            kind="pending_plan",
            text=str(event.payload.get("goal") or ""),
            status="pending",
            attributes={"plan": event.payload.get("plan")},
        )

    def _on_plan_terminal(self, event: Event) -> None:
        rid = str(event.payload.get("request_id") or "")
        if rid in self._intents:
            self._intents[rid].status = "failed"
            self._intents.pop(rid, None)

    def _on_run_request(self, event: Event) -> None:
        rid = str(event.payload.get("request_id") or event.payload.get("run_id") or "")
        if not rid:
            return
        self._upsert(
            rid,
            kind="active_run",
            text=str(event.payload.get("goal") or event.payload.get("text") or ""),
            workspace_id=str(event.payload.get("workspace_id") or ""),
            status="pending",
        )

    def _on_run_started(self, event: Event) -> None:
        rid = str(event.payload.get("request_id") or event.payload.get("run_id") or "")
        if not rid:
            return
        self._upsert(rid, kind="active_run", status="active")

    def _on_run_terminal(self, event: Event) -> None:
        rid = str(event.payload.get("request_id") or event.payload.get("run_id") or "")
        if rid:
            self._intents.pop(rid, None)
