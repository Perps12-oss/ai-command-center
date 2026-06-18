"""Routes ui.command intents to typed command.routed events (Phase 3 handlers attach here)."""

from __future__ import annotations

from typing import Callable

from ai_command_center.core.event_bus import Event
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
INTENT_UNKNOWN = "unknown"


class CommandRouterService(BaseService):
    """
    Intent detection + routing only.

    MUST NOT: plan, reason, orchestrate, or run multi-step agent loops.
    See docs/PHASE3.md.
    """

    name = "command_router"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(self._bus.subscribe("ui.command", self._on_ui_command))

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
        self._bus.publish(
            "command.routed",
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
        lower = text.lower()
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
        return INTENT_CHAT, {"prompt": text}
