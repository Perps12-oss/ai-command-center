"""B4 — a workflow that cannot execute must fail explicitly, never stall.

At baseline a manifest whose steps are all non-executable passed the engine's
gates, registered a run, published WORKFLOW_STARTED, then had every step dropped
by ExecutionAuthority — leaving a registered run with no terminal event.
"""

from __future__ import annotations

from ai_command_center.core.contracts import is_executable_workflow_step
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    WORKFLOW_EXECUTION_REQUEST,
    WORKFLOW_FAILED,
    WORKFLOW_START,
    WORKFLOW_STARTED,
)
from ai_command_center.services.workflow_engine_service import WorkflowEngineService


def _engine(bus: EventBus) -> WorkflowEngineService:
    service = WorkflowEngineService(bus)
    service.start()
    return service


def _capture(bus: EventBus) -> tuple[list[dict], list[dict], list[dict]]:
    failed: list[dict] = []
    started: list[dict] = []
    handed_off: list[dict] = []
    bus.subscribe(WORKFLOW_FAILED, lambda e: failed.append(dict(e.payload)))
    bus.subscribe(WORKFLOW_STARTED, lambda e: started.append(dict(e.payload)))
    bus.subscribe(WORKFLOW_EXECUTION_REQUEST, lambda e: handed_off.append(dict(e.payload)))
    return failed, started, handed_off


def test_workflow_with_only_non_tool_steps_fails_explicitly() -> None:
    bus = EventBus()
    engine = _engine(bus)
    failed, started, handed_off = _capture(bus)

    bus.publish(
        WORKFLOW_START,
        {
            "run_id": "wf-nontool",
            "workflow_id": "demo",
            "steps": [
                {"id": "a", "type": "decision", "tool": "shell"},
                {"id": "b", "type": "note", "tool": "shell"},
            ],
        },
        source="test",
    )

    assert failed, "non-executable workflow produced no WORKFLOW_FAILED — stuck run"
    assert failed[0]["run_id"] == "wf-nontool"
    assert "no executable tool steps" in failed[0]["error"]
    assert not started, "must not announce a workflow it cannot run"
    assert not handed_off, "must not hand off a manifest with no executable steps"
    assert engine._runs == {}, "failed workflow must leave no registered run"


def test_workflow_with_blank_tool_names_fails_explicitly() -> None:
    bus = EventBus()
    engine = _engine(bus)
    failed, started, _ = _capture(bus)

    bus.publish(
        WORKFLOW_START,
        {
            "run_id": "wf-blank",
            "workflow_id": "demo",
            "steps": [
                {"id": "a", "type": "tool", "tool": ""},
                {"id": "b", "type": "tool", "tool": "   "},
            ],
        },
        source="test",
    )

    assert failed, "blank tool names produced no WORKFLOW_FAILED — stuck run"
    assert not started
    assert engine._runs == {}


def test_mixed_valid_and_invalid_steps_still_runs() -> None:
    """Drop-and-continue is preserved: one good step is enough to proceed."""
    bus = EventBus()
    _engine(bus)
    failed, started, handed_off = _capture(bus)

    bus.publish(
        WORKFLOW_START,
        {
            "run_id": "wf-mixed",
            "workflow_id": "demo",
            "steps": [
                {"id": "a", "type": "decision", "tool": "shell"},
                {"id": "b", "type": "tool", "tool": "shell", "args": {"command": "echo 1"}},
            ],
        },
        source="test",
    )

    assert not failed, "a workflow with one executable step must not fail"
    assert started, "expected WORKFLOW_STARTED"
    assert handed_off, "expected hand-off to ExecutionAuthority"


def test_executable_step_predicate_matches_intake_semantics() -> None:
    """The shared predicate (Inv 11) must keep ExecutionAuthority's exact rules."""
    assert is_executable_workflow_step({"tool": "shell"}), "missing type defaults to tool"
    assert is_executable_workflow_step({"type": "tool", "tool": "shell"})
    assert not is_executable_workflow_step({"type": "decision", "tool": "shell"})
    assert not is_executable_workflow_step({"type": "tool", "tool": "  "})
    assert not is_executable_workflow_step({"type": "tool"})
    assert not is_executable_workflow_step("not-a-dict")
    assert not is_executable_workflow_step(None)
