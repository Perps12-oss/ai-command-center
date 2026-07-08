"""ExecutionsView — master list of execution runs.

Shows all execution_runs from AppState in a scrollable list.
Clicking a row opens ExecutionDetailView.

Architecture contract
─────────────────────
• Pure display view — no EventBus, service, or repository imports.
• Data supplied via apply_state() called from UIQueue.
• on_select callback triggers ExecutionDetailView navigation.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

_STATUS_COLORS: dict[str, str] = {
    "chat":          T.ACCENT_DEFAULT,
    "orchestration": T.STATUS_READY,
    "agent":         "#A78BFA",
    "workflow":      T.STATUS_BUSY,
}


class _ExecutionRow(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        run_id: str,
        source: str,
        summary: str,
        created_at: float,
        on_select: Callable[[str], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            corner_radius=T.SMALL_RADIUS,
            height=52,
        )
        self.pack_propagate(False)
        self._run_id = run_id

        import time
        color = _STATUS_COLORS.get(source, T.TEXT_MUTED)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="both", expand=True, padx=8, pady=6)

        ctk.CTkLabel(
            row,
            text=f"● {source}",
            font=(T.FONT_FAMILY, 9),
            text_color=color,
            width=80,
        ).pack(side="left")

        ctk.CTkLabel(
            row,
            text=summary[:60] if summary else run_id[:24],
            font=(T.FONT_FAMILY, 11),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", fill="x", expand=True, padx=(6, 0))

        if created_at:
            ts = time.strftime("%H:%M", time.localtime(created_at))
            ctk.CTkLabel(
                row,
                text=ts,
                font=(T.FONT_FAMILY, 9),
                text_color=T.TEXT_MUTED,
            ).pack(side="right", padx=4)

        ctk.CTkButton(
            row,
            text="▶",
            width=22, height=22,
            font=(T.FONT_FAMILY, 10),
            fg_color="transparent",
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=4,
            command=lambda: on_select(self._run_id),
        ).pack(side="right")

        self.bind("<Button-1>", lambda _: on_select(self._run_id))


class ExecutionsView(ctk.CTkFrame):
    """Master list view for all execution runs.

    Populated by apply_state() from the UIQueue/StateApplierMixin.
    """

    def __init__(
        self,
        master: Any,
        on_select: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_select = on_select or (lambda r: None)
        self._build()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0, height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="Executions",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", padx=T.PAD, pady=12)

        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        self._scroll.pack(fill="both", expand=True, padx=8, pady=8)

        self._empty_lbl = ctk.CTkLabel(
            self._scroll,
            text="No executions yet.",
            font=T.FONT_BODY,
            text_color=T.TEXT_MUTED,
        )
        self._empty_lbl.pack(pady=40)

    def apply_state(self, execution_runs: list[Any]) -> None:
        """Refresh the list from AppState.execution_runs."""
        for child in self._scroll.winfo_children():
            child.destroy()

        if not execution_runs:
            ctk.CTkLabel(
                self._scroll,
                text="No executions yet.",
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
            ).pack(pady=40)
            return

        for run in reversed(list(execution_runs)):
            _ExecutionRow(
                self._scroll,
                run_id=str(getattr(run, "run_id", "")),
                source=str(getattr(run, "source", "chat")),
                summary=str(getattr(run, "summary", "")),
                created_at=float(getattr(run, "created_at", 0.0)),
                on_select=self._on_select,
            ).pack(fill="x", pady=3)
