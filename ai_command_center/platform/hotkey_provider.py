"""Platform hotkey abstraction (Windows / Linux keyboard hook; graceful no-op elsewhere)."""

from __future__ import annotations

import sys
from typing import Protocol

from ai_command_center.utils import hotkey as _hotkey


class HotkeyProvider(Protocol):
    """Register global overlay hotkeys without binding the UI layer to a platform API."""

    @property
    def supported(self) -> bool:
        """True when the provider can attempt registration on this host."""

    def register(self, combo: str, callback) -> tuple[bool, str]:
        ...

    def validate(self, combo: str) -> tuple[bool, str]:
        ...


class _KeyboardHotkeyProvider:
    """Shared keyboard-library backend used on Windows and Linux."""

    @property
    def supported(self) -> bool:
        ok, _ = _hotkey.validate_hotkey()
        return ok

    def register(self, combo: str, callback) -> tuple[bool, str]:
        return _hotkey.register_hotkey(combo, callback)

    def validate(self, combo: str) -> tuple[bool, str]:
        return _hotkey.validate_hotkey(combo)


class WindowsHotkeyProvider(_KeyboardHotkeyProvider):
    """Delegates to keyboard-based global hotkey utilities on Windows."""


class LinuxHotkeyProvider(_KeyboardHotkeyProvider):
    """Delegates to keyboard-based global hotkey utilities on Linux."""


class MacOSHotkeyProvider:
    """Placeholder until CGEvent tap integration lands (Program 4 packaging track)."""

    @property
    def supported(self) -> bool:
        return False

    def register(self, combo: str, callback) -> tuple[bool, str]:
        return False, f"macOS hotkeys not supported yet ({combo})"

    def validate(self, combo: str) -> tuple[bool, str]:
        return False, "macOS hotkeys not supported yet"


class NoOpHotkeyProvider:
    """Graceful fallback when the host OS has no hotkey backend."""

    def __init__(self, platform_name: str | None = None) -> None:
        self._platform = platform_name or sys.platform

    @property
    def supported(self) -> bool:
        return False

    def register(self, combo: str, callback) -> tuple[bool, str]:
        return False, f"hotkeys unsupported on {self._platform} ({combo})"

    def validate(self, combo: str) -> tuple[bool, str]:
        return False, f"hotkeys unsupported on {self._platform}"


def get_hotkey_provider() -> HotkeyProvider:
    if sys.platform == "win32":
        return WindowsHotkeyProvider()
    if sys.platform == "linux":
        return LinuxHotkeyProvider()
    if sys.platform == "darwin":
        return MacOSHotkeyProvider()
    return NoOpHotkeyProvider(sys.platform)
