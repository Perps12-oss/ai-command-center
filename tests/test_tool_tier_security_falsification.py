"""SecurityTier falsification tests (ADR-004 / Option a).

Proves WRITE_DESTROY requires HITL regardless of provenance, unclassified tools
are rejected at the TOOL_INVOKE boundary, sandbox hardening blocks interpreter
injection, and permission vs HITL remain independent gates.

Run::

    APPDATA=/tmp/aicc_appdata python3 -m pytest \\
        tests/test_tool_tier_security_falsification.py \\
        -m control_plane_acceptance -p no:cacheprovider --no-cov
"""

from __future__ import annotations

import sqlite3
from typing import Any
from uuid import uuid4

import pytest

from ai_command_center.core.command_sandbox import (
    READONLY_COMMAND_SANDBOX,
    CommandSandbox,
    SecurityError,
)
from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION
from ai_command_center.core.control_plane import step_requires_human_approval
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
from ai_command_center.core.security_policy import resolve_tool_tier
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.domain.planner_plan import PlanStep
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
from tests.support.shell_confirmation import wire_auto_confirm_shell

pytestmark = pytest.mark.control_plane_acceptance


class _ProductionDefaultPermission:
    def check(self, permission: str, context: PermissionContext) -> bool:
        return permission == Permission.LAUNCH_TOOL.value


class _DenyAllPermission:
    def check(self, permission: str, context: PermissionContext) -> bool:
        return False


def _conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def _executed() -> list[str]:
    return []


def _wire_orchestrator_stack(
    bus: EventBus,
    *,
    permission: Any | None = None,
    sink: list[str] | None = None,
    auto_confirm: bool = False,
) -> ToolRegistry:
    if auto_confirm:
        wire_auto_confirm_shell(bus)
    registry = ToolRegistry()

    def _handler(args: dict[str, Any]) -> ToolResult:
        command = str(args.get("command", ""))
        if sink is not None:
            sink.append(command)
        return ToolResult(success=True, output=command or "ok")

    for name in ("shell", "workspace_execute_command"):
        registry.register_tool(
            ToolSpec(
                name=name,
                description=name,
                handler=_handler,
                tier=SecurityTier.WRITE_DESTROY,
            )
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


def _shell_run(
    command: str = "echo hi",
    *,
    capability: str = "shell",
    provenance: str = "agent",
) -> dict[str, Any]:
    return {
        "run_id": f"run-{uuid4().hex[:8]}",
        "actor_provenance": provenance,
        "actor_type": provenance if provenance else "agent",
        "plan": {
            "goal": "probe",
            "steps": [
                {
                    "step_id": "s1",
                    "capability": capability,
                    "args": {"command": command, "tool": "shell"},
                }
            ],
        },
        "workspace_context": {
            "workspace_id": str(uuid4()),
            "entity_id": str(uuid4()),
        },
    }


def test_agent_write_destroy_requires_approval() -> None:
    bus = EventBus()
    ran = _executed()
    _wire_orchestrator_stack(bus, permission=_ProductionDefaultPermission(), sink=ran)
    confirmations = _collect(bus, TOOL_CONFIRMATION_REQUIRED)
    completed = _collect(bus, TOOL_COMPLETED)

    bus.publish(
        EXECUTION_RUN_REQUEST,
        _shell_run(capability="agent.shell"),
        source="llm_planner",
    )

    assert confirmations, "agent WRITE_DESTROY must enter approval flow"
    assert not completed
    assert not ran


@pytest.mark.parametrize(
    "provenance",
    ["agent", "llm", "ui", "workflow", ""],
)
def test_write_destroy_hitl_all_provenances(provenance: str) -> None:
    step = PlanStep(step_id="s1", capability="shell", args={"command": "echo hi"})
    run = {"actor_provenance": provenance, "interactive_user": provenance == "ui"}
    assert step_requires_human_approval(step, run=run), (
        f"WRITE_DESTROY must require HITL for provenance={provenance!r}"
    )


def test_unclassified_tool_rejected_at_invoke_boundary() -> None:
    bus = EventBus()
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="mystery_tool", description="no tier", handler=lambda a: ToolResult(success=True, output="x"))
    )
    ToolExecutorService(bus, registry, permission_service=_ProductionDefaultPermission()).start()
    failed = _collect(bus, TOOL_FAILED)

    bus.publish(
        TOOL_INVOKE,
        {
            "contract_version": TOOL_CONTRACT_VERSION,
            "invoke_id": "x1",
            "tool": "mystery_tool",
            "args": {},
            "actor_type": "agent",
            "workspace_context": {"workspace_id": str(uuid4()), "entity_id": str(uuid4())},
        },
        source="test",
    )

    assert failed
    assert "unclassified" in str(failed[0].get("error", "")).lower()


def test_write_destroy_invoke_requires_human_approved_flag() -> None:
    bus = EventBus()
    _wire_orchestrator_stack(bus, permission=_ProductionDefaultPermission())
    failed = _collect(bus, TOOL_FAILED)

    bus.publish(
        TOOL_INVOKE,
        {
            "contract_version": TOOL_CONTRACT_VERSION,
            "invoke_id": "x2",
            "tool": "shell",
            "args": {"command": "echo hi"},
            "actor_type": "agent",
            "human_approved": False,
            "workspace_context": {"workspace_id": str(uuid4()), "entity_id": str(uuid4())},
        },
        source="test",
    )

    assert failed
    assert "human approval" in str(failed[0].get("error", "")).lower()


