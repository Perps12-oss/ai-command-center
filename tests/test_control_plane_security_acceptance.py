"""Control-plane security acceptance tests (adversarial invariants).

These tests encode required approval, actor-identity, and shell authority
invariants for the ADR-018 execution path. They are expected to **fail** on
``main`` until the remediation PR lands (see ``docs/audits/CONTROL_PLANE_SECURITY_AUDIT.md``).

Run only this suite::

    APPDATA=/tmp/aicc_appdata python3 -m pytest \\
        tests/test_control_plane_security_acceptance.py -m control_plane_acceptance
"""

from __future__ import annotations

import sqlite3
from typing import Any
from uuid import uuid4

import pytest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.command_sandbox import CommandSandbox
from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_REQUEST,
    EXECUTION_STEP_APPROVED,
    EXECUTION_STEP_AWAITING_APPROVAL,
    GOAL_SUBMIT_REQUEST,
    ORCHESTRATION_RECEIPT,
    TOOL_APPROVED,
    TOOL_COMPLETED,
    TOOL_CONFIRMATION_REQUIRED,
    TOOL_DENIED,
    TOOL_FAILED,
    TOOL_INVOKE,
    UI_COMMAND,
)
from ai_command_center.core.permission.permission import Permission, PermissionContext
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.domain.runtime_safety import SecurityTier
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
from ai_command_center.services.orchestration_service import OrchestrationService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry
from ai_command_center.ui.controller import UIController

pytestmark = pytest.mark.control_plane_acceptance

# Live defects remediated in cursor/control-plane-security-remediation-4b28.
# Keep marker import for documentation; xfail removed so XPASS guards regressions.


# ---------------------------------------------------------------------------
# Wiring helpers
# ---------------------------------------------------------------------------


class _DenyAllPermission:
    def check(self, permission: str, context: PermissionContext) -> bool:
        return False


def _conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def _wire_orchestrator_stack(
    bus: EventBus,
    *,
    permission: Any | None = None,
    register_shell: bool = True,
) -> ToolRegistry:
    registry = ToolRegistry()
    if register_shell:
        registry.register_tool(
            ToolSpec(
                name="shell",
                description="shell",
                handler=lambda args: ToolResult(
                    success=True, output=str(args.get("command", "ok"))
                ),
            )
        )
    ToolExecutorService(bus, registry, permission_service=permission).start()
    OrchestrationService(bus).start()
    ExecutionOrchestratorService(bus).start()
    return registry


def _wire_ea_stack(
    bus: EventBus,
    *,
    permission: Any | None = None,
) -> None:
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


# ---------------------------------------------------------------------------
# A. Approval authority
# ---------------------------------------------------------------------------


def test_auto_approve_cannot_suppress_require_approval_gate() -> None:
    """Mandatory step approval must not be bypassed by auto_approve payload."""
    bus = EventBus()
    _wire_orchestrator_stack(bus)
    awaiting = _collect(bus, EXECUTION_STEP_AWAITING_APPROVAL)
    confirmations = _collect(bus, TOOL_CONFIRMATION_REQUIRED)
    invokes = _collect(bus, TOOL_INVOKE)

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-auto-bypass",
            "auto_approve": True,
            "plan": {
                "goal": "gated",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "shell",
                        "args": {"command": "echo hi"},
                        "require_approval": True,
                    }
                ],
            },
        },
        source="test",
    )

    assert awaiting, "require_approval=True must pause even when auto_approve=True"
    assert confirmations, "confirmation must be emitted before TOOL_INVOKE"
    assert not invokes, "TOOL_INVOKE must not fire before human approval"


