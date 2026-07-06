"""Headless read-only replay visualization for execution runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_command_center.domain.execution_run import ExecutionRun
from ai_command_center.repositories.execution_run_repository import ExecutionRunRepository


@dataclass(frozen=True, slots=True)
class ReplayStage:
    """Single stage in a replay timeline."""

    stage: str
    source: str
    request_id: str
    created_at: float
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ReplayTimeline:
    """Read-only visualization of an execution run sequence."""

    request_id: str
    stages: tuple[ReplayStage, ...] = ()
    provider_ids: tuple[str, ...] = ()
    trace_id: str = ""
    span_id: str = ""


class ReplayRunner:
    """Builds replay timelines from persisted execution runs (read-only)."""

    def __init__(self, repo: ExecutionRunRepository) -> None:
        self._repo = repo

    def build_timeline(self, request_id: str) -> ReplayTimeline:
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
        )

    def list_runs(self, request_id: str) -> list[ExecutionRun]:
        return self._repo.list_by_request(request_id)
