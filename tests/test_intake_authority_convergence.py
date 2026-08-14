"""B1/B2 — every ExecutionAuthority intake must decide identically.

At baseline only UI_COMMAND published EXECUTION_AUTHORITY_DECISION and only
UI_COMMAND applied the workspace admission gate. Workflow and agent intakes
reached the scheduler with no observable authority decision.
"""

from __future__ import annotations

from ai_command_center.core.contracts import (
    INTAKE_AGENT,
    INTAKE_UI_COMMAND,
    INTAKE_WORKFLOW,
)
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    AGENT_EXECUTION_REQUEST,
    COMMAND_DEFERRED,
    EXECUTION_AUTHORITY_DECISION,
    GOAL_SUBMIT_REQUEST,
    UI_COMMAND,
    WORKFLOW_EXECUTION_REQUEST,
    WORKSPACE_ACTIVE,
)
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService

_REQUIRED_DECISION_FIELDS = frozenset(
    {"request_id", "intake", "kind", "text", "capability", "args", "reason",
     "skip_planner", "state_context"}
)


def _authority(bus: EventBus) -> ExecutionAuthorityService:
    service = ExecutionAuthorityService(bus)
    service.start()
    return service


def _capture(bus: EventBus) -> tuple[list[dict], list[dict], list[dict]]:
    decisions: list[dict] = []
    goals: list[dict] = []
    deferred: list[dict] = []
    bus.subscribe(EXECUTION_AUTHORITY_DECISION, lambda e: decisions.append(dict(e.payload)))
    bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: goals.append(dict(e.payload)))
    bus.subscribe(COMMAND_DEFERRED, lambda e: deferred.append(dict(e.payload)))
    return decisions, goals, deferred


_WORKFLOW_PAYLOAD = {
    "run_id": "wf-conv",
    "workflow_id": "demo",
    "steps": [{"id": "a", "type": "tool", "tool": "shell", "args": {"command": "echo 1"}}],
}
_AGENT_PAYLOAD = {"agent_id": "ag-1", "request_id": "ag-conv", "task": "do the thing"}


def test_workflow_intake_publishes_authority_decision() -> None:
    bus = EventBus()
    _authority(bus)
    decisions, goals, _ = _capture(bus)

    bus.publish(WORKFLOW_EXECUTION_REQUEST, dict(_WORKFLOW_PAYLOAD), source="test")

    assert decisions, "workflow intake published no EXECUTION_AUTHORITY_DECISION"
    assert decisions[0]["capability"] == "workflow"
    assert decisions[0]["kind"] == "actionable"
    assert decisions[0]["intake"] == INTAKE_WORKFLOW
    assert decisions[0]["request_id"] == "wf-conv"
    assert goals, "workflow must still reach the scheduler"


def test_agent_intake_publishes_authority_decision() -> None:
    bus = EventBus()
    _authority(bus)
    decisions, goals, _ = _capture(bus)

    bus.publish(AGENT_EXECUTION_REQUEST, dict(_AGENT_PAYLOAD), source="test")

    assert decisions, "agent intake published no EXECUTION_AUTHORITY_DECISION"
    assert decisions[0]["capability"] == "agent.shell"
    assert decisions[0]["intake"] == INTAKE_AGENT
    assert decisions[0]["request_id"] == "ag-conv"
    assert goals, "agent must still reach the scheduler"


