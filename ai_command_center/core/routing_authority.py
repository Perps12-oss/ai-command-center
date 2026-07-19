"""Routing authority source helpers for decision-event consumers.

ExecutionAuthorityService is the sole decision-maker for UI_COMMAND.
Navigate and other state capabilities execute via ExecutionPlan tools
(UI_NAVIGATE / TOOL_INVOKE).
"""

from __future__ import annotations

ROUTING_AUTHORITY_SOURCES: frozenset[str] = frozenset(
    {
        "execution_authority",
    }
)


def is_routing_authority(source: str | None) -> bool:
    """Return True when the event was published by a routing authority."""
    return str(source or "").strip() in ROUTING_AUTHORITY_SOURCES
