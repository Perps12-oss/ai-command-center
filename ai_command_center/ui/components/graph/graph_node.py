"""Domain-agnostic graph node visual contract.

Workflow, World Model, and Relationship views project domain data into
``GraphNodeVisual``; rendering stays inside the shared graph primitive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

NodeShape = Literal["rect", "oval"]


@dataclass(slots=True)
class GraphNodeVisual:
    """Renderable node — no workflow/world-model domain types."""

    node_id: str
    x: float
    y: float
    label: str = ""
    width: float = 120.0
    height: float = 48.0
    shape: NodeShape = "rect"
    fill: str = "#1a1a2e"
    outline: str = "#4a4a6a"
    outline_width: int = 1
    text_color: str = "#e0e0e0"
    font_size: int = 10
    font_bold: bool = False
    status_dot_color: str = ""
    badge: str = ""
    badge_color: str = ""
    secondary_label: str = ""
    secondary_color: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Axis-aligned bounding box (x0, y0, x1, y1)."""
        if self.shape == "oval":
            r = max(self.width, self.height) / 2.0
            return (self.x - r, self.y - r, self.x + r, self.y + r)
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def contains(self, canvas_x: float, canvas_y: float) -> bool:
        x0, y0, x1, y1 = self.bounds
        return x0 <= canvas_x <= x1 and y0 <= canvas_y <= y1

    def center(self) -> tuple[float, float]:
        if self.shape == "oval":
            return (self.x, self.y)
        return (self.x + self.width / 2.0, self.y + self.height / 2.0)

    def anchor_right(self) -> tuple[float, float]:
        if self.shape == "oval":
            r = max(self.width, self.height) / 2.0
            return (self.x + r, self.y)
        return (self.x + self.width, self.y + self.height / 2.0)

    def anchor_left(self) -> tuple[float, float]:
        if self.shape == "oval":
            r = max(self.width, self.height) / 2.0
            return (self.x - r, self.y)
        return (self.x, self.y + self.height / 2.0)


__all__ = ["GraphNodeVisual", "NodeShape"]
