"""Scheduled automation rows (n8n-style)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.automation_workspace import AutomationScheduleItem
from ai_command_center.ui.design_system import theme_v2 as T


class ScheduleManager(ctk.CTkFrame):
    """Cron schedule list for automations."""

    def __init__(
        self,
        master: Any,
        *,
        on_toggle: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, **kwargs)
        self._on_toggle = on_toggle or (lambda _schedule_id: None)
        ctk.CTkLabel(
            self,
            text="SCHEDULES",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))

    def update(self, schedules: Sequence[AutomationScheduleItem]) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()
        for schedule in schedules:
            row = ctk.CTkFrame(self._scroll, fg_color=T.BG_GLASS, corner_radius=T.SMALL_RADIUS)
            row.pack(fill="x", pady=3)
            top = ctk.CTkFrame(row, fg_color="transparent")
            top.pack(fill="x", padx=10, pady=(6, 2))
            ctk.CTkLabel(
                top,
                text=schedule.title,
                font=(T.FONT_FAMILY, 10, "bold"),
                text_color=T.TEXT_PRIMARY,
                anchor="w",
            ).pack(side="left", fill="x", expand=True)
            status = "On" if schedule.enabled else "Off"
            color = T.STATUS_READY if schedule.enabled else T.TEXT_MUTED
            ctk.CTkButton(
                top,
                text=status,
                width=44,
                height=22,
                font=(T.FONT_FAMILY, 9),
                fg_color=T.BG_GLASS_BORDER if schedule.enabled else "transparent",
                hover_color=T.BG_GLASS,
                text_color=color,
                command=lambda sid=schedule.schedule_id: self._on_toggle(sid),
            ).pack(side="right")
            ctk.CTkLabel(
                row,
                text=f"{schedule.cron} · {schedule.next_run_label}",
                font=(T.FONT_FAMILY, 9),
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=10, pady=(0, 8))


__all__ = ["ScheduleManager"]
