"""Brain runtime safety gateway and World Model mutation owner."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from pathlib import Path

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    OBSERVATION_RECEIVED,
    RUNTIME_ACTION_COMPLETED,
    RUNTIME_ACTION_DENIED,
    RUNTIME_ACTION_FAILED,
    RUNTIME_ACTION_REQUEST,
    RUNTIME_ACTION_STARTED,
    RUNTIME_APPROVAL_DECIDED,
    RUNTIME_APPROVAL_REQUESTED,
    RUNTIME_WORLD_MODEL_APPLY_COMPLETED,
    RUNTIME_WORLD_MODEL_APPLY_REQUESTED,
)
from ai_command_center.core.world_model.world_model import WorldModel
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.observation import ObservationChangeType, ObservationSource
from ai_command_center.domain.runtime_safety import (
    ActionResult,
    ActionStatus,
    ApprovalDecision,
    ApprovalRequest,
    RuntimeErrorCode,
    RuntimeErrorRecord,
    RetryHint,
    SecurityTier,
)
from ai_command_center.domain.world_model import Mutation, MutationType, Node
from ai_command_center.services.base import BaseService


class BrainRuntimeService(BaseService):
    """Executes approved Brain actions and owns World Model mutation application."""

    name = "brain_runtime"

    def __init__(self, bus, world_model: WorldModel) -> None:
        super().__init__(bus)
        self._world_model = world_model
        self._unsubscribers: list[Callable[[], None]] = []
        self._pending: dict[str, dict] = {}
        self._timers: dict[str, threading.Timer] = {}

    def _on_load(self) -> None:
        self._unsubscribers.extend(
            [
                self._bus.subscribe(RUNTIME_ACTION_REQUEST, self._on_action_request),
                self._bus.subscribe(RUNTIME_APPROVAL_DECIDED, self._on_approval_decided),
                self._bus.subscribe(OBSERVATION_RECEIVED, self._on_observation_received),
            ]
        )

    def _on_unload(self) -> None:
        for timer in self._timers.values():
            timer.cancel()
        self._timers.clear()
        self._pending.clear()
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_action_request(self, event: Event) -> None:
        payload = dict(event.payload)
        action_id = str(payload.get("action_id") or uuid.uuid4().hex)
        correlation = CorrelationContext.from_payload(payload).with_action(action_id)
        tier = _parse_tier(payload.get("tier"))
        self._bus.publish(
            RUNTIME_ACTION_STARTED,
            {
                "action_id": action_id,
                "tier": tier.value,
                "correlation": correlation.to_payload(),
            },
            source=self.name,
        )

        requires_approval = tier == SecurityTier.WRITE_DESTROY or bool(
            payload.get("require_approval", False)
        )
        if requires_approval and not bool(payload.get("auto_approve", False)):
            self._request_approval(action_id, tier, payload, correlation)
            return

        self._execute_action(action_id, payload, correlation)

    def _request_approval(
        self,
        action_id: str,
        tier: SecurityTier,
        payload: dict,
        correlation: CorrelationContext,
    ) -> None:
        approval = ApprovalRequest(
            id=str(payload.get("approval_id") or uuid.uuid4().hex),
            action_id=action_id,
            tier=tier,
            summary=str(payload.get("summary") or f"Approve {action_id}"),
            details=dict(payload.get("details") or {}),
            timeout_seconds=int(payload.get("timeout_seconds") or 60),
            correlation=correlation,
        )
        self._pending[approval.id] = {
            "action_id": action_id,
            "payload": payload,
            "correlation": correlation,
        }
        timer = threading.Timer(
            approval.timeout_seconds,
            lambda: self._deny_approval(approval.id, "approval timeout"),
        )
        timer.daemon = True
        self._timers[approval.id] = timer
        timer.start()
        self._bus.publish(
            RUNTIME_APPROVAL_REQUESTED,
            approval.to_payload(),
            source=self.name,
        )

    def _on_approval_decided(self, event: Event) -> None:
        approval_id = str(event.payload.get("approval_id") or event.payload.get("id") or "")
        if not approval_id or approval_id not in self._pending:
            return
        timer = self._timers.pop(approval_id, None)
        if timer is not None:
            timer.cancel()
        pending = self._pending.pop(approval_id)
        correlation: CorrelationContext = pending["correlation"]
        decision = ApprovalDecision(
            approval_id=approval_id,
            approved=bool(event.payload.get("approved", False)),
            reason=str(event.payload.get("reason") or ""),
            correlation=correlation,
        )
        if not decision.approved:
            self._publish_denied(
                pending["action_id"],
                "approval denied",
                correlation,
                code=RuntimeErrorCode.APPROVAL_DENIED,
            )
            return
        self._execute_action(pending["action_id"], pending["payload"], correlation)

    def _deny_approval(self, approval_id: str, reason: str) -> None:
        pending = self._pending.pop(approval_id, None)
        self._timers.pop(approval_id, None)
        if pending is None:
            return
        correlation: CorrelationContext = pending["correlation"]
        self._publish_denied(
            pending["action_id"],
            reason,
            correlation,
            code=RuntimeErrorCode.APPROVAL_TIMEOUT,
            status=ActionStatus.TIMED_OUT,
        )

    def _execute_action(
        self, action_id: str, payload: dict, correlation: CorrelationContext
    ) -> None:
        raw_mutation = payload.get("mutation")
        output = dict(payload.get("output") or {})
        try:
            if isinstance(raw_mutation, dict):
                mutation = _mutation_from_payload(raw_mutation, correlation)
                self._bus.publish(
                    RUNTIME_WORLD_MODEL_APPLY_REQUESTED,
                    {
                        "action_id": action_id,
                        "mutation": mutation.to_payload(),
                        "correlation": correlation.to_payload(),
                    },
                    source=self.name,
                )
                self._world_model.apply(mutation)
                self._bus.publish(
                    RUNTIME_WORLD_MODEL_APPLY_COMPLETED,
                    {
                        "action_id": action_id,
                        "mutation_id": mutation.id,
                        "correlation": correlation.to_payload(),
                    },
                    source=self.name,
                )
                output["mutation_id"] = mutation.id
            result = ActionResult(
                action_id=action_id,
                status=ActionStatus.SUCCEEDED,
                output=output,
                correlation=correlation,
            )
            self._bus.publish(
                RUNTIME_ACTION_COMPLETED,
                result.to_payload(),
                source=self.name,
            )
        except Exception as exc:
            error = RuntimeErrorRecord(
                code=RuntimeErrorCode.WORLD_MODEL_APPLY_FAILED,
                message=str(exc),
                retry_hint=RetryHint.REVISE_GOAL,
                correlation=correlation,
            )
            result = ActionResult(
                action_id=action_id,
                status=ActionStatus.FAILED,
                error=error,
                correlation=correlation,
            )
            self._bus.publish(RUNTIME_ACTION_FAILED, result.to_payload(), source=self.name)

    def _publish_denied(
        self,
        action_id: str,
        message: str,
        correlation: CorrelationContext,
        *,
        code: RuntimeErrorCode,
        status: ActionStatus = ActionStatus.DENIED,
    ) -> None:
        error = RuntimeErrorRecord(
            code=code,
            message=message,
            retry_hint=RetryHint.REQUEST_APPROVAL,
            correlation=correlation,
        )
        result = ActionResult(
            action_id=action_id,
            status=status,
            error=error,
            correlation=correlation,
        )
        self._bus.publish(RUNTIME_ACTION_DENIED, result.to_payload(), source=self.name)

    def _on_observation_received(self, event: Event) -> None:
        payload = event.payload
        if str(payload.get("source", "")) != ObservationSource.FILESYSTEM.value:
            return
        change_type = str(payload.get("change_type", ""))
        if change_type not in {
            ObservationChangeType.CREATED.value,
            ObservationChangeType.UPDATED.value,
            ObservationChangeType.SNAPSHOT.value,
        }:
            return
        raw = dict(payload.get("raw_payload") or {})
        subject = str(payload.get("subject") or raw.get("path") or "")
        if not subject:
            return
        correlation = CorrelationContext.from_payload(payload)
        path = Path(subject)
        node = Node(
            id=f"file:{path}",
            type="resource",
            attributes={
                "resource_type": "file" if raw.get("is_file", True) else "folder",
                "path": str(path),
                "name": path.name,
                "observer_id": str(payload.get("id", "")),
            },
        )
        mutation = Mutation(
            id=f"{correlation.correlation_id}:{node.id}",
            correlation=correlation,
            type=MutationType.UPDATE_NODE,
            payload={"node": node.to_payload()},
        )
        self._execute_action(
            action_id=correlation.action_id or f"observe:{node.id}",
            payload={
                "tier": SecurityTier.READ.value,
                "mutation": mutation.to_payload(),
                "auto_approve": True,
            },
            correlation=correlation,
        )


def _parse_tier(value: object) -> SecurityTier:
    raw = str(value or SecurityTier.READ.value).strip().lower()
    try:
        return SecurityTier(raw)
    except ValueError:
        return SecurityTier.READ


def _mutation_from_payload(payload: dict, correlation: CorrelationContext) -> Mutation:
    raw_correlation = payload.get("correlation")
    if isinstance(raw_correlation, dict):
        correlation = CorrelationContext.from_payload({"correlation": raw_correlation})
    return Mutation(
        id=str(payload.get("id") or uuid.uuid4().hex),
        correlation=correlation,
        type=MutationType(str(payload.get("type") or MutationType.UPDATE_NODE.value)),
        payload=dict(payload.get("payload") or {}),
    )
