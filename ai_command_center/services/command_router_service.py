"""Routes ui.command intents to typed command.routed events (Phase 3 handlers attach here)."""

from __future__ import annotations

from typing import Callable

from ai_command_center.core.contracts import COMMAND_ROUTED_VERSION
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.intents import (
    INTENT_AGENT,
    INTENT_CHAT,
    INTENT_MEMORY_REMEMBER,
    INTENT_MEMORY_SELECT,
    INTENT_NAVIGATE,
    INTENT_NOTE_NEW,
    INTENT_NOTE_SEARCH,
    INTENT_SHELL,
)
from ai_command_center.core.events.topics import COMMAND_ROUTED, UI_COMMAND
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
}

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
    Intent detection + routing only.

    MUST NOT: plan, reason, orchestrate, or run multi-step agent loops.
    """

    name = "command_router"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(self._bus.subscribe(UI_COMMAND, self._on_ui_command))

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    @staticmethod
    def _workspace_scope(event: Event) -> dict[str, str]:
        """Intent-agnostic workspace scope from ui.command payload."""
        scope: dict[str, str] = {}
        workspace_entity_id = str(event.payload.get("workspace_entity_id", "")).strip()
        if workspace_entity_id:
            scope["workspace_entity_id"] = workspace_entity_id
            scope["workspace_entity_type"] = str(
                event.payload.get("workspace_entity_type", "")
            )
            scope["workspace_entity_title"] = str(
                event.payload.get("workspace_entity_title", "")
            )
            for key in (
                "workspace_entity_description",
                "workspace_entity_url",
                "workspace_entity_path",
            ):
                value = str(event.payload.get(key, "")).strip()
                if value:
                    scope[key] = value
        workspace_id = str(event.payload.get("workspace_id", "")).strip()
        if workspace_id:
            scope["workspace_id"] = workspace_id
        return scope

    def _on_ui_command(self, event: Event) -> None:
        text = str(event.payload.get("text", "")).strip()
        if not text:
            return
        intent, args = self._classify(text)
        clipboard = event.payload.get("clipboard")
        if clipboard and intent == INTENT_CHAT:
            args = {**args, "clipboard": str(clipboard)}
        scope = self._workspace_scope(event)
        if scope:
            entity_keys = {k: v for k, v in scope.items() if k.startswith("workspace_entity")}
            if entity_keys:
                args = {**args, **entity_keys}
            if scope.get("workspace_id") and intent == INTENT_AGENT:
                args = {**args, "workspace_id": scope["workspace_id"]}
        payload: dict[str, object] = {
            "contract_version": COMMAND_ROUTED_VERSION,
            "text": text,
            "intent": intent,
            "args": args,
            "status": "pending",
            "metadata": {"executing": False, "source_router": self.name},
        }
        if scope:
            payload.update(scope)
        self._bus.publish(COMMAND_ROUTED, payload, source=self.name)

    @staticmethod
    def _classify(text: str) -> tuple[str, dict[str, str]]:
        stripped = text.strip()
        lower = stripped.lower()
        if lower in _VIEW_ALIASES:
            return INTENT_NAVIGATE, {"view": _VIEW_ALIASES[lower]}
        if text.startswith(">"):
            return INTENT_SHELL, {"command": text[1:].strip()}
        if lower.startswith("note:"):
            return INTENT_NOTE_SEARCH, {"query": text[5:].strip()}
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
            return INTENT_AGENT, {"task": role or "demo", "spawn_role": role, "spawn_mode": "single"}
        if lower.startswith("agents:"):
            body = stripped[7:].strip().lower()
            if body in {"", "demo", "multi", "multi-demo"}:
                return INTENT_AGENT, {"task": "multi-demo", "spawn_mode": "multi"}
            if body in {"pipeline demo", "pipeline", "pipeline-demo"}:
                return INTENT_AGENT, {"task": "pipeline-demo", "spawn_mode": "pipeline"}
            return INTENT_AGENT, {"task": body, "spawn_mode": "multi"}
        if lower.startswith("agent:"):
            return INTENT_AGENT, {"task": text[6:].strip() or "demo", "spawn_mode": "single"}
        if lower in {"agent demo", "supervised agent demo", "multi-agent demo", "agents demo"}:
            return INTENT_AGENT, {"task": "demo", "spawn_mode": "single"}
        for verb in _SHELL_VERBS:
            if lower == verb.strip() or lower.startswith(verb):
                return INTENT_SHELL, {"command": stripped}
        return INTENT_CHAT, {"prompt": text}
