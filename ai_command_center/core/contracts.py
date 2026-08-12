"""Versioned architecture contracts — bump only with explicit governance review.

Contracts locked at Phase 3D → 4 transition.

Version bump policy:
    1. Update constants and SUPPORTED_VERSIONS below.
    2. Update gate history in docs/ARCHITECTURE.md#gate-history.
    3. Run full phase regression suite (scripts/verify_contracts.py and all verify_phase*.py).
    4. Constitutional review required if consumer/producer ownership changes.

Gate: python scripts/verify_contracts.py

ContextBundle v1.2 (current):
    Producer: ContextManager.build_context() only
    Consumer: OllamaService.stream_chat() / .stream() / .chat()
    v1.2 adds workspace_state section labels from workspace_snippets (vNext M1).
    v1.0 and v1.1 remain in SUPPORTED_VERSIONS for backward compatibility.

command.deferred v1.0:
    Producer: ExecutionAuthorityService
    Consumer: UI workspace gate / AppState diagnostics

tool.invoke / tool.result v1.0 (Phase 4B):
    Producer: ExecutionOrchestratorService (exclusive)
    Consumer: ToolExecutorService — one invocation per event, no loops

OllamaService API v1.0: unchanged.

operation contract v1.0 (Blueprint Phase 0):
    Producer: OperationIndexerService
    Consumer: AppState reducer (_reduce_operation_loaded)
    OPERATION_LOAD_REQUEST payload: {correlation_id: str}
    OPERATION_LOADED payload: {correlation_id: str, snapshot: dict[str, Any]}
    OPERATION_SAVED payload: {correlation_id: str, goal_id: str, goal_title: str, goal_status: str}
    OPERATION_ARCHIVED payload: {correlation_id: str, frozen_at: float}
"""

from __future__ import annotations

# ContextBundle (ContextManager → OllamaService)
CONTEXT_BUNDLE_VERSION = "1.2"
CONTEXT_BUNDLE_VERSION_LEGACY = "1.0"
CONTEXT_BUNDLE_VERSION_V11 = "1.1"

# command.deferred envelope (ExecutionAuthority → UI workspace gate)
COMMAND_DEFERRED_VERSION = "1.0"

# OllamaService public API surface
OLLAMA_SERVICE_API_VERSION = "1.0"

# tool.invoke / tool.result envelope (Phase 4B)
TOOL_CONTRACT_VERSION = "1.0"

# operation.load_request / operation.loaded envelope (Blueprint Phase 0)
OPERATION_CONTRACT_VERSION = "1.0"

# execution.authority.decision `intake` provenance (Phase B).
#   Producer: ExecutionAuthorityService (sole publisher)
#   Consumer: chat_state reducer — only INTAKE_UI_COMMAND may mutate chat state
# A decision without an `intake` key predates this contract and is treated as
# INTAKE_UI_COMMAND, preserving established behaviour.
INTAKE_UI_COMMAND = "ui_command"
INTAKE_WORKFLOW = "workflow"
INTAKE_AGENT = "agent"

# TOOL_INVOKE without workspace_context — documented opt-out paths (Program 3 exit):
#   1. actor_type "user" with empty workspace_context (no active workspace at invoke time)
#   2. Non-production tests and verification scripts
#   3. Workflow runs without workspace binding (run["workspace_context"] defaults to {})
# Non-user actors (agent, workflow) require workspace_context per ToolExecutorService.

SUPPORTED_VERSIONS: dict[str, tuple[str, ...]] = {
    "context_bundle": (
        CONTEXT_BUNDLE_VERSION_LEGACY,
        CONTEXT_BUNDLE_VERSION_V11,
        CONTEXT_BUNDLE_VERSION,
    ),
    "command_deferred": (COMMAND_DEFERRED_VERSION,),
    "ollama_service": (OLLAMA_SERVICE_API_VERSION,),
    "tool": (TOOL_CONTRACT_VERSION,),
    "operation": (OPERATION_CONTRACT_VERSION,),
}


def build_workspace_context(
    *,
    workspace_id: object = None,
    entity_id: object = None,
    entity_type: object = None,
) -> dict[str, str]:
    """Build a tool.invoke workspace_context dict from scoped ids."""
    ctx: dict[str, str] = {}
    ws = str(workspace_id or "").strip()
    eid = str(entity_id or "").strip()
    etype = str(entity_type or "").strip()
    if ws:
        ctx["workspace_id"] = ws
    if eid:
        ctx["entity_id"] = eid
    if etype:
        ctx["entity_type"] = etype
    return ctx


def is_executable_workflow_step(step: object) -> bool:
    """Whether a workflow step manifest entry becomes an ExecutionPlan step.

    Single owner of this rule (Inv 11): WorkflowEngineService uses it to reject a
    workflow that would produce no work, and ExecutionAuthority uses it to build
    plan steps. Two independent copies could drift and silently reintroduce the
    stuck-run defect this predicate exists to prevent.

    A step with no explicit ``type`` is treated as a tool step, matching the
    established intake behaviour.
    """
    if not isinstance(step, dict):
        return False
    if str(step.get("type") or "tool") != "tool":
        return False
    return bool(str(step.get("tool") or "").strip())


def is_valid_workspace_context(value: object) -> bool:
    """Non-user tool invocations require workspace_id and/or entity_id."""
    if not isinstance(value, dict):
        return False
    ws = str(value.get("workspace_id", "")).strip()
    eid = str(value.get("entity_id", "")).strip()
    return bool(ws or eid)
