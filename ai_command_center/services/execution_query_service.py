"""ExecutionQueryService — reads execution run metadata and publishes results.

Subscribes to execution.query.request and publishes execution.query.result.
Reads ExecutionRunRepository and ExecutionEventRepository via ReplayRunner.

Architecture contract
─────────────────────
• Does NOT call other services directly (Rule 3).
• Publishes EXECUTION_QUERY_RESULT on the bus for AppState to reduce.
• Uses base_service.py lifecycle (STOPPED → STARTING → READY).
"""
from __future__ import annotations

import logging
from collections.abc import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_QUERY_REQUEST,
    EXECUTION_QUERY_RESULT,
)
from ai_command_center.orchestration.replay.replay_runner import ReplayRunner
from ai_command_center.repositories.execution_event_repository import ExecutionEventRepository
from ai_command_center.repositories.execution_run_repository import ExecutionRunRepository
from ai_command_center.services.base import BaseService

logger = logging.getLogger(__name__)


class ExecutionQueryService(BaseService):
    """Handles execution.query.request and returns enriched run metadata."""

    name = "execution_query"

    def __init__(
        self,
        bus: EventBus,
        *,
        run_repo: ExecutionRunRepository,
        event_repo: ExecutionEventRepository | None = None,
    ) -> None:
        super().__init__(bus)
        self._run_repo = run_repo
        self._replay = ReplayRunner(run_repo, event_repo=event_repo)
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(EXECUTION_QUERY_REQUEST, self._handle_query)
        )
        logger.info("[ExecutionQueryService] ready")

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _handle_query(self, event: Event) -> None:
        payload = dict(event.payload) if event.payload else {}
        request_id = str(payload.get("request_id", "")).strip()
        if not request_id:
            return

        timeline = self._replay.build_timeline(request_id)
        trace_spans: list[dict] = []
        for index, stage in enumerate(timeline.stages):
            parent_id = ""
            if index > 0 and timeline.stages[index - 1].event_id:
                parent_id = timeline.stages[index - 1].event_id
            trace_spans.append(
                {
                    "span_id": stage.event_id or f"{request_id}:{stage.stage}:{index}",
                    "parent_id": parent_id,
                    "name": stage.stage,
                    "kind": stage.source,
                    "status": "ok",
                    "duration_ms": 0.0,
                    "started_at": stage.created_at,
                    "attributes": stage.detail,
                }
            )

        provider_id = str(payload.get("provider_id", ""))
        model = str(payload.get("model", ""))
        if timeline.provider_ids:
            provider_id = provider_id or timeline.provider_ids[-1]

        for run in self._run_repo.list_by_request(request_id):
            snap = run.snapshot
            provider_id = provider_id or str(snap.get("provider_id", ""))
            model = model or str(snap.get("model", ""))

        execution_events = [
            event.to_bus_payload() for event in timeline.events
        ]

        result_payload: dict = {
            "request_id": request_id,
            "provider_id": provider_id,
            "model": model,
            "status": str(payload.get("status", "idle")),
            "intent": str(payload.get("intent", "")),
            "query": str(payload.get("query", "")),
            "response_source": str(payload.get("response_source", "")),
            "truth_valid": bool(payload.get("truth_valid", False)),
            "truth_detail": str(payload.get("truth_detail", "")),
            "trace_id": timeline.trace_id,
            "span_id": timeline.span_id,
            "trace_spans": trace_spans,
            "artifacts": payload.get("artifacts") or [],
            "metrics": payload.get("metrics") or {},
            "execution_events": execution_events,
            "timeline_source": timeline.source,
        }
        self._bus.publish(
            EXECUTION_QUERY_RESULT,
            result_payload,
            source=self.name,
        )
