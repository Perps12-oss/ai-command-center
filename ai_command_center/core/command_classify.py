"""Shared prefix/keyword command classification (no LLM, no execution)."""

from __future__ import annotations

from ai_command_center.core.events.intents import (
    INTENT_AGENT,
    INTENT_CHAT,
    INTENT_MEMORY_REMEMBER,
    INTENT_MEMORY_SELECT,
    INTENT_NAVIGATE,
    INTENT_NOTE_NEW,
    INTENT_SHELL,
)

_VIEW_ALIASES: dict[str, str] = {
    "settings": "settings",
    "chat": "chat",
    "notes": "notes",
    "plugins": "plugins",
    "home": "command_center",
    "workspace": "workspace",
    "system": "system",
    "memory": "memory",
    "command_center": "command_center",
    "brain": "brain",
    "goals": "goals",
    "agents": "agents",
    "approvals": "approvals",
    "providers": "providers",
    "executions": "executions",
    "evidence": "evidence",
    "operations": "operations",
    "automation": "automation",
    "capabilities": "capabilities",
    "artifacts": "artifacts",
    "graph": "graph_workspace",
    "graph_workspace": "graph_workspace",
    "relationship graph": "graph_workspace",
    "knowledge graph": "graph_workspace",
}

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


def classify_command(text: str) -> tuple[str, dict[str, str]]:
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
    return INTENT_CHAT, {"prompt": text}
