"""Control-plane invariants: approval gates and non-spoofable actor identity."""

from __future__ import annotations

from typing import Any

from ai_command_center.core.security_policy import (
    is_classified,
    tool_requires_human_approval,
)
from ai_command_center.domain.planner_plan import PlanStep

COMMAND_TOOL_CAPABILITIES = frozenset({"shell", "workspace_execute_command"})

INTERACTIVE_USER_ACTOR = "user"
DEFAULT_AUTOMATION_ACTOR = "agent"

UI_PROVENANCES = frozenset({"ui", "ui_interactive", "interactive"})
WORKFLOW_PROVENANCE = "workflow"


def capability_requires_human_approval(capability: str) -> bool:
    return capability.strip().lower() in COMMAND_TOOL_CAPABILITIES


def effective_tool_for_step(step: PlanStep) -> str:
    """Return the tool a step will actually dispatch, not its capability label.

    ``agent.*`` capabilities are dispatched by
    ``ExecutionOrchestratorService._dispatch_agent_step``, which reads the tool
    from ``step.args["tool"]`` and **defaults to shell**. The capability label is
    planner-authored, so it must never be the thing the approval gate keys on.
    ``agent.task`` is the one agent capability that dispatches no tool (it
    re-enters intake instead) and therefore resolves to no tool here.
    """
    cap = step.capability.strip().lower()
    if not cap.startswith("agent."):
        return cap
    if cap == "agent.task":
        return ""
    args = step.args if isinstance(step.args, dict) else {}
    return str(args.get("tool") or "shell").strip().lower() or "shell"


def step_is_classified(step: PlanStep) -> bool:
    """Return True when the step's dispatched tool has an authoritative tier.

    Steps that dispatch no tool (orchestration-only capabilities such as
    ``llm``, ``goal``, ``workflow``, ``agent.task``) are not tool actions and
    are outside ADR-004's classification requirement.
    """
    tool = effective_tool_for_step(step)
    if not tool:
        return True
    return is_classified(tool)


def step_requires_human_approval(step: PlanStep, *, run: dict[str, Any]) -> bool:
    """Return True when orchestrator must pause for tool.confirmation_required.

    ADR-004/ADR-022: approval is a property of the action's SecurityTier, not of
    the actor. ``run`` is accepted for interface stability and deliberately not
    consulted — provenance identifies the actor for PermissionService and grants
    no approval authority.

    Unclassified tools are rejected upstream by :func:`step_is_classified`, so
    they never reach an approval decision.
    """
    if bool(step.require_approval):
        return True
    return tool_requires_human_approval(effective_tool_for_step(step))


def intake_run_fields(*, intake: str) -> dict[str, Any]:
    """Stamp non-spoofable run metadata at ExecutionAuthority admission."""
    raw = str(intake or "").strip().lower() or "unknown"
    fields: dict[str, Any] = {
        "auto_approve": False,
        "actor_provenance": raw,
        "interactive_user": False,
    }
    if raw in UI_PROVENANCES or raw == "ui_command":
        fields["actor_provenance"] = "ui"
        fields["interactive_user"] = True
        fields["actor_type"] = INTERACTIVE_USER_ACTOR
    elif raw == WORKFLOW_PROVENANCE:
        fields["actor_provenance"] = WORKFLOW_PROVENANCE
        fields["actor_type"] = WORKFLOW_PROVENANCE
    elif raw.startswith("agent"):
        fields["actor_provenance"] = "agent"
        fields["actor_type"] = DEFAULT_AUTOMATION_ACTOR
    return fields


def resolve_run_context(payload: dict[str, Any]) -> dict[str, Any]:
    """Derive trusted actor context from EXECUTION_RUN_REQUEST payload."""
    interactive_user = bool(payload.get("interactive_user"))
    provenance = str(payload.get("actor_provenance") or "").strip().lower()
    if provenance in UI_PROVENANCES:
        interactive_user = True
    if provenance == WORKFLOW_PROVENANCE:
        return {
            "actor_type": WORKFLOW_PROVENANCE,
            "interactive_user": False,
            "actor_provenance": provenance,
        }

    explicit_actor = str(payload.get("actor_type") or "").strip().lower()
    if interactive_user:
        actor_type = INTERACTIVE_USER_ACTOR
    elif explicit_actor and explicit_actor != INTERACTIVE_USER_ACTOR:
        actor_type = explicit_actor
    elif provenance == "agent":
        actor_type = DEFAULT_AUTOMATION_ACTOR
    else:
        actor_type = DEFAULT_AUTOMATION_ACTOR

    return {
        "actor_type": actor_type,
        "interactive_user": interactive_user and actor_type == INTERACTIVE_USER_ACTOR,
        "actor_provenance": provenance,
    }


def resolve_tool_invoke_actor(*, run: dict[str, Any]) -> tuple[str, bool]:
    """Return (actor_type, interactive_user) for TOOL_INVOKE — never trust step.args."""
    actor_type = str(run.get("actor_type") or DEFAULT_AUTOMATION_ACTOR).strip().lower()
    interactive_user = bool(run.get("interactive_user")) and actor_type == INTERACTIVE_USER_ACTOR
    if actor_type == INTERACTIVE_USER_ACTOR and not interactive_user:
        actor_type = DEFAULT_AUTOMATION_ACTOR
        interactive_user = False
    return actor_type, interactive_user


def plan_step_require_approval_for_capability(capability: str) -> bool:
    """Synthetic plans from EA must flag high-risk capabilities."""
    return capability_requires_human_approval(capability)
