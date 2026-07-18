"""Selection Inspector — read-only detail for the selected world-model node."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.world_model_snapshot import WorldModelSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children


class SelectionInspectorPanel(ctk.CTkFrame):
    """Detailed view of the selected entity (Article 12 Selection Inspector)."""

    def __init__(self, master: Any) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.WORLD_TEAL,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text="Selection Inspector",
            font=T.FONT_HEADER,
            text_color=T.WORLD_TEAL,
            anchor="w",
        ).pack(side="left")

        self._body = ctk.CTkScrollableFrame(
            self,
            fg_color=T.BG_DEEP,
            border_width=0,
            corner_radius=T.SMALL_RADIUS,
        )
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._empty()

    def apply_snapshot(self, wm: WorldModelSnapshot) -> None:
        clear_children(self._body)
        node = wm.selected_node
        if node is None:
            self._empty()
            return

        rel_count = len(wm.edges_for_selected)
        goal_links = [
            g.title or g.goal_id
            for g in wm.goals
            if g.goal_id and (
                g.goal_id in {v for _, v in node.attributes}
                or any(k.lower() == "goal_id" and v == g.goal_id for k, v in node.attributes)
            )
        ]
        if not goal_links and node.node_type == "goal":
            goal_links = [node.label or node.node_id]

        rows = (
            ("Entity ID", node.node_id),
            ("Name", node.label or "—"),
            ("Type", node.node_type or "—"),
            ("Relationship Count", str(rel_count)),
            ("Goal Links", ", ".join(goal_links) if goal_links else "—"),
        )
        for label, value in rows:
            self._row(label, value)

        if node.attributes:
            ctk.CTkLabel(
                self._body,
                text="Attributes",
                font=T.FONT_HEADER,
                text_color=T.TEXT_SECONDARY,
                anchor="w",
            ).pack(fill="x", padx=4, pady=(10, 2))
            for key, value in node.attributes:
                self._row(key, value)
        else:
            self._row("Attributes", "—")

        meta_keys = ("created_at", "updated_at", "workspace_id", "source", "metadata")
        meta_pairs = [(k, v) for k, v in node.attributes if k.lower() in meta_keys]
        ctk.CTkLabel(
            self._body,
            text="Metadata",
            font=T.FONT_HEADER,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        ).pack(fill="x", padx=4, pady=(10, 2))
        if meta_pairs:
            for key, value in meta_pairs:
                self._row(key, value)
        else:
            self._row("Metadata", "—")

    def _empty(self) -> None:
        clear_children(self._body)
        ctk.CTkLabel(
            self._body,
            text=(
                "Nothing selected to inspect.\n"
                "Inspector details appear when you select an entity in the graph or list.\n"
                "Next: click an entity in Knowledge Graph or Entity Explorer."
            ),
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            justify="left",
        ).pack(pady=24)

    def _row(self, label: str, value: str) -> None:
        frame = ctk.CTkFrame(self._body, fg_color="transparent")
        frame.pack(fill="x", padx=4, pady=2)
        ctk.CTkLabel(
            frame,
            text=label,
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            width=120,
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            frame,
            text=value,
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
            wraplength=180,
        ).pack(side="left", fill="x", expand=True)