def test_ea_shell_intake_requires_confirmation_before_tool_invoke() -> None:
    """Primary EA → scheduler → orchestrator path must not auto-run shell."""
    bus = EventBus()
    _wire_ea_stack(bus)
    confirmations = _collect(bus, TOOL_CONFIRMATION_REQUIRED)
    awaiting = _collect(bus, EXECUTION_STEP_AWAITING_APPROVAL)
    invokes = _collect(bus, TOOL_INVOKE)
    goals = _collect(bus, GOAL_SUBMIT_REQUEST)

    bus.publish(
        UI_COMMAND,
        {"text": ">echo control-plane-audit", "workspace_id": "ws-shell"},
        source="ui",
    )

    assert goals, "EA must admit shell command as a goal"
    assert goals[0].get("auto_approve") is not True, (
        "EA must not stamp auto_approve on shell intake"
    )
    assert awaiting or confirmations, (
        "shell intake must pause for human approval before execution"
    )
    assert not invokes, "shell must not reach TOOL_INVOKE without explicit approval"


def test_llm_write_capability_requires_approval_on_orchestrator_path() -> None:
    """LLM-sourced write/shell plans must require confirmation (not auto-run)."""
    bus = EventBus()
    _wire_orchestrator_stack(bus)
    confirmations = _collect(bus, TOOL_CONFIRMATION_REQUIRED)
    invokes = _collect(bus, TOOL_INVOKE)

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-llm-write",
            "actor_provenance": "llm",
            "plan": {
                "goal": "write via shell",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "shell",
                        "args": {"command": "echo write"},
                        "require_approval": True,
                    }
                ],
            },
        },
        source="llm_planner",
    )

    assert confirmations, "LLM write/shell must emit tool.confirmation_required"
    assert not invokes, "write path must not invoke tools before approval"


# ---------------------------------------------------------------------------
# B. Actor identity (non-spoofable)
# ---------------------------------------------------------------------------


def test_llm_payload_actor_type_user_is_not_trusted() -> None:
    """Plan args must not escalate actor_type to trusted interactive user."""
    bus = EventBus()
    _wire_orchestrator_stack(bus, permission=_DenyAllPermission())
    invokes = _collect(bus, TOOL_INVOKE)
    confirmations = _collect(bus, TOOL_CONFIRMATION_REQUIRED)
    failed = _collect(bus, TOOL_FAILED)

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-actor-spoof",
            "auto_approve": True,
            "actor_provenance": "llm",
            "plan": {
                "goal": "spoof user",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "workspace_execute_command",
                        "args": {
                            "command": "echo hi",
                            "actor_type": "user",
                        },
                        "require_approval": False,
                    }
                ],
            },
            "workspace_context": {
                "workspace_id": str(uuid4()),
                "entity_id": str(uuid4()),
            },
        },
        source="llm_planner",
    )

    # A run gated for human approval never reaches dispatch — a stricter
    # outcome than dispatching with a corrected actor. Either satisfies this
    # invariant; dispatching as "user" does not.
    if invokes:
        actor = str(invokes[0].get("actor_type", ""))
        assert actor != "user", (
            "payload actor_type=user must be rejected/overridden for non-interactive runs"
        )
    else:
        assert confirmations or failed, (
            "non-interactive run must be gated, denied, or dispatched as a "
            "non-user actor — never silently dropped"
        )


def test_missing_actor_type_does_not_default_to_trusted_user() -> None:
    """Absent actor_type must not inherit full user shell privilege."""
    bus = EventBus()
    _wire_orchestrator_stack(bus, permission=_DenyAllPermission())
    invokes = _collect(bus, TOOL_INVOKE)
    failed = _collect(bus, TOOL_FAILED)
    confirmations = _collect(bus, TOOL_CONFIRMATION_REQUIRED)

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-missing-actor",
            "auto_approve": True,
            "actor_provenance": "llm",
            "plan": {
                "goal": "missing actor",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "workspace_execute_command",
                        "args": {"command": "echo hi"},
                        "require_approval": False,
                    }
                ],
            },
            "workspace_context": {
                "workspace_id": str(uuid4()),
                "entity_id": str(uuid4()),
            },
        },
        source="llm_planner",
    )

    if invokes:
        assert str(invokes[0].get("actor_type", "")) != "user"
    else:
        assert failed or confirmations, (
            "missing actor must fail closed (deny/gate), not silently run as user"
        )


