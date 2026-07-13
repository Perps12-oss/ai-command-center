"""OperationIndexerService — indexes operations by correlation_id from EventBus events.

Responsibilities:
- Subscribe to goal/execution/agent lifecycle events.
- Upsert operation_index rows from event payloads (no cross-repository reads during indexing).
- Handle OPERATION_LOAD_REQUEST by reconstructing OperationSnapshot from repositories.
- Publish OPERATION_SAVED, OPERATION_LOADED, OPERATION_ARCHIVED.

Invariants enforced:
- Invariant 3: all reads/writes via EventBus or injected repositories.
- Invariant 5: OperationIndexRepository is the sole owner of operation_index storage.
- Invariant 8: all emitted topics are registered in topics.py.
"""

from __future__ import annotations

import time
from typing import Any

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import (
    AGENT_SPAWNED,
    AGENT_TASK_COMPLETE,
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    EXECUTION_RUN_STARTED,
    GOAL_ACTIVATED,
    GOAL_CANCELLED,
    GOAL_COMPLETED,
    GOAL_FAILED,
    GOAL_SUBMITTED,
    OPERATION_ARCHIVED,
    OPERATION_LOAD_REQUEST,
    OPERATION_LOADED,
    OPERATION_SAVED,
)
from ai_command_center.services.base import BaseService
from ai_command_center.domain.operation_snapshot import OperationSnapshot
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.repositories.operation_index_repository import (
    OperationIndexRepository,
)

_RECONSTRUCTION_TIMEOUT_S = 3.0


