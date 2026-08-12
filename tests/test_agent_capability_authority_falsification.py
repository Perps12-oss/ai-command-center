"""Falsification tests for the ``agent.*`` capability authority boundary.

These encode invariants that the post-#176 control plane is *claimed* to hold
(``docs/audits/RUNTIME_INTEGRITY_CLOSEOUT.md`` §4: "NO bypass found") but which
are **not** covered by ``tests/test_control_plane_security_acceptance.py``.

That suite exercises the ``shell`` and ``workspace_execute_command``
capabilities — both members of ``control_plane.COMMAND_TOOL_CAPABILITIES``, and
both asserted with ``require_approval=True``. It never exercises a capability
whose label begins with ``agent.``.

``control_plane.step_requires_human_approval`` short-circuits on that prefix::

    cap = step.capability.strip().lower()
    if cap.startswith("agent."):
        return False

and ``ExecutionOrchestratorService._dispatch_agent_step`` then defaults the
dispatched tool to ``shell`` and sources the command from ``step.args`` — which
is planner/LLM-authored. The capability *label* is therefore acting as a trust
boundary while remaining attacker-selectable.

Expected on ``main`` @ a582f7c: A1, A2, B1(git forms), C1 FAIL; the rest pass.
Every test asserts the security property, so each should go green once the
boundary is keyed on the effective tool rather than the capability label.

Run only this suite::

    APPDATA=/tmp/aicc_appdata python -m pytest \
        tests/test_agent_capability_authority_falsification.py \
        -m control_plane_acceptance -p no:cacheprovider --no-cov
"""

from __future__ import annotations

import sqlite3
from typing import Any
from uuid import uuid4

import pytest

from ai_command_center.core.command_sandbox import CommandSandbox, SecurityError
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    AGENT_EXECUTION_REQUEST,
    EXECUTION_RUN_REQUEST,
    GOAL_SUBMIT_REQUEST,
    TOOL_COMPLETED,
    TOOL_CONFIRMATION_REQUIRED,
    TOOL_FAILED,
    TOOL_INVOKE,
)
from ai_command_center.core.permission.permission import Permission, PermissionContext
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
from ai_command_center.services.orchestration_service import OrchestrationService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry

pytestmark = pytest.mark.control_plane_acceptance


# ---------------------------------------------------------------------------
# Wiring helpers — mirrors tests/test_control_plane_security_acceptance.py
# ---------------------------------------------------------------------------


class _ProductionDefaultPermission:
    """Mirrors the shipped default grant for automation actors.

    ``core/permission/permission_service.py:49`` grants ``agent`` actors
    ``LAUNCH_TOOL`` out of the box. Using a deny-all stub here would hide the
    finding, so this reproduces the real default instead.
    """

    def check(self, permission: str, context: PermissionContext) -> bool:
        return permission == Permission.LAUNCH_TOOL.value


def _conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def _executed() -> list[str]:
    return []


def _wire_orchestrator_stack(
    bus: EventBus, *, permission: Any | None = None, sink: list[str] | None = None
) -> ToolRegistry:
    registry = ToolRegistry()

    def _handler(args: dict[str, Any]) -> ToolResult:
        command = str(args.get("command", ""))
        if sink is not None:
            sink.append(command)
        return ToolResult(success=True, output=command or "ok")

    for name in ("shell", "workspace_execute_command"):
        registry.register_tool(
            ToolSpec(name=name, description=name, handler=_handler)
        )
    ToolExecutorService(bus, registry, permission_service=permission).start()
    OrchestrationService(bus).start()
    ExecutionOrchestratorService(bus).start()
    return registry


def _wire_ea_stack(bus: EventBus, *, permission: Any | None = None) -> None:
    from ai_command_center.services.agent_runtime_service import AgentRuntimeService

    _wire_orchestrator_stack(bus, permission=permission)
    SingleGoalScheduler(bus, GoalRepository(_conn())).start()
    agent = AgentRuntimeService(bus)
    agent.start()
    ExecutionAuthorityService(bus, agent_runtime=agent).start()


