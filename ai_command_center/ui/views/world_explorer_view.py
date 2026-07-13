"""WorldExplorerView — browse and inspect World Model nodes.

Architecture contract:
- Pure display widget. No repository access. No service calls.
- Reads from WorldModelState (AppState layer).
- Publishes WORLD_MODEL_NODE_SELECTED via EventBus on user selection.
- Publishes WORLD_MODEL_DEPENDENCY_INSPECT when user opens DependencyInspector.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    WORLD_MODEL_DEPENDENCY_INSPECT,
    WORLD_MODEL_GRAPH_REFRESHED,
    WORLD_MODEL_NODE_DESELECTED,
    WORLD_MODEL_NODE_SELECTED,
)
from ai_command_center.core.state.world_model_state import NodeSummary, WorldModelState
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children

_TYPE_ICON = {
    "workspace": "◈",
    "card": "▢",
    "resource": "🔗",
    "note": "📝",
    "goal": "🎯",
    "task": "✓",
    "file": "📄",
    "service": "⚙",
}
_DEFAULT_ICON = "●"

_TYPE_COLORS = {
    "workspace": "#3B82F6",
    "goal": "#22C55E",
    "task": "#EAB308",
    "resource": "#A78BFA",
    "note": "#F472B6",
    "service": "#00FFFF",
}


def _icon(node_type: str) -> str:
    return _TYPE_ICON.get(node_type, _DEFAULT_ICON)


def _color(node_type: str) -> str:
    return _TYPE_COLORS.get(node_type, T.TEXT_SECONDARY)


class _NodeRow(ctk.CTkFrame):
    """Single node row in the explorer list."""

    def __init__(
        self,
        master: Any,
        node: NodeSummary,
        selected: bool,
        on_click: Callable[[], None],
        on_inspect: Callable[[], None],
    ) -> None:
        border = T.ACCENT_DEFAULT if selected else T.BG_GLASS_BORDER
        bg = T.BG_INPUT if selected else T.BG_GLASS
        super().__init__(
            master,
            fg_color=bg,
            border_color=border,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
        )
        self.bind("<Button-1>", lambda _e: on_click())

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=6)
        left.bind("<Button-1>", lambda _e: on_click())

        icon_lbl = ctk.CTkLabel(
            left,
            text=_icon(node.node_type),
            font=(T.FONT_FAMILY, 14),
            text_color=_color(node.node_type),
            width=22,
            anchor="w",
        )
        icon_lbl.pack(side="left")
        icon_lbl.bind("<Button-1>", lambda _e: on_click())

        label = ctk.CTkLabel(
            left,
            text=node.label,
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY if selected else T.TEXT_SECONDARY,
            anchor="w",
        )
        label.pack(side="left", padx=(4, 0))
        label.bind("<Button-1>", lambda _e: on_click())

        type_lbl = ctk.CTkLabel(
            left,
            text=node.node_type,
            font=(T.FONT_FAMILY, 9),
            text_color=_color(node.node_type),
            anchor="w",
        )
        type_lbl.pack(side="left", padx=(8, 0))
        type_lbl.bind("<Button-1>", lambda _e: on_click())

        ctk.CTkButton(
            self,
            text="⋯",
            width=26,
            height=22,
            fg_color="transparent",
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            font=(T.FONT_FAMILY, 12),
            command=on_inspect,
        ).pack(side="right", padx=(0, 6))


class _FilterBar(ctk.CTkFrame):
    def __init__(self, master: Any, on_change: Callable[[str, str], None]) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_change = on_change

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._emit())

        ctk.CTkEntry(
            self,
            textvariable=self._search_var,
            placeholder_text="Filter nodes…",
            font=T.FONT_SMALL,
            height=30,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        self._type_var = tk.StringVar(value="all")
        self._type_menu = ctk.CTkOptionMenu(
            self,
            variable=self._type_var,
            values=["all", "workspace", "card", "resource", "note", "goal", "task", "file", "service"],
            width=110,
            height=30,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            button_color=T.BG_GLASS_BORDER,
            command=lambda _v: self._emit(),
        )
        self._type_menu.pack(side="left")

    def _emit(self) -> None:
        self._on_change(self._search_var.get(), self._type_var.get())


class WorldExplorerView(ctk.CTkFrame):
    """World Model node browser.

    Left panel: filter bar + scrollable node list.
    Right panel: node detail card with attributes table.
    """

    def __init__(self, master: Any, bus: EventBus, state: WorldModelState) -> None:
        super().__init__(master, fg_color=T.BG_DEEP)
        self._bus = bus
        self._state = state
        self._filter_text = ""
        self._filter_type = "all"
        self._unsub: Callable[[], None] | None = None
        self._build()
        self._unsub = state.add_listener(self._on_state_change)
        self._render_nodes()

    def destroy(self) -> None:
        if self._unsub is not None:
            self._unsub()
        super().destroy()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=T.BG_PANEL, height=48, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="◈  World Explorer",
            font=T.FONT_HEADER,
            text_color=T.TEXT_HEADING,
            anchor="w",
        ).pack(side="left", padx=16, pady=10)

        ctk.CTkButton(
            header,
            text="↻ Refresh",
            width=80,
            height=28,
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_SECONDARY,
            font=T.FONT_SMALL,
            command=self._request_refresh,
        ).pack(side="right", padx=12, pady=10)

        filter_frame = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0)
        filter_frame.pack(fill="x", padx=12, pady=(8, 4))
        _FilterBar(filter_frame, on_change=self._on_filter_change).pack(fill="x")

        self._pane = ctk.CTkFrame(self, fg_color="transparent")
        self._pane.pack(fill="both", expand=True, padx=12, pady=(4, 12))

        self._list_frame = ctk.CTkScrollableFrame(
            self._pane,
            fg_color=T.BG_PANEL,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
            label_text="",
        )
        self._list_frame.pack(side="left", fill="both", expand=True)

        self._detail_frame = ctk.CTkFrame(
            self._pane,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
            width=260,
        )
        self._detail_frame.pack(side="right", fill="y", padx=(12, 0))
        self._detail_frame.pack_propagate(False)
        self._render_detail(None)

    def _on_filter_change(self, text: str, type_filter: str) -> None:
        self._filter_text = text.lower()
        self._filter_type = type_filter
        self._render_nodes()

    def _request_refresh(self) -> None:
        self._bus.publish(WORLD_MODEL_GRAPH_REFRESHED, {}, source="world_explorer_view")

    def _on_state_change(self) -> None:
        self._render_nodes()
        sel = self._state.selected_node
        self._render_detail(sel)

    def _filtered_nodes(self) -> list[NodeSummary]:
        nodes = self._state.nodes
        if self._filter_type != "all":
            nodes = [n for n in nodes if n.node_type == self._filter_type]
        if self._filter_text:
            nodes = [n for n in nodes if self._filter_text in n.label.lower() or self._filter_text in n.node_id.lower()]
        return sorted(nodes, key=lambda n: (n.node_type, n.label))

    def _render_nodes(self) -> None:
        clear_children(self._list_frame)
        nodes = self._filtered_nodes()
        sel_id = self._state.selected_node_id
        if not nodes:
            ctk.CTkLabel(
                self._list_frame,
                text="No nodes in World Model.\nMutations will appear here.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                justify="center",
            ).pack(expand=True, pady=40)
            return
        for node in nodes:
            _NodeRow(
                self._list_frame,
                node=node,
                selected=(node.node_id == sel_id),
                on_click=lambda nid=node.node_id: self._select_node(nid),
                on_inspect=lambda nid=node.node_id: self._inspect_node(nid),
            ).pack(fill="x", pady=2, padx=2)

    def _render_detail(self, node: NodeSummary | None) -> None:
        clear_children(self._detail_frame)
        if node is None:
            ctk.CTkLabel(
                self._detail_frame,
                text="Select a node\nto inspect",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                justify="center",
            ).pack(expand=True)
            return

        ctk.CTkLabel(
            self._detail_frame,
            text=f"{_icon(node.node_type)}  {node.label}",
            font=T.FONT_HEADER,
            text_color=_color(node.node_type),
            anchor="w",
            wraplength=240,
        ).pack(fill="x", padx=12, pady=(12, 2))

        ctk.CTkLabel(
            self._detail_frame,
            text=node.node_type.upper(),
            font=(T.FONT_FAMILY, 9, "bold"),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=12)

        ctk.CTkLabel(
            self._detail_frame,
            text=f"ID: {node.node_id}",
            font=T.FONT_MONO,
            text_color=T.TEXT_MUTED,
            anchor="w",
            wraplength=240,
        ).pack(fill="x", padx=12, pady=(4, 8))

        if node.attributes:
            sep = ctk.CTkFrame(self._detail_frame, fg_color=T.BG_GLASS_BORDER, height=1)
            sep.pack(fill="x", padx=12, pady=(0, 8))
            ctk.CTkLabel(
                self._detail_frame,
                text="ATTRIBUTES",
                font=(T.FONT_FAMILY, 9, "bold"),
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=12)
            for key, val in list(node.attributes.items())[:12]:
                row = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=1)
                ctk.CTkLabel(
                    row, text=f"{key}:", font=T.FONT_SMALL,
                    text_color=T.TEXT_MUTED, width=80, anchor="w",
                ).pack(side="left")
                ctk.CTkLabel(
                    row, text=str(val)[:40], font=T.FONT_SMALL,
                    text_color=T.TEXT_PRIMARY, anchor="w",
                ).pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            self._detail_frame,
            text="Open Dependencies",
            font=T.FONT_SMALL,
            height=28,
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            command=lambda: self._inspect_node(node.node_id),
        ).pack(fill="x", padx=12, pady=(12, 4))

        ctk.CTkButton(
            self._detail_frame,
            text="Deselect",
            font=T.FONT_SMALL,
            height=28,
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            command=self._deselect,
        ).pack(fill="x", padx=12, pady=(0, 12))

    def _select_node(self, node_id: str) -> None:
        self._bus.publish(
            WORLD_MODEL_NODE_SELECTED,
            {"node_id": node_id},
            source="world_explorer_view",
        )

    def _deselect(self) -> None:
        self._bus.publish(WORLD_MODEL_NODE_DESELECTED, {}, source="world_explorer_view")

    def _inspect_node(self, node_id: str) -> None:
        self._bus.publish(
            WORLD_MODEL_DEPENDENCY_INSPECT,
            {"node_id": node_id},
            source="world_explorer_view",
        )
