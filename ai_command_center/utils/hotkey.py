"""Global hotkey registration (Alt+Space default)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

_hotkey_thread: threading.Thread | None = None
_registered = False
_hook_ok = False


def register_hotkey(combo: str, callback: Callable[[], None]) -> tuple[bool, str]:
    """
    Register a global hotkey in a background thread.
    Returns (success, detail_message).
    """
    global _hotkey_thread, _registered, _hook_ok

    if _registered:
        return _hook_ok, "hotkey already registered"

    def _run() -> None:
        global _hook_ok
        try:
            import keyboard

            keyboard.add_hotkey(combo, callback, suppress=False)
            _hook_ok = True
            keyboard.wait()
        except Exception as exc:  # noqa: BLE001
            _hook_ok = False

    _hotkey_thread = threading.Thread(target=_run, name="hotkey-listener", daemon=True)
    _hotkey_thread.start()
    _registered = True

    import time

    time.sleep(0.3)
    if _hook_ok:
        return True, f"registered {combo}"
    return False, f"failed to register {combo} (try running as admin or change hotkey in settings)"


def validate_hotkey(combo: str = "alt+space") -> tuple[bool, str]:
    """Check if keyboard library can load without registering."""
    try:
        import keyboard  # noqa: F401

        return True, f"keyboard library ok; default={combo}"
    except ImportError as exc:
        return False, str(exc)
