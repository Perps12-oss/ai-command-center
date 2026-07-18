"""BaseGraphCanvas — shared tkinter graph surface (zoom/pan/selection/draw).

Domain panels project into ``GraphNodeVisual`` / ``GraphEdgeVisual`` and
keep workflow- or world-model-specific behavior outside this primitive.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.components.graph.graph_edge import GraphEdgeVisual
from ai_command_center.ui.components.graph.graph_node import GraphNodeVisual
from ai_command_center.ui.components.graph.graph_selection import GraphSelection
from ai_command_center.ui.design_system import theme_v2 as T


class BaseGraphCanvas(ctk.CTkFrame):
    """Reusable graph rendering surface.

    Responsibilities (shared primitive):
    - node / edge drawing
    - zoom / pan
    - selection (single, ctrl-multi, shift box)
    - hit testing

    Non-responsibilities (domain panels):
    - workflow undo/redo, edge-handle editing
    - world-model snapshot projection
    - repository / service access
    """

    def __init__(
        self,
        master: Any,
        *,
        on_node_select: Callable[[str], None] | None = None,
        on_edge_select: Callable[[str], None] | None = None,
        on_node_move: Callable[[str, float, float], None] | None = None,
        on_background_click: Callable[[], None] | None = None,
        enable_zoom: bool = True,
        enable_pan: bool = True,
        enable_multi_select: bool = True,
        enable_node_drag: bool = False,
        enable_selection_box: bool = True,
        show_scrollbars: bool = True,
        empty_message: str = "No nodes",
        canvas_bg: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, corner_radius=0, **kwargs)
        self._on_node_select = on_node_select or (lambda _nid: None)
        self._on_edge_select = on_edge_select or (lambda _eid: None)
        self._on_node_move = on_node_move or (lambda _nid, _x, _y: None)
        self._on_background_click = on_background_click or (lambda: None)

        self._enable_zoom = enable_zoom
        self._enable_pan = enable_pan
        self._enable_multi_select = enable_multi_select
        self._enable_node_drag = enable_node_drag
        self._enable_selection_box = enable_selection_box
        self._empty_message = empty_message

        self._nodes: list[GraphNodeVisual] = []
        self._edges: list[GraphEdgeVisual] = []
        self._node_index: dict[str, GraphNodeVisual] = {}
        self.selection = GraphSelection()

        self._zoom_level = 1.0
        self._zoom_min = 0.25
        self._zoom_max = 3.0
        self._zoom_step = 0.1
        self._pan_mode = False
        self._pan_start: tuple[float, float] | None = None

        self._drag_node_id = ""
        self._drag_offset: tuple[float, float] = (0.0, 0.0)
        self._drag_origin: tuple[float, float] = (0.0, 0.0)

        self._selection_start: tuple[float, float] | None = None
        self._selection_box: int | None = None
        self._edge_hit_pads: dict[str, tuple[float, float, float, float]] = {}

        bg = canvas_bg if canvas_bg is not None else T.BG_DEEP
        self._tk_canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        if show_scrollbars:
            h_scroll = tk.Scrollbar(self, orient="horizontal", command=self._tk_canvas.xview)
            v_scroll = tk.Scrollbar(self, orient="vertical", command=self._tk_canvas.yview)
            self._tk_canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
            h_scroll.pack(side="bottom", fill="x")
            v_scroll.pack(side="right", fill="y")
            self._tk_canvas.pack(side="left", fill="both", expand=True)
        else:
            self._tk_canvas.pack(fill="both", expand=True)

        self._tk_canvas.bind("<Button-1>", self._on_canvas_press)
        self._tk_canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self._tk_canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        if enable_zoom:
            self._tk_canvas.bind("<MouseWheel>", self._on_mouse_wheel)
            self._tk_canvas.bind("<Button-4>", lambda e: self._zoom_delta(1))
            self._tk_canvas.bind("<Button-5>", lambda e: self._zoom_delta(-1))
        if enable_pan:
            self._tk_canvas.bind("<Button-2>", self._on_pan_start)
            self._tk_canvas.bind("<B2-Motion>", self._on_pan_drag)
            self._tk_canvas.bind("<ButtonRelease-2>", self._on_pan_end)
        if enable_selection_box:
            self._tk_canvas.bind("<Shift-Button-1>", self._on_selection_start)

        self._tk_canvas.bind("<Configure>", lambda _e: self._on_configure())

    @property
    def tk_canvas(self) -> tk.Canvas:
        return self._tk_canvas

    def set_scene(
        self,
        nodes: Sequence[GraphNodeVisual],
        edges: Sequence[GraphEdgeVisual],
        *,
        selected_node_ids: set[str] | None = None,
        selected_edge_ids: set[str] | None = None,
        redraw: bool = True,
    ) -> None:
        self._nodes = list(nodes)
        self._edges = list(edges)
        self._node_index = {n.node_id: n for n in self._nodes}
        if selected_node_ids is not None:
            self.selection.selected_node_ids = set(selected_node_ids)
        if selected_edge_ids is not None:
            self.selection.selected_edge_ids = set(selected_edge_ids)
        if redraw:
            self.redraw()

    def redraw(self) -> None:
        self._tk_canvas.delete("all")
        self._edge_hit_pads.clear()
        self._on_before_draw()

        if not self._nodes:
            w = max(int(self._tk_canvas.winfo_width() or 200), 100)
            h = max(int(self._tk_canvas.winfo_height() or 120), 60)
            self._tk_canvas.create_text(
                w // 2,
                h // 2,
                text=self._empty_message,
                fill=T.TEXT_MUTED,
                font=(T.FONT_FAMILY, 12),
            )
            self._on_after_draw()
            return

        for edge in self._edges:
            self._draw_edge(edge)
        for node in self._nodes:
            self._draw_node(node)

        self._apply_zoom_and_scroll()
        self._on_after_draw()

    def _apply_zoom_and_scroll(self) -> None:
        if self._zoom_level != 1.0:
            self._tk_canvas.scale("all", 0, 0, self._zoom_level, self._zoom_level)
        max_x = 0.0
        max_y = 0.0
        for node in self._nodes:
            _x0, _y0, x1, y1 = node.bounds
            max_x = max(max_x, x1 + 40)
            max_y = max(max_y, y1 + 40)
        self._tk_canvas.configure(
            scrollregion=(0, 0, max_x * self._zoom_level, max_y * self._zoom_level)
        )

    def _draw_node(self, node: GraphNodeVisual) -> None:
        selected = self.selection.is_node_selected(node.node_id)
        outline = T.ACCENT_DEFAULT if selected else node.outline
        width = max(2, node.outline_width) if selected else node.outline_width
        tags = ("node", node.node_id, *node.tags)

        if node.shape == "oval":
            r = max(node.width, node.height) / 2.0
            self._tk_canvas.create_oval(
                node.x - r,
                node.y - r,
                node.x + r,
                node.y + r,
                fill=node.fill,
                outline=outline,
                width=width,
                tags=tags,
            )
            self._tk_canvas.create_text(
                node.x,
                node.y - (6 if node.secondary_label else 0),
                text=node.label,
                fill=node.text_color,
                font=self._node_font(node),
                anchor="center",
                tags=tags,
            )
            if node.secondary_label:
                self._tk_canvas.create_text(
                    node.x,
                    node.y + 8,
                    text=node.secondary_label,
                    fill=node.secondary_color or T.TEXT_MUTED,
                    font=(T.FONT_FAMILY, max(7, node.font_size - 2)),
                    anchor="center",
                    tags=tags,
                )
        else:
            x0, y0 = node.x, node.y
            x1, y1 = node.x + node.width, node.y + node.height
            self._tk_canvas.create_rectangle(
                x0, y0, x1, y1,
                fill=node.fill,
                outline=outline,
                width=width,
                tags=tags,
            )
            if node.status_dot_color:
                cy = y0 + node.height / 2
                self._tk_canvas.create_oval(
                    x0 + 8, cy - 5, x0 + 18, cy + 5,
                    fill=node.status_dot_color,
                    outline="",
                    tags=tags,
                )
            self._tk_canvas.create_text(
                x0 + node.width / 2 + (5 if node.status_dot_color else 0),
                y0 + node.height / 2,
                text=node.label,
                fill=node.text_color,
                font=self._node_font(node),
                anchor="center",
                tags=tags,
            )
            if node.badge:
                self._tk_canvas.create_text(
                    x1 - 10,
                    y0 + 8,
                    text=node.badge,
                    fill=node.badge_color or T.ACCENT_DEFAULT,
                    font=(T.FONT_FAMILY, 10, "bold"),
                    tags=tags,
                )

        self._decorate_node(node, tags)

    def _node_font(self, node: GraphNodeVisual) -> tuple:
        if node.font_bold:
            return (T.FONT_FAMILY, node.font_size, "bold")
        return (T.FONT_FAMILY, node.font_size)

    def _draw_edge(self, edge: GraphEdgeVisual) -> None:
        src = self._node_index.get(edge.source_id)
        tgt = self._node_index.get(edge.target_id)
        if src is None or tgt is None:
            return

        if src.shape == "rect":
            sx, sy = src.anchor_right()
        else:
            sx, sy = src.center()
        if tgt.shape == "rect":
            tx, ty = tgt.anchor_left()
        else:
            tx, ty = tgt.center()

        # For oval-to-oval, connect center-to-center (radial/world graphs).
        if src.shape == "oval" and tgt.shape == "oval":
            sx, sy = src.center()
            tx, ty = tgt.center()

        selected = self.selection.is_edge_selected(edge.edge_id)
        color = T.ACCENT_DEFAULT if selected else edge.color
        line_width = edge.width + 1 if selected else edge.width
        tags = ("edge", edge.edge_id, *edge.tags)

        arrow = self._arrow_option(edge.arrow)
        self._tk_canvas.create_line(
            sx, sy, tx, ty,
            fill=color,
            width=line_width,
            arrow=arrow,
            arrowshape=(8, 10, 4) if arrow != tk.NONE else (),
            tags=tags,
        )
        mid_x = (sx + tx) / 2
        mid_y = (sy + ty) / 2
        self._edge_hit_pads[edge.edge_id] = (mid_x - 15, mid_y - 8, mid_x + 15, mid_y + 8)
        if edge.label:
            self._tk_canvas.create_text(
                mid_x,
                mid_y - 10,
                text=edge.label,
                fill=color,
                font=(T.FONT_FAMILY, 8),
                tags=tags,
            )

    @staticmethod
    def _arrow_option(arrow: str) -> str:
        if arrow == "forward":
            return tk.LAST
        if arrow == "backward":
            return tk.FIRST
        if arrow == "both":
            return tk.BOTH
        return tk.NONE

    # --- hooks for domain adapters ---

    def _decorate_node(self, node: GraphNodeVisual, tags: tuple[str, ...]) -> None:
        """Subclass hook (e.g. workflow edge handles)."""

    def _on_before_draw(self) -> None:
        """Subclass hook before scene draw."""

    def _on_after_draw(self) -> None:
        """Subclass hook after scene draw."""

    def _on_configure(self) -> None:
        """Default: no-op; view-only panels may redraw on resize."""

    def _intercept_press(self, canvas_x: float, canvas_y: float, event: tk.Event) -> bool:
        """Subclass hook — return True to consume the press."""
        return False

    def _intercept_release(self, canvas_x: float, canvas_y: float, event: tk.Event) -> bool:
        """Subclass hook — return True to consume the release."""
        return False

    # --- hit testing ---

    def hit_test_node(self, canvas_x: float, canvas_y: float) -> GraphNodeVisual | None:
        # Topmost last-drawn wins: reverse iterate
        for node in reversed(self._nodes):
            if node.contains(canvas_x, canvas_y):
                return node
        return None

    def hit_test_edge(self, canvas_x: float, canvas_y: float) -> GraphEdgeVisual | None:
        for edge in self._edges:
            pad = self._edge_hit_pads.get(edge.edge_id)
            if pad is None:
                continue
            x0, y0, x1, y1 = pad
            if x0 <= canvas_x <= x1 and y0 <= canvas_y <= y1:
                return edge
        return None

    def node_by_id(self, node_id: str) -> GraphNodeVisual | None:
        return self._node_index.get(node_id)

    # --- interaction ---

    def _event_xy(self, event: tk.Event) -> tuple[float, float]:
        return (self._tk_canvas.canvasx(event.x), self._tk_canvas.canvasy(event.y))

    def _on_canvas_press(self, event: tk.Event) -> None:
        canvas_x, canvas_y = self._event_xy(event)
        if self._intercept_press(canvas_x, canvas_y, event):
            return

        node = self.hit_test_node(canvas_x, canvas_y)
        if node is not None:
            additive = bool(self._enable_multi_select and (event.state & 0x4))
            self.selection.select_node(node.node_id, additive=additive)
            if self._enable_node_drag:
                self._drag_node_id = node.node_id
                if node.shape == "oval":
                    self._drag_offset = (canvas_x - node.x, canvas_y - node.y)
                else:
                    self._drag_offset = (canvas_x - node.x, canvas_y - node.y)
                self._drag_origin = (node.x, node.y)
            self.redraw()
            if len(self.selection.selected_node_ids) == 1:
                self._on_node_select(node.node_id)
            return

        edge = self.hit_test_edge(canvas_x, canvas_y)
        if edge is not None:
            additive = bool(self._enable_multi_select and (event.state & 0x4))
            self.selection.select_edge(edge.edge_id, additive=additive)
            self.redraw()
            self._on_edge_select(edge.edge_id)
            return

        if not (event.state & 0x1):
            self.selection.clear()
            self.redraw()
            self._on_background_click()

    def _on_selection_start(self, event: tk.Event) -> None:
        if not self._enable_selection_box:
            return
        canvas_x, canvas_y = self._event_xy(event)
        self._selection_start = (canvas_x, canvas_y)
        self._selection_box = self._tk_canvas.create_rectangle(
            canvas_x, canvas_y, canvas_x, canvas_y,
            outline=T.ACCENT_DEFAULT,
            dash=(4, 4),
            width=1,
        )

    def _on_canvas_drag(self, event: tk.Event) -> None:
        if self._selection_start is not None and self._selection_box is not None:
            canvas_x, canvas_y = self._event_xy(event)
            x0, y0 = self._selection_start
            self._tk_canvas.coords(self._selection_box, x0, y0, canvas_x, canvas_y)
            return
        if not self._enable_node_drag or not self._drag_node_id:
            return
        node = self._node_index.get(self._drag_node_id)
        if node is None:
            return
        canvas_x, canvas_y = self._event_xy(event)
        node.x = max(0.0, canvas_x - self._drag_offset[0])
        node.y = max(0.0, canvas_y - self._drag_offset[1])
        self.redraw()

    def _on_canvas_release(self, event: tk.Event) -> None:
        canvas_x, canvas_y = self._event_xy(event)
        if self._intercept_release(canvas_x, canvas_y, event):
            return

        if self._selection_start is not None and self._selection_box is not None:
            x0, y0 = self._selection_start
            chosen: set[str] = set()
            for node in self._nodes:
                nx, ny = node.center()
                if min(x0, canvas_x) <= nx <= max(x0, canvas_x) and min(y0, canvas_y) <= ny <= max(
                    y0, canvas_y
                ):
                    chosen.add(node.node_id)
            self.selection.select_nodes(chosen)
            self._tk_canvas.delete(self._selection_box)
            self._selection_box = None
            self._selection_start = None
            self.redraw()
            return

        if self._drag_node_id:
            node = self._node_index.get(self._drag_node_id)
            if node is not None:
                self._on_node_move(node.node_id, node.x, node.y)
            self._drag_node_id = ""

    def _on_pan_start(self, event: tk.Event) -> None:
        self._pan_mode = True
        self._pan_start = self._event_xy(event)
        self._tk_canvas.scan_mark(event.x, event.y)

    def _on_pan_drag(self, event: tk.Event) -> None:
        if not self._pan_mode:
            return
        self._tk_canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_pan_end(self, _event: tk.Event) -> None:
        self._pan_mode = False
        self._pan_start = None

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        if event.delta > 0:
            self._zoom_delta(1)
        elif event.delta < 0:
            self._zoom_delta(-1)

    def _zoom_delta(self, direction: int) -> None:
        if not self._enable_zoom or not self._nodes:
            return
        if direction > 0:
            self._zoom_level = min(self._zoom_max, self._zoom_level + self._zoom_step)
        else:
            self._zoom_level = max(self._zoom_min, self._zoom_level - self._zoom_step)
        self.redraw()

    def zoom_in(self) -> None:
        self._zoom_delta(1)

    def zoom_out(self) -> None:
        self._zoom_delta(-1)

    def zoom_reset(self) -> None:
        self._zoom_level = 1.0
        if self._nodes:
            self.redraw()

    def get_zoom_level(self) -> float:
        return self._zoom_level


__all__ = ["BaseGraphCanvas"]
