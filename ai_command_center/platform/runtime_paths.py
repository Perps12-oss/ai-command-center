"""Runtime storage paths for app-scoped data."""

from __future__ import annotations

import os
from pathlib import Path


def get_runtime_data_dir() -> Path:
    """Application data directory (not in repo)."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise OSError("APPDATA environment variable is not set")
    path = Path(appdata) / "AICommandCenter"
    path.mkdir(parents=True, exist_ok=True)
    return path
