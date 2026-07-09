"""ExecutionsView — master list of execution runs.

Shows all execution_runs from AppState in a scrollable list.
Clicking a row opens ExecutionDetailView.

Architecture contract
─────────────────────
• Pure display view — no EventBus, service, or repository imports.
• Data supplied via apply_state() called from UIQueue.
• on_select callback triggers execution query + detail navigation.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.execution_detail_view import ExecutionDetailView

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
        request_id: str,
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
        self._request_id = request_id

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
            text=summary[:60] if summary else request_id[:24],
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
            command=lambda: on_select(self._request_id),
        ).pack(side="right")

        self.bind("<Button-1>", lambda _: on_select(self._request_id))


class ExecutionsView(ctk.CTkFrame):
    """Master list view for all execution runs with optional detail drill-down."""

    def __init__(
        self,
        master: Any,
        on_select: Callable[[str], None] | None = None,
        on_scrub: Callable[[str, int], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_select = on_select or (lambda _request_id: None)
        self._on_scrub = on_scrub or (lambda _request_id, _index: None)
        self._selected_request_id = ""
        self._build()

    def _build(self) -> None:
        self._list_host = ctk.CTkFrame(self, fg_color="transparent")
        self._list_host.pack(fill="both", expand=True)

        header = ctk.CTkFrame(self._list_host, fg_color=T.BG_PANEL, corner_radius=0, height=50)
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
            self._list_host,
            fg_color="transparent",
            corner_radius=0,
        )
        self._scroll.pack(fill="both", expand=True, padx=8, pady=8)

        self._detail = ExecutionDetailView(
            self,
            on_back=self._show_list,
            on_scrub=self._handle_scrub,
        )

    def _show_list(self) -> None:
        self._selected_request_id = ""
        self._detail.pack_forget()
        self._list_host.pack(fill="both", expand=True)

    def _show_detail(self) -> None:
        self._list_host.pack_forget()
        self._detail.pack(fill="both", expand=True)

    def _handle_scrub(self, index: int) -> None:
        if self._selected_request_id:
            self._on_scrub(self._selected_request_id, index)

    def open_request(self, request_id: str) -> None:
        self._selected_request_id = request_id
        self._on_select(request_id)
        self._show_detail()

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
            request_id = str(getattr(run, "request_id", ""))
            if not request_id:
                continue
            _ExecutionRow(
                self._scroll,
                request_id=request_id,
                source=str(getattr(run, "source", "chat")),
                summary=str(getattr(run, "summary", "")),
                created_at=float(getattr(run, "created_at", 0.0)),
                on_select=self.open_request,
            ).pack(fill="x", pady=3)

    def apply_timeline(
        self,
        *,
        request_id: str,
        timeline_steps: Sequence[dict[str, Any]],
        scrub_labels: Sequence[str],
        scrub_index: int,
        timeline_source: str,
        spans: Sequence[dict[str, Any]] | None = None,
    ) -> None:
        """Update the detail panel from AppState.execution_timeline."""
        if request_id != self._selected_request_id:
            return
        run = type(
            "ExecutionRunView",
            (),
            {
                "run_id": request_id,
                "request_id": request_id,
                "source": timeline_source,
                "status": "complete",
                "provider_id": "",
                "model": "",
            },
        )()
        self._detail.show_execution(
            run,
            list(spans or []),
            timeline_steps=timeline_steps,
            scrub_labels=scrub_labels,
            scrub_index=scrub_index,
            timeline_source=timeline_source,
        )
