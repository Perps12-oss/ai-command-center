"""Runtime storage paths for app-scoped data."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """True when running from a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def get_install_dir() -> Path:
    """Directory containing the application executable or repo root in dev."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def get_runtime_data_dir() -> Path:
    """Application data directory (not in repo), selected by host OS."""
    path = get_platform_data_root() / "AICommandCenter"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_platform_data_root() -> Path:
    """Return the OS-specific user data root."""
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise OSError("APPDATA environment variable is not set")
        return Path(appdata)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".local" / "share"
