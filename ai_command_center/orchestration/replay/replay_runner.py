"""Headless read-only replay visualization for execution runs and events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_command_center.domain.execution_event import ExecutionEvent
from ai_command_center.domain.execution_run import ExecutionRun
from ai_command_center.repositories.execution_event_repository import ExecutionEventRepository
from ai_command_center.repositories.execution_run_repository import ExecutionRunRepository


@dataclass(frozen=True, slots=True)
class ReplayStage:
    """Single stage in a replay timeline."""

    stage: str
    source: str
    request_id: str
    created_at: float
    detail: dict[str, Any] = field(default_factory=dict)
    event_id: str = ""


@dataclass(frozen=True, slots=True)
class ReplayTimeline:
    """Read-only visualization of an execution run sequence."""

    request_id: str
    stages: tuple[ReplayStage, ...] = ()
    provider_ids: tuple[str, ...] = ()
    trace_id: str = ""
    span_id: str = ""
    source: str = "runs"
    events: tuple[ExecutionEvent, ...] = ()


class ReplayRunner:
    """Builds replay timelines from execution events, falling back to execution runs."""

    def __init__(
        self,
        run_repo: ExecutionRunRepository,
        *,
        event_repo: ExecutionEventRepository | None = None,
    ) -> None:
        self._repo = run_repo
        self._event_repo = event_repo

    @property
    def _run_repo(self) -> ExecutionRunRepository:
        return self._repo

    def build_timeline(self, request_id: str) -> ReplayTimeline:
        if self._event_repo is not None:
            events = self._event_repo.list_by_request(request_id)
            if events:
                return self._build_from_events(request_id, events)
        return self._build_from_runs(request_id)

    def list_events(self, request_id: str) -> list[ExecutionEvent]:
        if self._event_repo is None:
            return []
        return self._event_repo.list_by_request(request_id)

    def _build_from_events(
        self,
        request_id: str,
        events: list[ExecutionEvent],
    ) -> ReplayTimeline:
        stages: list[ReplayStage] = []
        trace_id = ""
        for event in events:
            trace_id = event.trace_id or trace_id
            stage_name = event.scope or event.event_type.split(".")[-1] or event.event_type
            stages.append(
                ReplayStage(
                    stage=stage_name,
                    source=event.actor or event.event_type,
                    request_id=request_id,
                    created_at=event.timestamp,
                    detail=event.payload_dict(),
                    event_id=event.event_id,
                )
            )
        return ReplayTimeline(
            request_id=request_id,
            stages=tuple(stages),
            provider_ids=(),
            trace_id=trace_id,
            span_id="",
            source="events",
            events=tuple(events),
        )

    def _build_from_runs(self, request_id: str) -> ReplayTimeline:
        runs = self._repo.list_by_request(request_id)
        stages: list[ReplayStage] = []
        providers: list[str] = []
        trace_id = ""
        span_id = ""
        for run in runs:
            snapshot = run.snapshot
            provider_id = str(snapshot.get("provider_id", ""))
            if provider_id:
                providers.append(provider_id)
            trace_id = str(snapshot.get("trace_id", trace_id))
            span_id = str(snapshot.get("span_id", span_id))
            stage_name = run.source
            if run.source == "orchestration":
                stage_name = str(snapshot.get("intent", "orchestration"))
            stages.append(
                ReplayStage(
                    stage=stage_name,
                    source=run.source,
                    request_id=run.request_id,
                    created_at=run.created_at,
                    detail=dict(snapshot),
                )
            )
        return ReplayTimeline(
            request_id=request_id,
            stages=tuple(stages),
            provider_ids=tuple(dict.fromkeys(providers)),
            trace_id=trace_id,
            span_id=span_id,
            source="runs",
            events=(),
        )

    def list_runs(self, request_id: str) -> list[ExecutionRun]:
        return self._repo.list_by_request(request_id)
