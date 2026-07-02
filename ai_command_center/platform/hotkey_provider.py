"""Platform hotkey abstraction (Track 6 — Windows first, Linux-ready interface)."""

from __future__ import annotations

from typing import Protocol

from ai_command_center.utils import hotkey as _hotkey


class HotkeyProvider(Protocol):
    def register(self, combo: str, callback) -> tuple[bool, str]:
        ...

    def validate(self, combo: str) -> tuple[bool, str]:
        ...


class WindowsHotkeyProvider:
    """Delegates to keyboard-based global hotkey utilities."""

    def register(self, combo: str, callback) -> tuple[bool, str]:
        return _hotkey.register_hotkey(combo, callback)

    def validate(self, combo: str) -> tuple[bool, str]:
        return _hotkey.validate_hotkey(combo)


def get_hotkey_provider() -> HotkeyProvider:
    return WindowsHotkeyProvider()
