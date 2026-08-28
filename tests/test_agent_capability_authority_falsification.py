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
from ai_command_center.core.security_policy import (
    READONLY_SHELL_ALLOWLIST,
    READONLY_SHELL_TOOL,
    SecurityTier,
    resolve_tool_tier,
)
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


class _DenyAllPermission:
    """Actor authorized for nothing — proves permission is independent of tier."""

    def check(self, permission: str, context: PermissionContext) -> bool:
        return False


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

    for name in ("shell", "workspace_execute_command", READONLY_SHELL_TOOL):
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
    sandbox = CommandSandbox(allowlist=frozenset({"python", "echo"}))
    with pytest.raises(SecurityError):
        sandbox.validate_command('python -c "import os"')


def test_b3_benign_allowlisted_commands_still_permitted() -> None:
    """The fix must not break ordinary allowlisted usage."""
    sandbox = CommandSandbox()
    assert sandbox.validate_command("git status")[0].lower().startswith("git")
    assert sandbox.validate_command("echo hello")[0].lower().startswith("echo")


def test_b3b_git_config_and_python_script_rejected() -> None:
    """Audit B8 — approved-looking commands must not grant deferred execution."""
    sandbox = CommandSandbox()
    with pytest.raises(SecurityError):
        sandbox.validate_command("git config --global core.fsmonitor calc")
    with pytest.raises(SecurityError):
        sandbox.validate_command("git config alias.x !calc")
    with pytest.raises(SecurityError):
        sandbox.validate_command("python some_script.py")
    with pytest.raises(SecurityError):
        sandbox.validate_command("git -C /tmp status")


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


def test_d1_authorized_agent_executes_bounded_read_without_hitl() -> None:
    """PROOF 1 (safe read): agent -> bounded READ -> authorized -> no HITL -> executes.

    Re-authored for the tier model. The prior version asserted that ``workflow``
    provenance was exempt from HITL — a provenance-based rule ADR-004 does not
    grant. Under ADR-004 the exemption belongs to the *tier*, so the positive
    control is now a genuinely READ-classified capability.
    """
    bus = EventBus()
    ran: list[str] = _executed()
    _wire_orchestrator_stack(bus, permission=_ProductionDefaultPermission(), sink=ran)
    confirmations = _collect(bus, TOOL_CONFIRMATION_REQUIRED)
    completed = _collect(bus, TOOL_COMPLETED)

    run = _agent_run("echo agent-ok")
    run["plan"]["steps"][0]["args"]["tool"] = READONLY_SHELL_TOOL
    bus.publish(EXECUTION_RUN_REQUEST, run, source="llm_planner")

    assert not confirmations, "a READ-classified action must not demand approval"
    assert completed, "authorized agent READ action must execute"
    assert ran == ["echo agent-ok"], f"expected the bounded command to run, got {ran!r}"


def test_d2_bounded_read_tool_cannot_reach_an_interpreter() -> None:
    """The READ classification is only defensible if the tool stays bounded."""
    sandbox = CommandSandbox(allowlist=READONLY_SHELL_ALLOWLIST)
    assert sandbox.validate_command("echo hi")[0].lower().startswith("echo")
    for command in ("python -m http.server", "git status", 'python -c "x"'):
        with pytest.raises(SecurityError):
            sandbox.validate_command(command)


def test_e1_unauthorized_actor_denied_even_for_read() -> None:
    """PROOF 3: PermissionService denial blocks execution independently of tier."""
    bus = EventBus()
    ran: list[str] = _executed()
    _wire_orchestrator_stack(bus, permission=_DenyAllPermission(), sink=ran)
    failed = _collect(bus, TOOL_FAILED)
    completed = _collect(bus, TOOL_COMPLETED)

    run = _agent_run("echo denied")
    run["plan"]["steps"][0]["args"]["tool"] = READONLY_SHELL_TOOL
    bus.publish(EXECUTION_RUN_REQUEST, run, source="llm_planner")

    assert not completed and not ran, "denied actor must not execute even a READ action"
    assert failed and failed[0].get("error") == "permission denied"


def test_e2_untiered_action_is_rejected() -> None:
    """PROOF 4: authorized actor + unclassified capability -> DENY, no execution."""
    bus = EventBus()
    ran: list[str] = _executed()
    _wire_orchestrator_stack(bus, permission=_ProductionDefaultPermission(), sink=ran)
    confirmations = _collect(bus, TOOL_CONFIRMATION_REQUIRED)
    completed = _collect(bus, TOOL_COMPLETED)
    invokes = _collect(bus, TOOL_INVOKE)

    failed = _collect(bus, TOOL_FAILED)

    run = _agent_run("echo untiered")
    run["plan"]["steps"][0]["args"]["tool"] = "totally_unregistered_tool"
    bus.publish(EXECUTION_RUN_REQUEST, run, source="llm_planner")

    assert not completed and not ran, "unclassified action must not execute"
    assert not confirmations, "unclassified action must be rejected, not gated"
    # Classification is enforced at the TOOL_INVOKE boundary, where the tool
    # name is concrete; the invoke may be published but must never execute.
    assert failed, "unclassified action must produce an explicit denial"
    assert failed[0].get("error") == "unclassified action rejected", failed[0]
    assert len(invokes) <= 1, "rejection must be terminal, not retried"


@pytest.mark.parametrize(
    "forged_tier",
    [None, "", "read", "READ", "unknown", "not_a_tier", "write_destroy"],
)
def test_e3_forged_tier_in_plan_args_is_ignored(forged_tier: object) -> None:
    """PROOF 5: an LLM cannot declare its own SecurityTier for a dangerous tool.

    Generic ``shell`` is WRITE_DESTROY in the authoritative registry. No value a
    planner supplies — including a valid-looking "read" — may lower that.
    """
    bus = EventBus()
    ran: list[str] = _executed()
    _wire_orchestrator_stack(bus, permission=_ProductionDefaultPermission(), sink=ran)
    confirmations = _collect(bus, TOOL_CONFIRMATION_REQUIRED)
    completed = _collect(bus, TOOL_COMPLETED)

    run = _agent_run("echo forged")
    step_args = run["plan"]["steps"][0]["args"]
    step_args["tool"] = "shell"
    step_args["tier"] = forged_tier
    step_args["security_tier"] = forged_tier
    run["plan"]["steps"][0]["security_tier"] = forged_tier
    bus.publish(EXECUTION_RUN_REQUEST, run, source="llm_planner")

    assert confirmations, (
        f"forged tier {forged_tier!r} suppressed approval for generic shell"
    )
    assert not completed and not ran, "generic shell executed without approval"


def test_e4_registry_is_the_only_tier_source() -> None:
    """Unit-level: tier resolution never consults caller-supplied data."""
    assert resolve_tool_tier("shell") is SecurityTier.WRITE_DESTROY
    assert resolve_tool_tier("workspace_execute_command") is SecurityTier.WRITE_DESTROY
    assert resolve_tool_tier(READONLY_SHELL_TOOL) is SecurityTier.READ
    for unknown in ("", "   ", "nope", "SHELL_", None):
        assert resolve_tool_tier(unknown) is None, unknown  # type: ignore[arg-type]


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
