"""OS Palette provider contract.

Defines the provider interface and command model used by ``OSPalette``.
Providers are UI-layer projections: they read ``AppState`` and return
``PaletteCommand`` objects whose ``action`` closures publish existing UI
intents (``UI_NAVIGATE``, ``UI_OPEN_CHAT``, ``UI_LAUNCH_RESOURCE``, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class PaletteCommand:
    """A single item in the OS palette."""

    label: str = ""
    description: str = ""
    action: Callable[[], None] | None = None
    section: str = ""
    command_id: str = ""


class PaletteProvider(ABC):
    """Base class for palette command providers.

    Implementations return ``PaletteCommand`` instances for the current
    ``AppState`` snapshot. Lower ``priority`` values sort first.
    """

    name: str = ""
    priority: int = 100

    @abstractmethod
    def get_commands(self, app_state: Any) -> list[PaletteCommand]:
        """Return commands for the given AppState snapshot."""


@dataclass
class StaticPaletteProvider(PaletteProvider):
    """Provider that returns a fixed list of commands."""

    commands: list[PaletteCommand] = field(default_factory=list)
    name: str = "Static"
    priority: int = 0

    def get_commands(self, app_state: Any) -> list[PaletteCommand]:
        return list(self.commands)


@dataclass
class WorkspaceOSPaletteProvider(PaletteProvider):
    """Provider that builds launch/chat commands from Workspace OS entities."""

    get_entities: Callable[[Any], tuple[Any, ...]] = field(default=lambda _s: ())
    on_open_chat: Callable[[dict[str, Any]], None] = field(default=lambda _p: None)
    on_launch: Callable[[dict[str, Any]], None] = field(default=lambda _p: None)
    name: str = "Workspace"
    priority: int = 50

    def get_commands(self, app_state: Any) -> list[PaletteCommand]:
        commands: list[PaletteCommand] = []
        for entity in self.get_entities(app_state):
            meta = dict(getattr(entity, "metadata", ()))
            resource_type = meta.get("resource_type")
            value = meta.get("url") or meta.get("path") or meta.get("command") or ""
            chat_payload: dict[str, Any] = {
                "entity_id": str(getattr(entity, "entity_id", "")),
                "entity_type": str(getattr(entity, "entity_type", "")),
                "title": str(getattr(entity, "title", "")),
            }
            if meta.get("description"):
                chat_payload["description"] = str(meta["description"])
            if meta.get("url"):
                chat_payload["url"] = str(meta["url"])
            elif meta.get("path"):
                chat_payload["path"] = str(meta["path"])
            elif meta.get("command"):
                chat_payload["path"] = str(meta["command"])
            label = f"💬  Chat: {getattr(entity, 'title', '') or getattr(entity, 'entity_id', '')}"
            desc = f"Open chat attached to {getattr(entity, 'entity_type', 'entity')}"
            commands.append(
                PaletteCommand(
                    label=label,
                    description=desc,
                    action=lambda p=chat_payload: self.on_open_chat(p),
                    section=self.name,
                    command_id=f"chat:{chat_payload['entity_id']}",
                )
            )
            if not resource_type or not value:
                continue
            launch_payload = {
                "resource_id": str(getattr(entity, "entity_id", "")),
                "resource_type": resource_type,
                "value": value,
            }
            commands.append(
                PaletteCommand(
                    label=f"🚀  {getattr(entity, 'title', '')}",
                    description=f"Workspace OS {getattr(entity, 'entity_type', '')} ({resource_type})",
                    action=lambda p=launch_payload: self.on_launch(p),
                    section=self.name,
                    command_id=f"launch:{launch_payload['resource_id']}",
                )
            )
        return commands


__all__ = ["PaletteCommand", "PaletteProvider", "StaticPaletteProvider", "WorkspaceOSPaletteProvider"]
