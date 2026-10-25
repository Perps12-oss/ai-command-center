"""Authoritative SecurityTier classification for tool actions (ADR-004/ADR-022).

ADR-004 makes the approval requirement a property of the **action's tier**, not
of the actor::

    "WRITE_DESTROY requires explicit local approval."
    "Actions without a declared tier are rejected."

ADR-022 keeps the two axes independent::

    AutonomyScore = PolicyConfidence (SecurityTier, require_approval, PermissionService)
    "Policy gates ... remain hard constraints"

So this module answers exactly one question — *how much harm can this action
do?* — and never *who is asking*. Actor authorization lives in
``PermissionService``; provenance identifies the actor but grants no approval
authority.

**Tier is keyed on the dispatched tool, never on the plan step.** ``PlanStep``
and ``TOOL_INVOKE`` payloads are planner/LLM-authored, so a tier read from them
would be forgeable. Classification is a lookup in the table below, which is the
single source of truth.

Unclassified tools resolve to ``None`` and MUST be rejected by callers — never
defaulted to READ.
"""

from __future__ import annotations

from ai_command_center.domain.runtime_safety import SecurityTier

# Bounded read-only command runner: no interpreters, no network, no mutation.
# Distinct from the generic ``shell`` tool precisely so that "runs a command"
# and "runs an arbitrary program" are not the same capability.
READONLY_SHELL_TOOL = "shell_readonly"

# Programs permitted by READONLY_SHELL_TOOL. Deliberately excludes python and
# git: both accept code or a program path as an argument, so neither can be
# classified READ regardless of the subcommand used. Also excludes ``cat`` /
# ``type``: unconstrained path arguments would allow unapproved arbitrary file
# reads (e.g. the settings DB that may hold API keys). Use a path-validated
# file tool for content reads inside the vault/workspace.
READONLY_SHELL_ALLOWLIST: frozenset[str] = frozenset(
    {"echo", "whoami", "hostname", "ls", "dir"}
)

# ---------------------------------------------------------------------------
# The authoritative table. Keyed by TOOL name as dispatched via TOOL_INVOKE.
# ---------------------------------------------------------------------------
#
# Generic ``shell`` and ``workspace_execute_command`` are WRITE_DESTROY, not
# because every command they run is destructive, but because the capability
# they expose is *arbitrary program execution*. A capability is classified by
# its worst reachable outcome, not by the commands a demo happens to use.
_TOOL_TIERS: dict[str, SecurityTier] = {
    # --- READ: no side effects outside the process -------------------------
    READONLY_SHELL_TOOL: SecurityTier.READ,
    "system_time_query": SecurityTier.READ,
    "calendar_query": SecurityTier.READ,
    "notes.search": SecurityTier.READ,
    "memory.query": SecurityTier.READ,
    "navigate": SecurityTier.READ,
    "search_files": SecurityTier.READ,
    # --- WRITE: bounded, reversible side effects ---------------------------
    "notes.create": SecurityTier.WRITE,
    "memory.store": SecurityTier.WRITE,
    # Planner capability aliases (planner_service.py `preferred=` tuples).
    # Aliases are classified alongside their canonical tool so a rename cannot
    # silently produce an unclassified — and therefore rejected — action.
    "create_note": SecurityTier.WRITE,
    "note.create": SecurityTier.WRITE,
    "create_task": SecurityTier.WRITE,
    "create_entity": SecurityTier.WRITE,
    "modify_file": SecurityTier.WRITE,
    "send_email": SecurityTier.WRITE,
    # --- WRITE_DESTROY: irreversible or arbitrary ---------------------------
    "delete_file": SecurityTier.WRITE_DESTROY,
    "git_push": SecurityTier.WRITE_DESTROY,
    "calendar_event_create": SecurityTier.WRITE,
    "launch_application": SecurityTier.WRITE,
    "workspace_open_url": SecurityTier.WRITE,
    "workspace_open_folder": SecurityTier.WRITE,
    # --- WRITE_DESTROY: arbitrary execution --------------------------------
    "shell": SecurityTier.WRITE_DESTROY,
    "workspace_execute_command": SecurityTier.WRITE_DESTROY,
}


class UnclassifiedActionError(Exception):
    """Raised when an action has no authoritative SecurityTier (ADR-004)."""


def resolve_tool_tier(tool: str) -> SecurityTier | None:
    """Return the authoritative tier for ``tool``, or None if unclassified.

    Never consults caller-supplied data. ``None`` means *reject* — callers must
    not substitute a default.
    """
    if not isinstance(tool, str):
        return None
    return _TOOL_TIERS.get(tool.strip().lower())


def is_classified(tool: str) -> bool:
    return resolve_tool_tier(tool) is not None


def tier_requires_human_approval(tier: SecurityTier | None) -> bool:
    """ADR-004: WRITE_DESTROY always requires explicit local human approval.

    An unclassified action (``None``) is *rejected* rather than approved, so it
    is not an approval question — callers must reject before reaching here.
    """
    return tier is SecurityTier.WRITE_DESTROY


def tool_requires_human_approval(tool: str) -> bool:
    """Convenience wrapper: does dispatching ``tool`` demand HITL?

    Unclassified tools return False here **only** because they must already
    have been rejected by the classification gate; never call this without
    first checking :func:`is_classified`.
    """
    return tier_requires_human_approval(resolve_tool_tier(tool))


def classified_tools() -> frozenset[str]:
    return frozenset(_TOOL_TIERS)


__all__ = [
    "READONLY_SHELL_ALLOWLIST",
    "READONLY_SHELL_TOOL",
    "SecurityTier",
    "UnclassifiedActionError",
    "classified_tools",
    "is_classified",
    "resolve_tool_tier",
    "tier_requires_human_approval",
    "tool_requires_human_approval",
]