def test_all_intakes_emit_the_same_decision_field_set() -> None:
    """The equivalence test whose absence let the divergence survive."""
    seen: dict[str, set[str]] = {}

    for label, topic, payload, needs_ws in (
        (INTAKE_UI_COMMAND, UI_COMMAND, {"text": "What is Python?"}, True),
        (INTAKE_WORKFLOW, WORKFLOW_EXECUTION_REQUEST, dict(_WORKFLOW_PAYLOAD), False),
        (INTAKE_AGENT, AGENT_EXECUTION_REQUEST, dict(_AGENT_PAYLOAD), False),
    ):
        bus = EventBus()
        _authority(bus)
        decisions, _, _ = _capture(bus)
        if needs_ws:
            bus.publish(WORKSPACE_ACTIVE, {"workspace_id": "ws-1"}, source="test")
        bus.publish(topic, payload, source="test")
        assert decisions, f"{label} intake published no decision"
        assert decisions[0]["intake"] == label
        seen[label] = set(decisions[0]) - {"workspace_id"}

    field_sets = list(seen.values())
    assert all(fields == field_sets[0] for fields in field_sets), (
        "intakes emit different decision fields: "
        + " | ".join(f"{k}={sorted(v)}" for k, v in seen.items())
    )
    assert _REQUIRED_DECISION_FIELDS <= field_sets[0], (
        f"decision missing required fields: {sorted(_REQUIRED_DECISION_FIELDS - field_sets[0])}"
    )


def test_workflow_proceeds_without_active_workspace() -> None:
    """B-D1a(A): `workflow` is workspace-optional, so it must not defer."""
    bus = EventBus()
    _authority(bus)
    _, goals, deferred = _capture(bus)

    bus.publish(WORKFLOW_EXECUTION_REQUEST, dict(_WORKFLOW_PAYLOAD), source="test")

    assert goals, "workflow deferred without a workspace — exemption not applied"
    assert not deferred


def test_agent_proceeds_without_active_workspace_on_every_intake() -> None:
    """B-D1a(A): the gate is keyed on capability, so both doors admit alike.

    This documents a deliberate supersession: UI agent commands deferred before
    Phase B. See docs/audits/GATE_SUPERSESSION_WORKSPACE_REQUIRED_AGENT.md.
    """
    for topic, payload in (
        (AGENT_EXECUTION_REQUEST, dict(_AGENT_PAYLOAD)),
        (UI_COMMAND, {"text": "agent: demo"}),
    ):
        bus = EventBus()
        _authority(bus)
        _, goals, deferred = _capture(bus)
        bus.publish(topic, payload, source="test")
        assert not deferred, f"{topic} deferred an agent capability without a workspace"
        assert goals, f"{topic} produced no GOAL_SUBMIT_REQUEST"


def test_non_exempt_capability_still_defers_without_workspace() -> None:
    """Guards against an over-broad exemption — `shell` must keep deferring."""
    bus = EventBus()
    _authority(bus)
    _, goals, deferred = _capture(bus)

    bus.publish(UI_COMMAND, {"text": "> echo hello"}, source="test")

    assert deferred, "shell must still defer without an active workspace"
    assert deferred[0]["intent"] == "shell"
    assert not goals


def test_workflow_defers_nothing_but_shell_still_gated_via_workflow_steps() -> None:
    """A workflow whose steps are shell tools is admitted as capability `workflow`.

    The gate keys on the decision capability, not on the tools inside the plan;
    this pins that intended semantics so a future change cannot drift silently.
    """
    bus = EventBus()
    _authority(bus)
    _, goals, deferred = _capture(bus)

    bus.publish(WORKFLOW_EXECUTION_REQUEST, dict(_WORKFLOW_PAYLOAD), source="test")

    assert goals and not deferred
    assert goals[0]["authority_decision"]["capability"] == "workflow"


def test_convergence_preserves_downstream_contract() -> None:
    """GOAL_SUBMIT_REQUEST still carries authority_decision for every intake."""
    for topic, payload in (
        (WORKFLOW_EXECUTION_REQUEST, dict(_WORKFLOW_PAYLOAD)),
        (AGENT_EXECUTION_REQUEST, dict(_AGENT_PAYLOAD)),
    ):
        bus = EventBus()
        _authority(bus)
        _, goals, _ = _capture(bus)
        bus.publish(topic, payload, source="test")
        assert goals, f"{topic} produced no GOAL_SUBMIT_REQUEST"
        assert goals[0].get("authority_decision", {}).get("capability")
        assert goals[0].get("plan", {}).get("steps")
