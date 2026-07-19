"""Shared intent / capability prefix identifiers.

Used by ``CommandRouterService.classify`` and ExecutionAuthority prefix maps.
Services must import from this module — not from ``command_router_service`` —
to avoid peer imports.
"""

from __future__ import annotations

INTENT_CHAT = "chat"
INTENT_SHELL = "shell"
INTENT_NOTE_SEARCH = "note_search"
INTENT_NOTE_NEW = "note_new"
INTENT_NAVIGATE = "navigate"
INTENT_MEMORY_REMEMBER = "memory_remember"
INTENT_MEMORY_SELECT = "memory_select"
INTENT_AGENT = "agent"
INTENT_UNKNOWN = "unknown"

__all__ = [
    "INTENT_CHAT",
    "INTENT_SHELL",
    "INTENT_NOTE_SEARCH",
    "INTENT_NOTE_NEW",
    "INTENT_NAVIGATE",
    "INTENT_MEMORY_REMEMBER",
    "INTENT_MEMORY_SELECT",
    "INTENT_AGENT",
    "INTENT_UNKNOWN",
]
