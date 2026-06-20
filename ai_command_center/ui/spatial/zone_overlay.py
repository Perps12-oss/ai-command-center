"""L3 zone highlight overlays — disabled (no canvas motion rectangles)."""

from __future__ import annotations

from typing import Any


class ZoneMotionOverlay:
    """No-op overlay — green motion borders removed per design."""

    def __init__(self, mount: Any, page_id: str) -> None:
        self._mount = mount
        self._page_id = page_id

    def trigger(self, event_key: str, intensity: float = 0.5) -> None:
        return
