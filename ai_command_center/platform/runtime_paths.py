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


def _runtime_data_base_dir() -> Path:
    """OS-specific parent directory for application data (not in repo)."""
    # Support APPDATA override on all platforms for headless/cloud isolation.
    appdata_override = os.environ.get("APPDATA")
    if appdata_override:
        return Path(appdata_override)
    if sys.platform == "win32":
        raise OSError("APPDATA environment variable is not set")
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".local" / "share"


def get_runtime_data_dir() -> Path:
    """Application data directory (not in repo)."""
    path = _runtime_data_base_dir() / "AICommandCenter"
    path.mkdir(parents=True, exist_ok=True)
    return path
