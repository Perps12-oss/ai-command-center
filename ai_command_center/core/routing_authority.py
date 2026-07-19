"""Routing authority source helpers for COMMAND_ROUTED consumers.

ExecutionAuthorityService is the sole decision-maker for UI_COMMAND.
Legacy capability handlers (notes, memory, navigate, agents) still consume
COMMAND_ROUTED when the authority publishes it for those intents.
"""

from __future__ import annotations

ROUTING_AUTHORITY_SOURCES: frozenset[str] = frozenset(
    {
        "execution_authority",
        "command_router",  # retained for tests / migration compatibility
    }
)


def is_routing_authority(source: str | None) -> bool:
    """Return True when the event was published by a routing authority."""
    return str(source or "").strip() in ROUTING_AUTHORITY_SOURCES