def test_permission_and_hitl_are_independent_gates() -> None:
    """Permission granted but HITL missing must still block WRITE_DESTROY."""
    bus = EventBus()
    _wire_orchestrator_stack(bus, permission=_ProductionDefaultPermission())
    failed = _collect(bus, TOOL_FAILED)

    bus.publish(
        TOOL_INVOKE,
        {
            "contract_version": TOOL_CONTRACT_VERSION,
            "invoke_id": "x3",
            "tool": "shell",
            "args": {"command": "echo hi"},
            "actor_type": "agent",
            "workspace_context": {"workspace_id": str(uuid4()), "entity_id": str(uuid4())},
        },
        source="test",
    )

    assert failed
    assert failed[0].get("error") == "human approval required"

    bus2 = EventBus()
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(
            name="shell",
            description="shell",
            handler=lambda a: ToolResult(success=True, output="ok"),
            tier=SecurityTier.WRITE_DESTROY,
        )
    )
    ToolExecutorService(bus2, registry, permission_service=_DenyAllPermission()).start()
    failed2 = _collect(bus2, TOOL_FAILED)
    bus2.publish(
        TOOL_INVOKE,
        {
            "contract_version": TOOL_CONTRACT_VERSION,
            "invoke_id": "x4",
            "tool": "shell",
            "args": {"command": "echo hi"},
            "actor_type": "agent",
            "human_approved": True,
            "workspace_context": {"workspace_id": str(uuid4()), "entity_id": str(uuid4())},
        },
        source="test",
    )
    assert failed2
    assert failed2[0].get("error") == "permission denied"


def test_auto_approve_does_not_suppress_write_destroy() -> None:
    step = PlanStep(step_id="s1", capability="shell", args={"command": "echo hi"})
    assert step_requires_human_approval(step, run={"auto_approve": True})


@pytest.mark.parametrize(
    "command",
    [
        "git -c core.fsmonitor=calc status",
        "git clone --upload-pack=calc host:repo",
        "git -c alias.z=!calc z",
        "python -m http.server",
        "python -m pip install attacker-pkg",
    ],
)
def test_sandbox_rejects_interpreter_injection(command: str) -> None:
    sandbox = CommandSandbox()
    with pytest.raises(SecurityError):
        sandbox.validate_command(command)


def test_readonly_sandbox_rejects_interpreters() -> None:
    with pytest.raises(SecurityError):
        READONLY_COMMAND_SANDBOX.validate_command("git status")
    with pytest.raises(SecurityError):
        READONLY_COMMAND_SANDBOX.validate_command("python -m http.server")
    with pytest.raises(SecurityError):
        READONLY_COMMAND_SANDBOX.validate_command("cat /etc/passwd")
    with pytest.raises(SecurityError):
        READONLY_COMMAND_SANDBOX.validate_command(r"type C:\Windows\win.ini")
    assert READONLY_COMMAND_SANDBOX.validate_command("echo hi")


def test_shell_readonly_tier_is_read() -> None:
    assert resolve_tool_tier("shell_readonly") == SecurityTier.READ


def test_workflow_write_destroy_requires_confirmation() -> None:
    bus = EventBus()
    _wire_orchestrator_stack(bus, permission=_ProductionDefaultPermission())
    confirmations = _collect(bus, TOOL_CONFIRMATION_REQUIRED)
    invokes = _collect(bus, TOOL_INVOKE)

    run = _shell_run(provenance="workflow")
    run["actor_type"] = "workflow"
    bus.publish(EXECUTION_RUN_REQUEST, run, source="workflow_engine")

    assert confirmations, "workflow WRITE_DESTROY must still require HITL (ADR-004)"
    assert not invokes


def test_workflow_dispatches_after_approval() -> None:
    bus = EventBus()
    ran = _executed()
    _wire_orchestrator_stack(
        bus,
        permission=_ProductionDefaultPermission(),
        sink=ran,
        auto_confirm=True,
    )
    invokes = _collect(bus, TOOL_INVOKE)

    run = _shell_run("echo workflow", provenance="workflow")
    run["actor_type"] = "workflow"
    bus.publish(EXECUTION_RUN_REQUEST, run, source="workflow_engine")

    assert invokes
    assert invokes[0].get("human_approved") is True
    assert str(invokes[0].get("actor_type", "")) != "user"
    assert ran == ["echo workflow"]


def test_agent_task_does_not_launder_provenance() -> None:
    bus = EventBus()
    _wire_ea_stack(bus, permission=_ProductionDefaultPermission())
    submits = _collect(bus, GOAL_SUBMIT_REQUEST)

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
    ]
    assert not escalated


def test_agent_execution_request_stays_agent() -> None:
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

    assert submits
    for payload in submits:
        assert not bool(payload.get("interactive_user"))
        assert str(payload.get("actor_type", "")).lower() != "user"
