"""Workflow toolbar for the graph workspace."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class WorkflowToolbar(ctk.CTkFrame):
    """Top toolbar with workflow name and run/compare actions."""

    def __init__(
        self,
        master: Any,
        *,
        on_run: Callable[[], None] | None = None,
        on_compare: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, height=46, **kwargs)
        self.pack_propagate(False)
        self._on_run = on_run or (lambda: None)
        self._on_compare = on_compare or (lambda: None)

        self._title = ctk.CTkLabel(
            self,
            text="Workflow",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._title.pack(side="left", padx=T.PAD, pady=10)

        self._status = ctk.CTkLabel(
            self,
            text="",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
        )
        self._status.pack(side="left", padx=(4, 0))

        btn_cfg: dict[str, Any] = dict(
            height=28,
            font=(T.FONT_FAMILY, 10),
            corner_radius=T.SMALL_RADIUS,
        )
        ctk.CTkButton(
            self,
            text="Compare",
            width=72,
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            command=self._on_compare,
            **btn_cfg,
        ).pack(side="right", padx=(4, T.PAD), pady=9)

        self._run_btn = ctk.CTkButton(
            self,
            text="Run",
            width=64,
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_PRIMARY,
            command=self._on_run,
            **btn_cfg,
        )
        self._run_btn.pack(side="right", pady=9)

    def set_workflow_name(self, name: str) -> None:
        self._title.configure(text=name or "Workflow")

    def set_running(self, running: bool) -> None:
        self._status.configure(text="Running" if running else "")
        self._run_btn.configure(state="disabled" if running else "normal")


__all__ = ["WorkflowToolbar"]
