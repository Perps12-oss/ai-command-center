"""Repository for UI layout and spatial spec assets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SpatialRepository:
    """Owns layout, background, and spatial spec loading for the UI layer."""

    def __init__(self, design_dir: str | Path | None = None) -> None:
        self._design_dir = Path(design_dir) if design_dir is not None else Path(__file__).resolve().parents[1] / ".." / "design"
        self._design_dir = self._design_dir.resolve()

    def load_background_layer(self) -> dict[str, Any]:
        return self._load_json(self._design_dir / "BACKGROUND_LAYER.json")

    def load_layout_schema(self) -> dict[str, Any]:
        return self._load_json(self._design_dir / "LAYOUT_SCHEMA.json")

    def load_motion_bindings(self) -> dict[str, Any]:
        return self._load_json(self._design_dir / "MOTION_BINDINGS.json")

    def load_style_lock(self) -> dict[str, Any]:
        return self._load_json(self._design_dir / "STYLE_LOCK.json")

    def load_spatial_map(self) -> dict[str, Any]:
        return self._load_json(self._design_dir / "SPATIAL_MAP.json")

    def _load_json(self, path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path.name} must be a JSON object")
        return data
