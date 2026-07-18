"""Domain-agnostic graph edge visual contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ArrowDir = Literal["none", "forward", "backward", "both"]


@dataclass(slots=True)
class GraphEdgeVisual:
    """Renderable edge — no workflow/world-model domain types."""

    edge_id: str
    source_id: str
    target_id: str
    color: str = "#4a4a6a"
    width: int = 2
    arrow: ArrowDir = "forward"
    label: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    @staticmethod
    def make_id(source_id: str, target_id: str) -> str:
        return f"{source_id}->{target_id}"


__all__ = ["GraphEdgeVisual", "ArrowDir"]
