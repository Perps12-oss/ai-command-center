"""Mutation Journal — last 200 world-model mutations with expand/collapse."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.world_model_snapshot import MutationSnapshot, WorldModelSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children

_MAX_JOURNAL = 200


class MutationJournalPanel(ctk.CTkFrame):
    """Operational visibility into recent world-model mutations."""

    def __init__(self, master: Any) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.WORLD_TEAL,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        self._expanded: set[str] = set()
        self._entries: tuple[MutationSnapshot, ...] = ()

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text="Mutation Journal",
            font=T.FONT_HEADER,
            text_color=T.WORLD_TEAL,
            anchor="w",
        ).pack(side="left")
        self._count_label = ctk.CTkLabel(
            header,
            text="0",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="e",
        )
        self._count_label.pack(side="right")

        self._list = ctk.CTkScrollableFrame(
            self,
            fg_color=T.BG_DEEP,
            border_width=0,
            corner_radius=T.SMALL_RADIUS,
        )
        self._list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_snapshot(self, wm: WorldModelSnapshot) -> None:
        entries = wm.mutation_log[-_MAX_JOURNAL:]
        self._entries = tuple(reversed(entries))
        self._count_label.configure(text=str(len(self._entries)))
        self._render()

    def _render(self) -> None:
        clear_children(self._list)
        if not self._entries:
            ctk.CTkLabel(
                self._list,
                text="No mutations recorded.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).pack(pady=24)
            return

        for entry in self._entries:
            mid = entry.mutation_id or f"{entry.timestamp}:{entry.summary}"
            expanded = mid in self._expanded
            row = ctk.CTkFrame(
                self._list,
                fg_color=T.BG_GLASS,
                border_color=T.BG_GLASS_BORDER,
                border_width=1,
                corner_radius=T.SMALL_RADIUS,
            )
            row.pack(fill="x", pady=2)

            top = ctk.CTkFrame(row, fg_color="transparent")
            top.pack(fill="x", padx=8, pady=(4, 2 if expanded else 4))

            toggle = ctk.CTkButton(
                top,
                text="▾" if expanded else "▸",
                width=24,
                height=22,
                fg_color="transparent",
                hover_color=T.BG_GLASS_BORDER,
                text_color=T.WORLD_TEAL,
                font=T.FONT_SMALL,
                command=lambda m=mid: self._toggle(m),
            )
            toggle.pack(side="left")

            ctk.CTkLabel(
                top,
                text=entry.timestamp or "—",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                width=140,
                anchor="w",
            ).pack(side="left", padx=(4, 8))
            ctk.CTkLabel(
                top,
                text=entry.mutation_type or "mutation",
                font=T.FONT_SMALL,
                text_color=T.WORLD_TEAL,
                width=100,
                anchor="w",
            ).pack(side="left")
            entity = entry.goal_id or entry.correlation_id or "—"
            ctk.CTkLabel(
                top,
                text=entity,
                font=T.FONT_SMALL,
                text_color=T.TEXT_SECONDARY,
                width=100,
                anchor="w",
            ).pack(side="left", padx=(8, 0))
            ctk.CTkLabel(
                top,
                text=(entry.summary or "")[:80],
                font=T.FONT_SMALL,
                text_color=T.TEXT_PRIMARY,
                anchor="w",
            ).pack(side="left", fill="x", expand=True, padx=(8, 0))

            if expanded:
                detail = ctk.CTkFrame(row, fg_color=T.BG_INPUT, corner_radius=T.SMALL_RADIUS)
                detail.pack(fill="x", padx=8, pady=(0, 6))
                lines = (
                    f"mutation_id: {entry.mutation_id or '—'}",
                    f"operation: {entry.mutation_type or '—'}",
                    f"entity/goal: {entity}",
                    f"correlation: {entry.correlation_id or '—'}",
                    f"summary: {entry.summary or '—'}",
                )
                for line in lines:
                    ctk.CTkLabel(
                        detail,
                        text=line,
                        font=T.FONT_MONO,
                        text_color=T.TEXT_SECONDARY,
                        anchor="w",
                    ).pack(fill="x", padx=8, pady=1)

    def _toggle(self, mutation_id: str) -> None:
        if mutation_id in self._expanded:
            self._expanded.discard(mutation_id)
        else:
            self._expanded.add(mutation_id)
        self._render()