def _collect(bus: EventBus, topic: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    bus.subscribe(topic, lambda e: events.append(dict(e.payload)))
    return events


def _agent_run(command: str, *, capability: str = "agent.shell") -> dict[str, Any]:
    """An EXECUTION_RUN_REQUEST an LLM planner could legitimately produce."""
    return {
        "run_id": f"run-agent-{uuid4().hex[:8]}",
        "actor_provenance": "agent",
        "actor_type": "agent",
        "plan": {
            "goal": "agent step",
            "steps": [
                {
                    "step_id": "s1",
                    "capability": capability,
                    # require_approval deliberately absent — agent_runtime_service.py
                    # never sets it (grep -c require_approval -> 0 hits).
                    "args": {"tool": "shell", "command": command},
                }
            ],
        },
        "workspace_context": {
            "workspace_id": str(uuid4()),
            "entity_id": str(uuid4()),
        },
    }


# ---------------------------------------------------------------------------
# A. The agent.* approval exemption
# ---------------------------------------------------------------------------


def test_a1_agent_shell_step_requires_authorization() -> None:
    """An agent.* step reaching the shell tool must still be gated.

    FALSIFIES: closeout §4 "NO bypass found".

    control_plane.step_requires_human_approval returns False for any capability
    beginning with ``agent.``, so no TOOL_CONFIRMATION_REQUIRED is published,
    and the production-default LAUNCH_TOOL grant satisfies _shell_allowed.
    """
    bus = EventBus()
    ran: list[str] = _executed()
    _wire_orchestrator_stack(bus, permission=_ProductionDefaultPermission(), sink=ran)
    confirmations = _collect(bus, TOOL_CONFIRMATION_REQUIRED)
    failed = _collect(bus, TOOL_FAILED)
    completed = _collect(bus, TOOL_COMPLETED)

    bus.publish(EXECUTION_RUN_REQUEST, _agent_run("echo pwned"), source="llm_planner")

    assert confirmations or failed, (
        "agent.shell reached the shell tool with neither a human-approval "
        "prompt nor a permission denial; the capability label alone decided "
        "the trust boundary (control_plane.py:26-28)"
    )
    assert not completed, "agent.shell executed without authorization"
    assert not ran, f"command actually executed unauthorized: {ran!r}"


@pytest.mark.parametrize(
    "provenance",
    [
        pytest.param("agent", id="agent"),
        pytest.param("llm", id="llm"),
        pytest.param("", id="unknown-empty"),
    ],
)
def test_a2_non_ui_provenance_still_gates_command_capabilities(
    provenance: str,
) -> None:
    """Human approval must not be reserved for UI-typed commands alone.

    Broader than the agent.* prefix: ``step_requires_human_approval`` returns
    True only when provenance is in UI_PROVENANCES (or interactive_user is set).
    Every other origin — agent, llm, workflow, and unknown/empty — falls through
    to ``return False`` for the plain ``shell`` capability::

        'ui'       capability=shell -> True
        'agent'    capability=shell -> False
        'llm'      capability=shell -> False
        ''         capability=shell -> False   <- unknown provenance fails OPEN

    So the ``cap.startswith("agent.")`` early-out is redundant: non-UI origins
    already skip HITL entirely, leaving PermissionService — which grants agents
    LAUNCH_TOOL by default — as the only control.
    """
    from ai_command_center.core.control_plane import step_requires_human_approval
    from ai_command_center.domain.planner_plan import PlanStep

    step = PlanStep(step_id="s1", capability="shell", args={"command": "git status"})
    assert step_requires_human_approval(step, run={"actor_provenance": provenance}), (
        f"provenance {provenance!r} bypasses human approval for the 'shell' "
        "capability; only 'ui' is gated (control_plane.py:30-36)"
    )


def test_a3_unknown_provenance_fails_closed() -> None:
    """A run with no provenance at all must not be treated as pre-authorized."""
    from ai_command_center.core.control_plane import step_requires_human_approval
    from ai_command_center.domain.planner_plan import PlanStep

    step = PlanStep(step_id="s1", capability="shell", args={"command": "git status"})
    assert step_requires_human_approval(step, run={}), (
        "a run carrying no actor_provenance skipped human approval — the "
        "default branch of step_requires_human_approval fails open"
    )


# ---------------------------------------------------------------------------
# B. Sandbox argument validation for allowlisted interpreters
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("git -c core.fsmonitor=calc status", id="git-c-fsmonitor"),
        pytest.param("git clone --upload-pack=calc host:repo", id="git-upload-pack"),
        pytest.param("git -c alias.z=!calc z", id="git-alias-bang"),
        pytest.param("python -m http.server", id="python-dash-m"),
        pytest.param("python -m pip install attacker-pkg", id="python-m-pip"),
    ],
)
def test_b1_allowlisted_interpreters_reject_code_bearing_arguments(
    command: str,
) -> None:
    """python and git take code via arguments; argv[0] allowlisting is not enough.

    command_sandbox.py:77 blocks only ``python -c`` / ``--command``. Neither
    ``python -m`` nor any git argument form is validated, and _DANGEROUS_PATTERNS
    contains no git entry. None of these strings contains a character from
    _SHELL_METACHARS, so all reach subprocess.Popen.
    """
    sandbox = CommandSandbox()
    with pytest.raises(SecurityError):
        sandbox.validate_command(command)


def test_b2_python_c_remains_blocked() -> None:
    """Regression guard for the #175 fix — must keep passing."""
    sandbox = CommandSandbox()
    with pytest.raises(SecurityError):
        sandbox.validate_command('python -c "import os"')