def test_serialized_plan_actor_escalation_rejected() -> None:
    """Deserialized plan JSON cannot upgrade privileges via actor_type."""
    bus = EventBus()
    _wire_orchestrator_stack(bus, permission=_DenyAllPermission())
    invokes = _collect(bus, TOOL_INVOKE)
    confirmations = _collect(bus, TOOL_CONFIRMATION_REQUIRED)
    failed = _collect(bus, TOOL_FAILED)

    serialized_plan = {
        "goal": "escalation",
        "steps": [
            {
                "step_id": "step-1",
                "capability": "shell",
                "args": {"command": "echo x", "actor_type": "user"},
                "require_approval": False,
            }
        ],
    }
    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-serialized",
            "auto_approve": True,
            "actor_provenance": "serialized_goal",
            "plan": serialized_plan,
            "workspace_context": {"workspace_id": str(uuid4())},
        },
        source="goal_store",
    )

    # 'serialized_goal' is not an exempt provenance, so this now gates before
    # dispatch. Blocking is stricter than dispatching with a corrected actor.
    if invokes:
        assert str(invokes[0].get("actor_type", "")) != "user"
    else:
        assert confirmations or failed, (
            "deserialized plan must be gated or denied, never dispatched as user"
        )


# ---------------------------------------------------------------------------
# C. Shell / tool authority
# ---------------------------------------------------------------------------


def test_llm_workspace_execute_command_hits_permission_boundary() -> None:
    """Non-interactive workspace_execute_command must pass LAUNCH_TOOL gate."""
    bus = EventBus()
    _wire_orchestrator_stack(bus, permission=_DenyAllPermission())
    failed = _collect(bus, TOOL_FAILED)
    completed = _collect(bus, TOOL_COMPLETED)

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-ws-cmd",
            "auto_approve": True,
            "actor_provenance": "llm",
            "plan": {
                "goal": "run command",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "workspace_execute_command",
                        "args": {"command": "echo hi"},
                        "require_approval": False,
                    }
                ],
            },
            "workspace_context": {
                "workspace_id": str(uuid4()),
                "entity_id": str(uuid4()),
            },
        },
        source="llm_planner",
    )

    assert failed or not completed
    if failed:
        assert failed[0].get("error") == "permission denied"


@pytest.mark.parametrize(
    "command",
    [
        'python -c "print(1)"',
        "git status",
    ],
)
def test_llm_shell_primitives_require_authorization(command: str) -> None:
    """Allowlisted python/git must not run without approval + permission."""
    bus = EventBus()
    _wire_orchestrator_stack(bus, permission=_DenyAllPermission())
    confirmations = _collect(bus, TOOL_CONFIRMATION_REQUIRED)
    failed = _collect(bus, TOOL_FAILED)
    completed = _collect(bus, TOOL_COMPLETED)
    invokes = _collect(bus, TOOL_INVOKE)

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": f"run-shell-{uuid4().hex[:8]}",
            "auto_approve": True,
            "actor_provenance": "llm",
            "plan": {
                "goal": "shell primitive",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "workspace_execute_command",
                        "args": {"command": command},
                        "require_approval": True,
                    }
                ],
            },
            "workspace_context": {
                "workspace_id": str(uuid4()),
                "entity_id": str(uuid4()),
            },
        },
        source="llm_planner",
    )

    assert confirmations or failed, (
        f"command {command!r} must not complete without authorization"
    )
    assert not completed, f"command {command!r} must not succeed without authorization"
    if invokes:
        assert str(invokes[0].get("actor_type", "")) != "user"


def test_sandbox_python_c_inline_execution_is_blocked() -> None:
    """Sandbox must reject python -c even when python is allowlisted."""
    sandbox = CommandSandbox()
    with pytest.raises(Exception, match="inline execution"):
        sandbox.validate_command('python -c "import os"')


