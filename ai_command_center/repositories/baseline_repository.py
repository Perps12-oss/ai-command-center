"""Baseline metrics file repository."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class BaselineRepository:
    """Owns baseline file read/write operations."""

    def __init__(self, runtime_dir: Path) -> None:
        self._path = runtime_dir / "baseline.json"

    @property
    def path(self) -> Path:
        return self._path

    def write(self, payload: dict[str, Any]) -> Path:
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self._path

    def read(self) -> dict[str, Any] | None:
        if not self._path.is_file():
            return None
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
