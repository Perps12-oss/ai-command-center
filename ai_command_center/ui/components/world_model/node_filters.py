"""Shared World Model node filter helpers and filter bar (PR-UI-E08)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.world_model_snapshot import NodeSnapshot
from ai_command_center.ui.design_system import theme_v2 as T

TYPE_OPTIONS = (
    "all",
    "workspace",
    "card",
    "resource",
    "note",
    "goal",
    "task",
    "file",
    "service",
)
STATUS_OPTIONS = ("all", "active", "paused", "complete", "failed", "cancelled")
SORT_OPTIONS = ("name", "type", "status")


@dataclass(frozen=True, slots=True)
class NodeFilterState:
    """Immutable filter projection for list + graph panels."""

    search: str = ""
    type_filter: str = "all"
    status_filter: str = "all"
    sort_key: str = "name"


def node_status(node: NodeSnapshot) -> str:
    for key, value in node.attributes:
        if key.lower() == "status":
            return value
    return "active"


def filter_nodes(
    nodes: Sequence[NodeSnapshot],
    state: NodeFilterState,
) -> list[NodeSnapshot]:
    """Apply search / type / status / sort to world-model nodes."""
    result = list(nodes)
    type_filter = (state.type_filter or "all").strip().lower()
    status_filter = (state.status_filter or "all").strip().lower()
    search = (state.search or "").strip().lower()
    if type_filter != "all":
        result = [n for n in result if n.node_type == type_filter]
    if status_filter != "all":
        result = [n for n in result if node_status(n) == status_filter]
    if search:
        result = [
            n
            for n in result
            if search in n.label.lower()
            or search in n.node_id.lower()
            or search in n.node_type.lower()
        ]
    key = (state.sort_key or "name").strip().lower()
    if key == "type":
        result.sort(key=lambda n: (n.node_type, n.label.lower()))
    elif key == "status":
        result.sort(key=lambda n: (node_status(n), n.label.lower()))
    else:
        result.sort(key=lambda n: n.label.lower())
    return result


class NodeFiltersBar(ctk.CTkFrame):
    """Shared filter controls for World Model Explorer."""

    def __init__(
        self,
        master: Any,
        *,
        on_change: Callable[[NodeFilterState], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.WORLD_TEAL,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
            **kwargs,
        )
        self._on_change = on_change
        self._state = NodeFilterState()

        ctk.CTkLabel(
            self,
            text="Filters",
            font=T.FONT_HEADER,
            text_color=T.WORLD_TEAL,
            anchor="w",
        ).pack(side="left", padx=(T.PAD, 8), pady=8)

        self._search_entry = ctk.CTkEntry(
            self,
            placeholder_text="Search entities…",
            font=T.FONT_SMALL,
            height=28,
            width=180,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
        )
        self._search_entry.pack(side="left", padx=(0, 6), pady=8)
        self._search_entry.bind("<KeyRelease>", lambda _e: self._emit())

        self._type_menu = ctk.CTkOptionMenu(
            self,
            values=list(TYPE_OPTIONS),
            width=100,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            button_color=T.WORLD_TEAL,
            command=lambda _v: self._emit(),
        )
        self._type_menu.set("all")
        self._type_menu.pack(side="left", padx=(0, 6), pady=8)

        self._status_menu = ctk.CTkOptionMenu(
            self,
            values=list(STATUS_OPTIONS),
            width=100,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            button_color=T.WORLD_TEAL,
            command=lambda _v: self._emit(),
        )
        self._status_menu.set("all")
        self._status_menu.pack(side="left", padx=(0, 6), pady=8)

        self._sort_menu = ctk.CTkOptionMenu(
            self,
            values=list(SORT_OPTIONS),
            width=90,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            button_color=T.WORLD_TEAL,
            command=lambda _v: self._emit(),
        )
        self._sort_menu.set("name")
        self._sort_menu.pack(side="left", padx=(0, T.PAD), pady=8)

    @property
    def state(self) -> NodeFilterState:
        return self._state

    def set_state(self, state: NodeFilterState) -> None:
        self._state = state
        self._search_entry.delete(0, "end")
        if state.search:
            self._search_entry.insert(0, state.search)
        self._type_menu.set(state.type_filter or "all")
        self._status_menu.set(state.status_filter or "all")
        self._sort_menu.set(state.sort_key or "name")

    def _emit(self) -> None:
        self._state = NodeFilterState(
            search=str(self._search_entry.get() or ""),
            type_filter=str(self._type_menu.get() or "all"),
            status_filter=str(self._status_menu.get() or "all"),
            sort_key=str(self._sort_menu.get() or "name"),
        )
        if self._on_change is not None:
            self._on_change(self._state)


__all__ = [
    "TYPE_OPTIONS",
    "STATUS_OPTIONS",
    "SORT_OPTIONS",
    "NodeFilterState",
    "NodeFiltersBar",
    "node_status",
    "filter_nodes",
]