def test_b3_benign_allowlisted_commands_still_permitted() -> None:
    """The fix must not break ordinary allowlisted usage."""
    sandbox = CommandSandbox()
    assert sandbox.validate_command("git status")[0].lower().startswith("git")
    assert sandbox.validate_command("echo hello")[0].lower().startswith("echo")


# ---------------------------------------------------------------------------
# C. Provenance laundering via agent.task -> UI_COMMAND
# ---------------------------------------------------------------------------


def test_c1_agent_task_does_not_launder_agent_provenance_into_user_trust() -> None:
    """An agent-authored step must not acquire interactive-user identity.

    _dispatch_agent_step publishes UI_COMMAND for capability 'agent.task'
    (execution_orchestrator_service.py:580-591). ExecutionAuthorityService
    subscribes to UI_COMMAND and unconditionally stamps intake=INTAKE_UI_COMMAND
    (:217/:262/:290), which intake_run_fields maps to interactive_user=True and
    actor_type="user" — short-circuiting _shell_allowed before PermissionService
    is ever consulted.
    """
    bus = EventBus()
    _wire_ea_stack(bus, permission=_ProductionDefaultPermission())
    submits = _collect(bus, GOAL_SUBMIT_REQUEST)
    invokes = _collect(bus, TOOL_INVOKE)

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": f"run-launder-{uuid4().hex[:8]}",
            "actor_provenance": "agent",
            "actor_type": "agent",
            "plan": {
                "goal": "laundering probe",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "agent.task",
                        "args": {"task": "escalate me"},
                    }
                ],
            },
            "workspace_context": {"workspace_id": str(uuid4())},
        },
        source="llm_planner",
    )

    escalated = [
        s
        for s in submits
        if bool(s.get("interactive_user"))
        or str(s.get("actor_type", "")).lower() == "user"
        or str(s.get("actor_provenance", "")).lower() in {"ui", "ui_command"}
    ]
    assert not escalated, (
        "agent.task re-entered intake as UI_COMMAND and was stamped with "
        f"interactive-user provenance: {escalated!r}"
    )
    assert not [i for i in invokes if str(i.get("actor_type", "")) == "user"], (
        "an agent-originated run produced a TOOL_INVOKE carrying actor_type=user"
    )


def test_d1_workflow_provenance_still_dispatches_with_nonuser_actor() -> None:
    """Positive control: the exempt path must still reach dispatch.

    After the approval boundary was made fail-closed, several actor-identity
    assertions in test_control_plane_security_acceptance.py are satisfied by the
    step being *blocked*. This test keeps the identity path positively covered:
    ``workflow`` provenance is exempt from per-step HITL by design (closeout §4,
    "Workflow shell — workflow actor, LAUNCH_TOOL, no per-step HITL"), so it must
    still dispatch — and must still not dispatch as an interactive user.
    """
    bus = EventBus()
    _wire_orchestrator_stack(bus, permission=_ProductionDefaultPermission())
    invokes = _collect(bus, TOOL_INVOKE)

    run = _agent_run("echo workflow", capability="shell")
    run["actor_provenance"] = "workflow"
    run["actor_type"] = "workflow"
    bus.publish(EXECUTION_RUN_REQUEST, run, source="workflow_engine")

    assert invokes, (
        "workflow provenance is documented as exempt from per-step approval; "
        "gating it would break the documented design"
    )
    assert str(invokes[0].get("actor_type", "")) != "user", (
        "workflow run dispatched with interactive-user identity"
    )


def test_d2_interactive_user_path_still_gates_and_can_be_approved() -> None:
    """Positive control: UI-originated shell must still raise a confirmation."""
    bus = EventBus()
    _wire_orchestrator_stack(bus, permission=_ProductionDefaultPermission())
    confirmations = _collect(bus, TOOL_CONFIRMATION_REQUIRED)

    run = _agent_run("echo hello", capability="shell")
    run["actor_provenance"] = "ui"
    run["interactive_user"] = True
    bus.publish(EXECUTION_RUN_REQUEST, run, source="ui")

    assert confirmations, "interactive shell must still prompt for confirmation"


def test_c2_agent_execution_request_intake_stays_agent() -> None:
    """The legitimate AGENT_EXECUTION_REQUEST intake must stamp agent provenance.

    Control test for C1 — this path is expected to be correct today.
    """
    bus = EventBus()
    _wire_ea_stack(bus, permission=_ProductionDefaultPermission())
    submits = _collect(bus, GOAL_SUBMIT_REQUEST)

    bus.publish(
        AGENT_EXECUTION_REQUEST,
        {
            "request_id": str(uuid4()),
            "task": "do a thing",
            "spawn_role": "research",
            "workspace_id": str(uuid4()),
        },
        source="agent_runtime",
    )

    assert submits, "AGENT_EXECUTION_REQUEST produced no GOAL_SUBMIT_REQUEST"
    for payload in submits:
        assert not bool(payload.get("interactive_user")), payload
        assert str(payload.get("actor_type", "")).lower() != "user", payload