# ---------------------------------------------------------------------------
# D. Fail closed
# ---------------------------------------------------------------------------


def test_approval_without_paused_run_is_noop() -> None:
    """Stale or missing approval state must not resume execution."""
    bus = EventBus()
    _wire_orchestrator_stack(bus)
    invokes = _collect(bus, TOOL_INVOKE)

    bus.publish(
        TOOL_APPROVED,
        {
            "confirmation_id": "missing:s1",
            "run_id": "missing",
            "step_id": "s1",
            "approved": True,
        },
        source="ui",
    )

    assert not invokes, "approval without an active paused run must not dispatch tools"


def test_malformed_confirmation_id_denies_resume() -> None:
    """Malformed confirmation must not resume a paused run."""
    bus = EventBus()
    _wire_orchestrator_stack(bus)
    invokes = _collect(bus, TOOL_INVOKE)

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-malformed",
            "plan": {
                "goal": "gated",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "shell",
                        "args": {"command": "echo hi"},
                        "require_approval": True,
                    }
                ],
            },
        },
        source="test",
    )

    bus.publish(
        TOOL_APPROVED,
        {
            "confirmation_id": "not-a-valid-id",
            "run_id": "run-malformed",
            "step_id": "wrong-step",
            "approved": True,
        },
        source="ui",
    )

    assert not invokes, "malformed approval must not dispatch tools"


def test_unknown_actor_denies_shell_invoke() -> None:
    """Unknown actor_type must not receive LAUNCH_TOOL by default."""
    bus = EventBus()
    registry = ToolRegistry()
    ToolExecutorService(bus, registry, permission_service=_DenyAllPermission()).start()
    failed = _collect(bus, TOOL_FAILED)

    bus.publish(
        TOOL_INVOKE,
        {
            "contract_version": TOOL_CONTRACT_VERSION,
            "invoke_id": "unk-1",
            "tool": "workspace_execute_command",
            "args": {"command": "echo hi"},
            "actor_type": "llm",
            "workspace_context": {
                "workspace_id": str(uuid4()),
                "entity_id": str(uuid4()),
            },
        },
        source="llm",
    )

    assert failed
    assert failed[0].get("error") == "permission denied"


def test_unknown_permission_string_denies_check() -> None:
    from ai_command_center.core.permission.permission_service import PermissionService

    service = PermissionService(EventBus())
    with pytest.raises(ValueError, match="Invalid permission"):
        service.check(
            "not.a.real.permission",
            PermissionContext(
                entity_id=None,
                entity_type=None,
                action_id=None,
                actor_type="agent",
                actor_id=None,
            ),
        )


def test_confirmation_denied_fails_closed() -> None:
    """Explicit denial must not leave a paused run executing."""
    bus = EventBus()
    _wire_orchestrator_stack(bus)
    invokes = _collect(bus, TOOL_INVOKE)
    completed = _collect(bus, EXECUTION_RUN_COMPLETE)

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-denied",
            "plan": {
                "goal": "gated",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "shell",
                        "args": {"command": "echo hi"},
                        "require_approval": True,
                    }
                ],
            },
        },
        source="test",
    )

    bus.publish(
        TOOL_DENIED,
        {
            "confirmation_id": "run-denied:s1",
            "run_id": "run-denied",
            "step_id": "s1",
            "reason": "user denied",
        },
        source="ui",
    )

    assert not invokes
    assert not completed or completed[0].get("success") is False


