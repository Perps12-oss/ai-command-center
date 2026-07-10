"""NodeLibraryPalette — draggable node type palette for workflow graph.

P4.1: Node library palette with draggable node types
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

__all__ = ["NodeLibraryPalette", "NodeTypeCard", "NODE_TYPES"]


# Node type definitions with icons and descriptions
NODE_TYPES = [
    {
        "id": "planning",
        "label": "Planning",
        "icon": "📋",
        "description": "Create plans and schedules",
        "color": "#3B82F6",
    },
    {
        "id": "provider",
        "label": "Provider",
        "icon": "🤖",
        "description": "AI model interaction",
        "color": "#10B981",
    },
    {
        "id": "tool",
        "label": "Tool",
        "icon": "🔧",
        "description": "Execute tools",
        "color": "#F59E0B",
    },
    {
        "id": "artifact",
        "label": "Artifact",
        "icon": "📄",
        "description": "Create or read artifacts",
        "color": "#8B5CF6",
    },
    {
        "id": "inspector",
        "label": "Inspector",
        "icon": "🔍",
        "description": "Inspect entities",
        "color": "#EC4899",
    },
    {
        "id": "automation",
        "label": "Automation",
        "icon": "⚡",
        "description": "Automated workflow",
        "color": "#06B6D4",
    },
    {
        "id": "memory",
        "label": "Memory",
        "icon": "🧠",
        "description": "Memory operations",
        "color": "#F97316",
    },
    {
        "id": "external",
        "label": "External",
        "icon": "🌐",
        "description": "External capability",
        "color": "#6366F1",
    },
]


class NodeTypeCard(ctk.CTkFrame):
    """A single node type card in the palette."""

    def __init__(
        self,
        master: Any,
        node_type: dict,
        on_drag_start: Callable[[dict], None],
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_GLASS, corner_radius=6, **kwargs)
        self._node_type = node_type
        self._on_drag_start = on_drag_start

        self.configure(height=56, cursor="hand1")
        self.pack_propagate(False)

        # Icon
        icon_label = ctk.CTkLabel(
            self,
            text=node_type["icon"],
            font=(T.FONT_FAMILY, 16),
            width=36,
        )
        icon_label.pack(side="left", padx=(8, 4), pady=8)

        # Text content
        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, pady=6)

        label = ctk.CTkLabel(
            text_frame,
            text=node_type["label"],
            font=(T.FONT_FAMILY, 11, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        label.pack(fill="x")

        desc = ctk.CTkLabel(
            text_frame,
            text=node_type["description"],
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
            wraplength=100,
        )
        desc.pack(fill="x")

        # Bind drag events
        self.bind("<Button-1>", self._on_drag_start)
        self.bind("<B1-Motion>", self._on_drag)
        icon_label.bind("<Button-1>", self._on_drag_start)
        icon_label.bind("<B1-Motion>", self._on_drag)
        label.bind("<Button-1>", self._on_drag_start)
        label.bind("<B1-Motion>", self._on_drag)
        desc.bind("<Button-1>", self._on_drag_start)
        desc.bind("<B1-Motion>", self._on_drag)

    def _on_drag_start(self, event: Any) -> None:
        self._on_drag_start(self._node_type)

    def _on_drag(self, event: Any) -> None:
        pass  # Drag handling is done at the palette level


class NodeLibraryPalette(ctk.CTkFrame):
    """Sidebar palette showing available node types for the workflow graph."""

    def __init__(
        self,
        master: Any,
        on_node_add: Callable[[str, float, float], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, **kwargs)
        self._on_node_add = on_node_add or (lambda _type, _x, _y: None)
        self._selected_node_type: dict | None = None

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent", height=36)
        header.pack(fill="x", padx=12, pady=(10, 4))

        title = ctk.CTkLabel(
            header,
            text="Node Library",
            font=(T.FONT_FAMILY, 11, "bold"),
            text_color=T.TEXT_SECONDARY,
        )
        title.pack(side="left")

        # Node type list
        self._scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=T.BG_GLASS,
            scrollbar_button_hover_color=T.BG_GLASS_BORDER,
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=8, pady=4)

        for node_type in NODE_TYPES:
            card = NodeTypeCard(
                self._scroll_frame,
                node_type=node_type,
                on_drag_start=self._on_drag_start,
            )
            card.pack(fill="x", pady=2)

        # Drop hint
        hint = ctk.CTkLabel(
            self,
            text="Drag nodes to canvas\nor double-click to add",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            justify="center",
        )
        hint.pack(side="bottom", pady=8)

    def _on_drag_start(self, node_type: dict) -> None:
        self._selected_node_type = node_type
        self._on_node_add(node_type["id"], 0, 0)  # Coordinates filled by drop

    def add_node_at_position(self, node_type_id: str, x: float, y: float) -> None:
        """Called when a node is dropped on the canvas."""
        self._on_node_add(node_type_id, x, y)


__all__ = ["NodeLibraryPalette", "NODE_TYPES"]
