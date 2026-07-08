"""HotkeyProvider platform selection and graceful no-op behavior."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from ai_command_center.platform import hotkey_provider as hp


def test_get_hotkey_provider_windows() -> None:
    with patch.object(sys, "platform", "win32"):
        provider = hp.get_hotkey_provider()
    assert isinstance(provider, hp.WindowsHotkeyProvider)


def test_get_hotkey_provider_linux() -> None:
    with patch.object(sys, "platform", "linux"):
        provider = hp.get_hotkey_provider()
    assert isinstance(provider, hp.LinuxHotkeyProvider)


def test_get_hotkey_provider_macos_is_noop() -> None:
    with patch.object(sys, "platform", "darwin"):
        provider = hp.get_hotkey_provider()
    assert isinstance(provider, hp.MacOSHotkeyProvider)
    ok, detail = provider.register("alt+space", lambda: None)
    assert ok is False
    assert "macOS" in detail


def test_noop_provider_on_unknown_platform() -> None:
    with patch.object(sys, "platform", "freebsd"):
        provider = hp.get_hotkey_provider()
    assert isinstance(provider, hp.NoOpHotkeyProvider)
    assert provider._platform == "freebsd"
    ok, detail = provider.validate("alt+space")
    assert ok is False
    assert "freebsd" in detail


def test_windows_provider_delegates_to_hotkey_utils() -> None:
    provider = hp.WindowsHotkeyProvider()
    callback = MagicMock()
    with patch.object(hp._hotkey, "register_hotkey", return_value=(True, "ok")) as register:
        ok, detail = provider.register("alt+space", callback)
    register.assert_called_once_with("alt+space", callback)
    assert ok is True
    assert detail == "ok"

    with patch.object(hp._hotkey, "validate_hotkey", return_value=(True, "valid")):
        ok, detail = provider.validate("ctrl+shift+w")
    assert ok is True
    assert detail == "valid"
