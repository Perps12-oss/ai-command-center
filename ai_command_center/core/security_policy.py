"""Authoritative SecurityTier resolution for tool execution (ADR-004).

ToolSpec may declare ``tier``; this module supplies the canonical fallback table.
Unknown tools resolve to ``None`` and must be rejected fail-closed.
"""

from __future__ import annotations

from ai_command_center.core.tools import ToolSpec
from ai_command_center.domain.runtime_safety import SecurityTier

# Capability labels that dispatch to a different registered tool name.
_CAPABILITY_TOOL_ALIASES: dict[str, str] = {
    "create_note": "notes.create",
    "note.create": "notes.create",
    "note_search": "notes.search",
    "search_files": "notes.search",
    "shell": "shell",
    "workspace_execute_command": "workspace_execute_command",
}

# Authoritative fallback when ToolSpec.tier is unset.
_FALLBACK_TOOL_TIERS: dict[str, SecurityTier] = {
    "shell": SecurityTier.WRITE_DESTROY,
    "workspace_execute_command": SecurityTier.WRITE_DESTROY,
    "shell_readonly": SecurityTier.READ,
    "notes.create": SecurityTier.WRITE,
    "notes.search": SecurityTier.READ,
    "memory.store": SecurityTier.WRITE,
    "memory.query": SecurityTier.READ,
    "navigate": SecurityTier.READ,
    "launch_application": SecurityTier.WRITE,
    "system_time_query": SecurityTier.READ,
    "calendar_query": SecurityTier.READ,
    "calendar_event_create": SecurityTier.WRITE,
    "workspace_open_url": SecurityTier.WRITE,
    "workspace_open_folder": SecurityTier.WRITE,
    # Common planner capability labels (orchestrator uses capability as tool name).
    "create_task": SecurityTier.WRITE,
    "create_entity": SecurityTier.WRITE,
    "search_files": SecurityTier.READ,
    "modify_file": SecurityTier.WRITE,
    "delete_file": SecurityTier.WRITE_DESTROY,
    "git_push": SecurityTier.WRITE_DESTROY,
    "send_email": SecurityTier.WRITE,
    # External capability namespace (read-only probe).
    "mcp.filesystem.read": SecurityTier.READ,
}


def normalize_tool_name(name: str) -> str:
    """Map capability aliases to canonical tool registry names."""
    key = str(name or "").strip().lower()
    if not key:
        return ""
    return _CAPABILITY_TOOL_ALIASES.get(key, key)


def resolve_tool_tier(tool_name: str, spec: ToolSpec | None = None) -> SecurityTier | None:
    """Resolve SecurityTier for a tool name; ``None`` means unclassified (reject)."""
    if spec is not None and spec.tier is not None:
        return spec.tier
    normalized = normalize_tool_name(spec.name if spec is not None else tool_name)
    if not normalized:
        return None
    return _FALLBACK_TOOL_TIERS.get(normalized)


def tier_requires_hitl(tier: SecurityTier) -> bool:
    """ADR-004: WRITE_DESTROY requires explicit human approval."""
    return tier == SecurityTier.WRITE_DESTROY