class OperationIndexerService(BaseService):
    """Indexes and reconstructs operations by correlation_id."""

    name = "operation_indexer"

    def __init__(
        self,
        bus: EventBus,
        *,
        op_repo: OperationIndexRepository,
        goal_repo: GoalRepository,
    ) -> None:
        super().__init__(bus)
        self._op_repo = op_repo
        self._goal_repo = goal_repo
        self._unsubs: list = []

    def _on_load(self) -> None:
        sub = self._bus.subscribe
        self._unsubs = [
            sub(GOAL_SUBMITTED, self._handle_goal_event),
            sub(GOAL_ACTIVATED, self._handle_goal_event),
            sub(GOAL_COMPLETED, self._handle_goal_event),
            sub(GOAL_FAILED, self._handle_goal_event),
            sub(GOAL_CANCELLED, self._handle_goal_event),
            sub(EXECUTION_RUN_STARTED, self._handle_execution_event),
            sub(EXECUTION_RUN_COMPLETE, self._handle_execution_event),
            sub(EXECUTION_RUN_FAILED, self._handle_execution_event),
            sub(AGENT_SPAWNED, self._handle_agent_event),
            sub(AGENT_TASK_COMPLETE, self._handle_agent_event),
            sub(OPERATION_LOAD_REQUEST, self._handle_load_request),
        ]

    def _on_unload(self) -> None:
        for unsub in self._unsubs:
            try:
                unsub()
            except Exception:
                pass
        self._unsubs.clear()

    def _handle_goal_event(self, event: Event) -> None:
        payload = event.payload
        correlation_id = str(payload.get("correlation_id", ""))
        if not correlation_id:
            return
        existing = self._op_repo.get(correlation_id)
        goal_data: dict[str, Any] = payload.get("goal") or payload  # type: ignore[assignment]
        status = str(goal_data.get("status", payload.get("status", "")))
        started = existing.started_at if existing else 0.0
        completed = existing.completed_at if existing else 0.0
        if not started and status in ("active", "queued"):
            started = time.time()
        if not completed and status in ("complete", "failed", "cancelled"):
            completed = time.time()
        snapshot = OperationSnapshot(
            correlation_id=correlation_id,
            goal_id=str(goal_data.get("id", existing.goal_id if existing else "")),
            goal_title=str(goal_data.get("title", existing.goal_title if existing else "")),
            goal_status=status or (existing.goal_status if existing else "unknown"),
            goal_priority=str(goal_data.get("priority", existing.goal_priority if existing else "normal")),
            started_at=started,
            completed_at=completed,
            agent_ids=existing.agent_ids if existing else (),
            execution_ids=existing.execution_ids if existing else (),
            tags=existing.tags if existing else (),
        )
        self._op_repo.upsert(snapshot)
        self._bus.publish(
            OPERATION_SAVED,
            {
                "correlation_id": correlation_id,
                "goal_id": snapshot.goal_id,
                "goal_title": snapshot.goal_title,
                "goal_status": snapshot.goal_status,
            },
            source=self.name,
        )

    def _handle_execution_event(self, event: Event) -> None:
        payload = event.payload
        correlation_id = str(payload.get("correlation_id", ""))
        if not correlation_id:
            return
        existing = self._op_repo.get(correlation_id)
        run_id = str(payload.get("run_id", payload.get("request_id", "")))
        if not run_id:
            return
        current_ids = set(existing.execution_ids if existing else ())
        current_ids.add(run_id)
        snapshot = OperationSnapshot(
            correlation_id=correlation_id,
            goal_id=existing.goal_id if existing else "",
            goal_title=existing.goal_title if existing else "",
            goal_status=existing.goal_status if existing else "unknown",
            goal_priority=existing.goal_priority if existing else "normal",
            started_at=existing.started_at if existing else 0.0,
            completed_at=existing.completed_at if existing else 0.0,
            agent_ids=existing.agent_ids if existing else (),
            execution_ids=tuple(sorted(current_ids)),
            tags=existing.tags if existing else (),
        )
        self._op_repo.upsert(snapshot)

    def _handle_agent_event(self, event: Event) -> None:
        payload = event.payload
        correlation_id = str(payload.get("correlation_id", ""))
        if not correlation_id:
            return
        existing = self._op_repo.get(correlation_id)
        agent_id = str(payload.get("agent_id", payload.get("agent_run_id", "")))
        if not agent_id:
            return
        current_ids = set(existing.agent_ids if existing else ())
        current_ids.add(agent_id)
        snapshot = OperationSnapshot(
            correlation_id=correlation_id,
            goal_id=existing.goal_id if existing else "",
            goal_title=existing.goal_title if existing else "",
            goal_status=existing.goal_status if existing else "unknown",
            goal_priority=existing.goal_priority if existing else "normal",
            started_at=existing.started_at if existing else 0.0,
            completed_at=existing.completed_at if existing else 0.0,
            agent_ids=tuple(sorted(current_ids)),
            execution_ids=existing.execution_ids if existing else (),
            tags=existing.tags if existing else (),
        )
        self._op_repo.upsert(snapshot)

    def _handle_load_request(self, event: Event) -> None:
        payload = event.payload
        correlation_id = str(payload.get("correlation_id", ""))
        if not correlation_id:
            return
        archive = self._op_repo.get_archive(correlation_id)
        if archive is not None:
            self._bus.publish(
                OPERATION_LOADED,
                {"correlation_id": correlation_id, "snapshot": archive.to_dict()},
                source=self.name,
            )
            return
        deadline = time.monotonic() + _RECONSTRUCTION_TIMEOUT_S
        index_entry = self._op_repo.get(correlation_id)
        goal = None
        if time.monotonic() < deadline:
            try:
                goal = self._goal_repo.get_by_correlation(correlation_id)
            except Exception:
                pass
        snapshot = OperationSnapshot(
            correlation_id=correlation_id,
            goal_id=goal.id if goal else (index_entry.goal_id if index_entry else ""),
            goal_title=goal.title if goal else (index_entry.goal_title if index_entry else ""),
            goal_status=goal.status.value if goal else (index_entry.goal_status if index_entry else "unknown"),
            goal_priority=goal.priority.value if goal else (index_entry.goal_priority if index_entry else "normal"),
            started_at=index_entry.started_at if index_entry else 0.0,
            completed_at=index_entry.completed_at if index_entry else 0.0,
            agent_ids=index_entry.agent_ids if index_entry else (),
            execution_ids=index_entry.execution_ids if index_entry else (),
            is_partial=time.monotonic() >= deadline,
        )
        self._bus.publish(
            OPERATION_LOADED,
            {"correlation_id": correlation_id, "snapshot": snapshot.to_dict()},
            source=self.name,
        )

    def archive_operation(self, correlation_id: str) -> None:
        """Operator-triggered archive — freezes the current index entry immutably."""
        snapshot = self._op_repo.get(correlation_id)
        if snapshot is None:
            return
        self._op_repo.archive(snapshot)
        self._bus.publish(
            OPERATION_ARCHIVED,
            {"correlation_id": correlation_id, "frozen_at": time.time()},
            source=self.name,
        )
