"""Pure command classifier library + optional legacy observer.

Decision-making for typed UI_COMMAND is owned by ExecutionAuthorityService.
This service no longer publishes COMMAND_ROUTED from UI_COMMAND; its ``classify``
helper remains the shared prefix/keyword table used by the authority.
"""

from __future__ import annotations

from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.intents import (
    INTENT_AGENT,
    INTENT_CHAT,
    INTENT_MEMORY_REMEMBER,
    INTENT_MEMORY_SELECT,
    INTENT_NAVIGATE,
    INTENT_NOTE_NEW,
    INTENT_SHELL,
)
from ai_command_center.core.events.topics import (
    WORKSPACE_ACTIVE,
    WORKSPACE_DEACTIVATED,
)
from ai_command_center.services.base import BaseService

_VIEW_ALIASES: dict[str, str] = {
    "settings": "settings",
    "chat": "chat",
    "notes": "notes",
    "plugins": "plugins",
    "home": "home",
    "workspace": "workspace",
    "system": "system",
    "memory": "memory",
    "command_center": "command_center",
    "goals": "goals",
    "agents": "agents",
    "approvals": "approvals",
    "providers": "providers",
    "executions": "executions",
    "automation": "automation",
    "capabilities": "capabilities",
    "artifacts": "artifacts",
}

# Navigation and inspector flows may proceed without an active workspace (soft gate).
_WORKSPACE_OPTIONAL_INTENTS: frozenset[str] = frozenset({INTENT_NAVIGATE})

# Obvious shell verbs when user omits the ">" prefix.
_SHELL_VERBS: tuple[str, ...] = (
    "echo ",
    "dir",
    "dir ",
    "cd ",
    "type ",
    "ls ",
    "pwd",
    "whoami",
    "get-childitem",
    "get-content ",
)


class CommandRouterService(BaseService):
    """
    Classifier library retained for shared prefix tables.

    MUST NOT: subscribe to UI_COMMAND for decision-making, plan, orchestrate,
    or publish competing COMMAND_ROUTED fan-out. ExecutionAuthority owns intake.
    """

    name = "command_router"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []
        self._active_workspace_id: str = ""

    def _on_load(self) -> None:
        # Workspace tracking only — no UI_COMMAND decision subscription (INV-1).
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_ACTIVE, self._on_workspace_active)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_DEACTIVATED, self._on_workspace_deactivated)
        )

    def _on_workspace_active(self, event: Event) -> None:
        self._active_workspace_id = str(event.payload.get("workspace_id", "")).strip()

    def _on_workspace_deactivated(self, event: Event) -> None:
        cleared = str(event.payload.get("workspace_id", "")).strip()
        if not cleared or cleared == self._active_workspace_id:
            self._active_workspace_id = ""

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    @staticmethod
    def classify(text: str) -> tuple[str, dict[str, str]]:
        """Prefix/keyword classification table (no LLM, no execution)."""
        stripped = text.strip()
        lower = stripped.lower()
        if lower in _VIEW_ALIASES:
            return INTENT_NAVIGATE, {"view": _VIEW_ALIASES[lower]}
        if text.startswith(">"):
            return INTENT_SHELL, {"command": text[1:].strip()}
        if lower.startswith("note:"):
            return INTENT_NOTE_NEW, {"body": text[5:].strip()}
        if lower.startswith("new note:"):
            return INTENT_NOTE_NEW, {"body": text[9:].strip()}
        if lower.startswith("go "):
            return INTENT_NAVIGATE, {"view": text[3:].strip().lower()}
        if lower.startswith("remember:"):
            return INTENT_MEMORY_REMEMBER, {"body": text[9:].strip()}
        if lower.startswith("memory:"):
            return INTENT_MEMORY_SELECT, {"query": text[7:].strip()}
        if lower.startswith("agent: spawn "):
            role = stripped[13:].strip()
            return INTENT_AGENT, {
                "task": role or "demo",
                "spawn_role": role,
                "spawn_mode": "single",
            }
        if lower.startswith("agents:"):
            body = stripped[7:].strip().lower()
            if body in {"", "demo", "multi", "multi-demo"}:
                return INTENT_AGENT, {"task": "multi-demo", "spawn_mode": "multi"}
            if body in {"pipeline demo", "pipeline", "pipeline-demo"}:
                return INTENT_AGENT, {"task": "pipeline-demo", "spawn_mode": "pipeline"}
            return INTENT_AGENT, {"task": body, "spawn_mode": "multi"}
        if lower.startswith("agent:"):
            return INTENT_AGENT, {
                "task": text[6:].strip() or "demo",
                "spawn_mode": "single",
            }
        if lower in {
            "agent demo",
            "supervised agent demo",
            "multi-agent demo",
            "agents demo",
        }:
            return INTENT_AGENT, {"task": "demo", "spawn_mode": "single"}
        for verb in _SHELL_VERBS:
            if lower == verb.strip() or lower.startswith(verb):
                return INTENT_SHELL, {"command": stripped}
        # INTENT_CHAT here is a classifier label only — ExecutionAuthority maps it
        # to an explicit llm PlanStep, never a direct LLM_REQUEST publish.
        return INTENT_CHAT, {"prompt": text}

    # Back-compat alias for older call sites / tests.
    _classify = classify
