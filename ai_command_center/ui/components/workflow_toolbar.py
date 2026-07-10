"""Workflow toolbar for the graph workspace.

P4.3: Workflow execution controls (pause, resume, cancel)
P4.6: Keyboard shortcuts button
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class WorkflowToolbar(ctk.CTkFrame):
    """Top toolbar with workflow name and execution/run controls."""

    def __init__(
        self,
        master: Any,
        *,
        on_run: Callable[[], None] | None = None,
        on_pause: Callable[[], None] | None = None,
        on_resume: Callable[[], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
        on_compare: Callable[[], None] | None = None,
        on_export: Callable[[], None] | None = None,
        on_import: Callable[[], None] | None = None,
        on_undo: Callable[[], None] | None = None,
        on_redo: Callable[[], None] | None = None,
        on_shortcuts: Callable[[], None] | None = None,
        on_zoom_in: Callable[[], None] | None = None,
        on_zoom_out: Callable[[], None] | None = None,
        on_zoom_reset: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, height=46, **kwargs)
        self.pack_propagate(False)

        # Callbacks
        self._on_run = on_run or (lambda: None)
        self._on_pause = on_pause or (lambda: None)
        self._on_resume = on_resume or (lambda: None)
        self._on_cancel = on_cancel or (lambda: None)
        self._on_compare = on_compare or (lambda: None)
        self._on_export = on_export or (lambda: None)
        self._on_import = on_import or (lambda: None)
        self._on_undo = on_undo or (lambda: None)
        self._on_redo = on_redo or (lambda: None)
        self._on_shortcuts = on_shortcuts or (lambda: None)
        self._on_zoom_in = on_zoom_in or (lambda: None)
        self._on_zoom_out = on_zoom_out or (lambda: None)
        self._on_zoom_reset = on_zoom_reset or (lambda: None)

        # Left side - zoom controls
        self._zoom_label = ctk.CTkLabel(
            self,
            text="100%",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
            width=44,
        )
        self._zoom_label.pack(side="left", padx=(T.PAD, 4), pady=10)

        small_btn_cfg: dict[str, Any] = dict(
            width=28,
            height=28,
            font=(T.FONT_FAMILY, 12),
            corner_radius=T.SMALL_RADIUS,
        )

        ctk.CTkButton(
            self,
            text="−",
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
            command=self._on_zoom_out,
            **small_btn_cfg,
        ).pack(side="left", padx=(0, 2), pady=9)

        ctk.CTkButton(
            self,
            text="↺",
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
            command=self._on_zoom_reset,
            **small_btn_cfg,
        ).pack(side="left", padx=(0, 2), pady=9)

        ctk.CTkButton(
            self,
            text="+",
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
            command=self._on_zoom_in,
            **small_btn_cfg,
        ).pack(side="left", padx=(0, 8), pady=9)

        # Separator
        sep1 = ctk.CTkFrame(self, width=1, fg_color=T.BG_GLASS_BORDER)
        sep1.pack(side="left", fill="y", padx=8, pady=8)

        # Title and status
        self._title = ctk.CTkLabel(
            self,
            text="Workflow",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._title.pack(side="left", pady=10)

        self._status = ctk.CTkLabel(
            self,
            text="",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
        )
        self._status.pack(side="left", padx=(4, 0))

        # Execution controls (center)
        exec_frame = ctk.CTkFrame(self, fg_color="transparent")
        exec_frame.pack(side="left", padx=12)

        btn_cfg: dict[str, Any] = dict(
            height=28,
            font=(T.FONT_FAMILY, 10),
            corner_radius=T.SMALL_RADIUS,
        )

        # Undo/Redo
        self._undo_btn = ctk.CTkButton(
            exec_frame,
            text="↶",
            width=32,
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            command=self._on_undo,
            **btn_cfg,
        )
        self._undo_btn.pack(side="left", padx=(0, 2))

        self._redo_btn = ctk.CTkButton(
            exec_frame,
            text="↷",
            width=32,
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            command=self._on_redo,
            **btn_cfg,
        )
        self._redo_btn.pack(side="left", padx=(0, 8))

        # Cancel button
        self._cancel_btn = ctk.CTkButton(
            exec_frame,
            text="■",
            width=32,
            fg_color=T.BG_GLASS,
            hover_color=T.STATUS_ERROR_BG,
            text_color=T.STATUS_ERROR,
            command=self._on_cancel,
            **btn_cfg,
        )
        self._cancel_btn.pack(side="left", padx=(0, 2))

        # Pause button
        self._pause_btn = ctk.CTkButton(
            exec_frame,
            text="⏸",
            width=32,
            fg_color=T.BG_GLASS,
            hover_color=T.STATUS_BUSY_BG,
            text_color=T.STATUS_BUSY,
            command=self._on_pause,
            **btn_cfg,
        )
        self._pause_btn.pack(side="left", padx=(0, 2))

        # Run/Resume button
        self._run_btn = ctk.CTkButton(
            exec_frame,
            text="▶",
            width=48,
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_PRIMARY,
            command=self._on_run,
            **btn_cfg,
        )
        self._run_btn.pack(side="left", padx=(0, 8))

        # Right side buttons
        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.pack(side="right", padx=(0, T.PAD))

        # Shortcuts button
        ctk.CTkButton(
            right_frame,
            text="⌨",
            width=32,
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            command=self._on_shortcuts,
            **btn_cfg,
        ).pack(side="right", padx=(4, 0))

        # Import button
        ctk.CTkButton(
            right_frame,
            text="Import",
            width=64,
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            command=self._on_import,
            **btn_cfg,
        ).pack(side="right", padx=(4, 0))

        # Export button
        ctk.CTkButton(
            right_frame,
            text="Export",
            width=64,
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            command=self._on_export,
            **btn_cfg,
        ).pack(side="right", padx=(4, 0))

        # Compare button
        ctk.CTkButton(
            right_frame,
            text="Compare",
            width=72,
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            command=self._on_compare,
            **btn_cfg,
        ).pack(side="right", padx=(4, 0))

    def set_workflow_name(self, name: str) -> None:
        self._title.configure(text=name or "Workflow")

    def set_running(self, running: bool) -> None:
        """Update toolbar state for running workflow."""
        if running:
            self._status.configure(text="Running")
            self._run_btn.configure(text="⏸", command=self._on_pause, state="normal")
            self._cancel_btn.configure(state="normal")
        else:
            self._status.configure(text="")
            self._run_btn.configure(text="▶", command=self._on_run, state="normal")
            self._cancel_btn.configure(state="disabled")

    def set_paused(self, paused: bool) -> None:
        """Update toolbar state for paused workflow."""
        if paused:
            self._status.configure(text="Paused")
            self._run_btn.configure(text="▶", command=self._on_resume, state="normal")
        else:
            self._status.configure(text="Running")
            self._run_btn.configure(text="⏸", command=self._on_pause, state="normal")

    def set_zoom_level(self, level: float) -> None:
        """Update zoom level display."""
        self._zoom_label.configure(text=f"{int(level * 100)}%")

    def set_undo_enabled(self, enabled: bool) -> None:
        """Enable/disable undo button."""
        self._undo_btn.configure(state="normal" if enabled else "disabled")

    def set_redo_enabled(self, enabled: bool) -> None:
        """Enable/disable redo button."""
        self._redo_btn.configure(state="normal" if enabled else "disabled")


__all__ = ["WorkflowToolbar"]
