"""ADR-022 Gate 4 — autonomy bands and escalate-only (autonomy_escalation)."""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    AUTONOMY_SCORE_UPDATED,
    DECISION_RECORD_UPDATED,
    EXECUTION_RUN_FAILED,
    EXECUTION_RUN_REQUEST,
    EXECUTION_STEP_AWAITING_APPROVAL,
    TOOL_INVOKE,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.domain.autonomy_score import AutonomyScore, confidence_band
from ai_command_center.domain.planner_plan import ExecutionPlan, PlanStep
from ai_command_center.services.execution_orchestrator_service import ExecutionOrchestratorService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry
from tests.support.shell_confirmation import TRUSTED_UI_RUN


def test_autonomy_escalation_band_fixtures() -> None:
    assert confidence_band(0.39) == "high"
    assert confidence_band(0.40) == "medium"
    assert confidence_band(0.69) == "medium"
    assert confidence_band(0.70) == "low"
    high = AutonomyScore.compute(
        policy_confidence=0.39,
        evidence_confidence=0.39,
        verification_confidence=0.39,
        execution_confidence=0.39,
    )
    assert high.band == "high"
    assert high.escalate
    med = AutonomyScore.compute(
        policy_confidence=0.5,
        evidence_confidence=0.5,
        verification_confidence=0.5,
        execution_confidence=0.5,
    )
    assert med.band == "medium"
    assert not med.escalate
    low = AutonomyScore.compute(
        policy_confidence=0.9,
        evidence_confidence=0.9,
        verification_confidence=0.9,
        execution_confidence=0.9,
    )
    assert low.band == "low"
    assert not low.escalate


def test_autonomy_escalation_high_pauses_not_denies() -> None:
    bus = EventBus()
    awaiting: list[dict] = []
    failed: list[dict] = []
    scores: list[dict] = []
    bus.subscribe(EXECUTION_STEP_AWAITING_APPROVAL, lambda e: awaiting.append(dict(e.payload)))
    bus.subscribe(EXECUTION_RUN_FAILED, lambda e: failed.append(dict(e.payload)))
    bus.subscribe(AUTONOMY_SCORE_UPDATED, lambda e: scores.append(dict(e.payload)))
    orch = ExecutionOrchestratorService(bus)
    orch.start()
    plan = ExecutionPlan(
        goal="search",
        steps=(PlanStep(step_id="s1", capability="notes.search", args={"query": "x"}),),
    )
    orch._runs["run-high"] = {
        "request_id": "req-high",
        "correlation": {},
        "plan": plan,
        "index": 0,
        "observations": [{"success": False, "error": "stale"}],
        "step_outputs": [],
        "workspace_context": {},
        "truth_valid": False,
        "paused": False,
    }
    orch._advance_run("run-high")
    assert awaiting, "HIGH must HITL, not skip"
    assert not failed, "low confidence must not independently deny"
    assert scores
    assert scores[-1]["band"] == "high"
    assert scores[-1]["escalate"] is True


def test_autonomy_escalation_medium_extra_verification() -> None:
    bus = EventBus()
    records: list[dict] = []
    bus.subscribe(DECISION_RECORD_UPDATED, lambda e: records.append(dict(e.payload)))

    def _empty(_args: object) -> ToolResult:
        return ToolResult(success=True, output="", error="")

    registry = ToolRegistry()
    registry.register_tool(ToolSpec(name="notes.search", description="search", handler=_empty))
    ToolExecutorService(bus, registry).start()
    ExecutionOrchestratorService(bus).start()
    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            **TRUSTED_UI_RUN,
            "run_id": "run-med",
            "auto_approve": True,
            "plan": {
                "goal": "search",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "notes.search",
                        "args": {"query": "x"},
                        "require_approval": False,
                    }
                ],
            },
        },
        source="test",
    )
    completed = [r for r in records if str(r.get("summary", "")).startswith("step completed")]
    assert completed
    verification = completed[-1]["verification"]
    assert verification.get("source") == "truth_boundary_equivalent"
    assert verification.get("valid") is False
    assert "ungrounded" in str(verification.get("detail", ""))


def test_autonomy_escalation_write_destroy_hitl_on_low_band() -> None:
    bus = EventBus()
    awaiting: list[dict] = []
    invokes: list[dict] = []
    bus.subscribe(EXECUTION_STEP_AWAITING_APPROVAL, lambda e: awaiting.append(dict(e.payload)))
    bus.subscribe(TOOL_INVOKE, lambda e: invokes.append(dict(e.payload)))
    ExecutionOrchestratorService(bus).start()
    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            **TRUSTED_UI_RUN,
            "run_id": "run-wd",
            "plan": {
                "goal": "shell",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "shell",
                        "args": {"command": "echo hi"},
                        "require_approval": False,
                    }
                ],
            },
        },
        source="test",
    )
    assert awaiting, "WRITE_DESTROY remains HITL regardless of band"
    assert invokes == [], "must not dispatch shell before approval"


def test_autonomy_escalation_no_execution_authority_bypass() -> None:
    from pathlib import Path

    text = Path("ai_command_center/services/execution_orchestrator_service.py").read_text(
        encoding="utf-8"
    )
    assert "ExecutionAuthorityService" not in text
    assert "execution_authority" not in text
    domain = Path("ai_command_center/domain/autonomy_score.py").read_text(encoding="utf-8")
    assert "ExecutionAuthority" not in domain
