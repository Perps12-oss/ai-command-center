"""Control-plane invariants: approval gates and non-spoofable actor identity."""

from __future__ import annotations

from typing import Any

from ai_command_center.domain.planner_plan import PlanStep

COMMAND_TOOL_CAPABILITIES = frozenset({"shell", "workspace_execute_command"})

INTERACTIVE_USER_ACTOR = "user"
DEFAULT_AUTOMATION_ACTOR = "agent"

UI_PROVENANCES = frozenset({"ui", "ui_interactive", "interactive"})
WORKFLOW_PROVENANCE = "workflow"


def capability_requires_human_approval(capability: str) -> bool:
    return capability.strip().lower() in COMMAND_TOOL_CAPABILITIES


def step_requires_human_approval(step: PlanStep, *, run: dict[str, Any]) -> bool:
    """Return True when orchestrator must pause for tool.confirmation_required."""
    if bool(step.require_approval):
        return True
    cap = step.capability.strip().lower()
    if cap.startswith("agent."):
        return False
    if not capability_requires_human_approval(cap):
        return False
    provenance = str(run.get("actor_provenance") or "").lower()
    if provenance == WORKFLOW_PROVENANCE:
        return False
    if provenance in UI_PROVENANCES or bool(run.get("interactive_user")):
        return True
    return False


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
