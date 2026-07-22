"""Thin World Model graph surface — BaseGraphCanvas specialization (no new engine)."""

from __future__ import annotations

from typing import Any

from ai_command_center.ui.components.graph import BaseGraphCanvas
from ai_command_center.ui.design_system import theme_v2 as T


class WorldGraphCanvas(BaseGraphCanvas):
    """World-model defaults on the shared graph primitive.

    ADR / gate: must remain a thin subclass of ``BaseGraphCanvas``.
    Do not add a private drawing engine.
    """

    def __init__(self, master: Any, **kwargs: Any) -> None:
        kwargs.setdefault("enable_zoom", True)
        kwargs.setdefault("enable_pan", True)
        kwargs.setdefault("enable_multi_select", False)
        kwargs.setdefault("enable_node_drag", False)
        kwargs.setdefault("enable_selection_box", False)
        kwargs.setdefault("show_scrollbars", False)
        kwargs.setdefault("canvas_bg", T.BG_DEEP)
        kwargs.setdefault(
            "empty_message",
            (
                "No entities in the World Model yet.\n"
                "Entities appear when notes, goals, or workspace activity is indexed.\n"
                "Next: click New Entity or open Goals/Chat to create linked work."
            ),
        )
        super().__init__(master, **kwargs)


__all__ = ["WorldGraphCanvas"]
