"""Routes ui.command intents to typed command.routed events (Phase 3 handlers attach here)."""

from __future__ import annotations

from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import COMMAND_ROUTED, UI_COMMAND
from ai_command_center.core.contracts import COMMAND_ROUTED_VERSION
from ai_command_center.services.base import BaseService

# Intents consumed by Phase 3+ services
INTENT_CHAT = "chat"
INTENT_SHELL = "shell"
INTENT_NOTE_SEARCH = "note_search"
INTENT_NOTE_NEW = "note_new"
INTENT_NAVIGATE = "navigate"
INTENT_MEMORY_REMEMBER = "memory_remember"
INTENT_MEMORY_SELECT = "memory_select"
INTENT_AGENT = "agent"
INTENT_UNKNOWN = "unknown"

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

    def _on_ui_command(self, event: Event) -> None:
        text = str(event.payload.get("text", "")).strip()
        if not text:
            return
        intent, args = self._classify(text)
        clipboard = event.payload.get("clipboard")
        if clipboard and intent == INTENT_CHAT:
            args = {**args, "clipboard": str(clipboard)}
        workspace_entity_id = str(event.payload.get("workspace_entity_id", "")).strip()
        if workspace_entity_id and intent == INTENT_CHAT:
            args = {
                **args,
                "workspace_entity_id": workspace_entity_id,
                "workspace_entity_type": str(event.payload.get("workspace_entity_type", "")),
                "workspace_entity_title": str(event.payload.get("workspace_entity_title", "")),
            }
            for key in ("workspace_entity_description", "workspace_entity_url", "workspace_entity_path"):
                value = str(event.payload.get(key, "")).strip()
                if value:
                    args[key] = value
        self._bus.publish(
            COMMAND_ROUTED,
            {
                "contract_version": COMMAND_ROUTED_VERSION,
                "text": text,
                "intent": intent,
                "args": args,
                "status": "pending",
                "metadata": {"executing": False, "source_router": self.name},
            },
            source=self.name,
        )

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
        if lower.startswith("agent:"):
            return INTENT_AGENT, {"task": text[6:].strip() or "demo"}
        if lower in {"agent demo", "supervised agent demo"}:
            return INTENT_AGENT, {"task": "demo"}
        for verb in _SHELL_VERBS:
            if lower == verb.strip() or lower.startswith(verb):
                return INTENT_SHELL, {"command": stripped}
        return INTENT_CHAT, {"prompt": text}
