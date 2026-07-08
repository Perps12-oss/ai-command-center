"""UI package."""

from __future__ import annotations

from typing import Any

__all__ = ["CommandPaletteApp"]


def __getattr__(name: str) -> Any:
    if name == "CommandPaletteApp":
        from ai_command_center.ui.app import CommandPaletteApp

        return CommandPaletteApp
    raise AttributeError(name)
