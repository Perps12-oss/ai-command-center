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
    """Application data directory (not in repo)."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise OSError("APPDATA environment variable is not set")
    path = Path(appdata) / "AICommandCenter"
    path.mkdir(parents=True, exist_ok=True)
    return path