def test_brain_write_destroy_auto_approve_payload_cannot_bypass() -> None:
    """Brain runtime: auto_approve must not bypass WRITE_DESTROY approval."""
    from ai_command_center.core.event_bus import EventBus as Bus
    from ai_command_center.core.events.topics import (
        RUNTIME_ACTION_COMPLETED,
        RUNTIME_ACTION_REQUEST,
        RUNTIME_APPROVAL_REQUESTED,
    )
    from ai_command_center.core.world_model.world_model import WorldModel
    from ai_command_center.repositories.world_model_repository import SQLiteWorldModelRepository
    from ai_command_center.services.brain_runtime_service import BrainRuntimeService

    bus = Bus()
    BrainRuntimeService(bus, WorldModel(SQLiteWorldModelRepository(_conn()))).start()
    approvals = _collect(bus, RUNTIME_APPROVAL_REQUESTED)
    completed = _collect(bus, RUNTIME_ACTION_COMPLETED)

    bus.publish(
        RUNTIME_ACTION_REQUEST,
        {
            "action_id": "destroy-auto",
            "tier": SecurityTier.WRITE_DESTROY.value,
            "auto_approve": True,
            "source_actor": "llm",
        },
        source="llm",
    )

    assert approvals, "WRITE_DESTROY must require approval even with auto_approve=True"
    assert not completed


def test_late_approval_after_denial_does_not_execute() -> None:
    """Expired/denied confirmation must not be revivable by a late approval."""
    bus = EventBus()
    _wire_orchestrator_stack(bus)
    invokes = _collect(bus, TOOL_INVOKE)

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-expired",
            "plan": {
                "goal": "gated",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "shell",
                        "args": {"command": "echo hi"},
                        "require_approval": True,
                    }
                ],
            },
        },
        source="test",
    )

    bus.publish(
        TOOL_DENIED,
        {
            "confirmation_id": "run-expired:s1",
            "run_id": "run-expired",
            "step_id": "s1",
            "reason": "confirmation expired",
        },
        source="ui",
    )

    bus.publish(
        TOOL_APPROVED,
        {
            "confirmation_id": "run-expired:s1",
            "run_id": "run-expired",
            "step_id": "s1",
            "approved": True,
        },
        source="ui",
    )

    assert not invokes, "late approval after denial/expiry must not execute"


# ---------------------------------------------------------------------------
# E. Happy path (regression guard — should pass on current main)
# ---------------------------------------------------------------------------


def test_human_approval_executes_and_emits_receipt() -> None:
    """Explicit human approval must allow execution and produce receipt evidence."""
    bus = EventBus()
    _wire_orchestrator_stack(bus)
    store = AppStateStore(bus)
    controller = UIController(bus, store, on_state=lambda: None)

    confirmations = _collect(bus, TOOL_CONFIRMATION_REQUIRED)
    receipts = _collect(bus, ORCHESTRATION_RECEIPT)
    completed = _collect(bus, EXECUTION_RUN_COMPLETE)

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-happy",
            "request_id": "req-happy",
            "actor_provenance": "ui",
            "interactive_user": True,
            "plan": {
                "goal": "approved shell",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "shell",
                        "args": {"command": "echo ok"},
                        "require_approval": True,
                    }
                ],
            },
        },
        source="test",
    )

    assert confirmations
    assert store.snapshot.pending_tool_confirmations
    controller.publish_tool_confirmation("run-happy:s1", approved=True)

    assert completed and completed[0].get("success") is not False
    assert receipts, "successful run must emit orchestration receipt before completion"
    assert not store.snapshot.pending_tool_confirmations
    store.close()


def test_human_approval_via_step_approved_executes() -> None:
    """EXECUTION_STEP_APPROVED remains a valid resume path after pause."""
    bus = EventBus()
    _wire_orchestrator_stack(bus)
    invokes = _collect(bus, TOOL_INVOKE)
    completed = _collect(bus, EXECUTION_RUN_COMPLETE)

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-step-approved",
            "request_id": "req-step-approved",
            "actor_provenance": "ui",
            "interactive_user": True,
            "plan": {
                "goal": "step approved",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "shell",
                        "args": {"command": "echo ok"},
                        "require_approval": True,
                    }
                ],
            },
        },
        source="test",
    )

    bus.publish(
        EXECUTION_STEP_APPROVED,
        {"run_id": "run-step-approved", "step_id": "s1"},
        source="ui",
    )

    assert invokes
    assert completed
