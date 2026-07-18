"""Execution List — filter/sort/search execution_library run history."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState, ExecutionRunItem
from ai_command_center.domain.execution_library_snapshot import ExecutionRunEntry
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import execution_state_color
from ai_command_center.ui.widget_utils import clear_children

_STATUS_RANK = {
    "active": 0,
    "running": 0,
    "awaiting_approval": 0,
    "in_progress": 0,
    "failed": 1,
    "error": 1,
    "waiting": 2,
    "queued": 2,
    "pending": 2,
    "blocked": 2,
    "complete": 3,
    "completed": 3,
    "success": 3,
    "idle": 4,
}


@dataclass(frozen=True, slots=True)
class _RunRow:
    run_id: str
    request_id: str
    goal: str
    status: str
    source: str
    created_at: float
    duration: str
    summary: str


def _format_duration(created_at: float) -> str:
    if not created_at:
        return "—"
    elapsed = max(0.0, time.time() - float(created_at))
    if elapsed < 60:
        return f"{int(elapsed)}s"
    if elapsed < 3600:
        return f"{int(elapsed // 60)}m"
    return f"{elapsed / 3600:.1f}h"


def _rows_from_snapshot(snap: AppState) -> list[_RunRow]:
    lib = snap.execution_library
    rows: list[_RunRow] = []
    if lib.run_history:
        active_goal = lib.active_plan.goal if lib.active_plan.is_active else ""
        for entry in lib.run_history:
            goal = active_goal if (
                entry.run_id == lib.active_plan.run_id
                or entry.request_id == lib.active_plan.request_id
            ) else (entry.summary or "—")
            rows.append(
                _RunRow(
                    run_id=entry.run_id or entry.request_id,
                    request_id=entry.request_id or entry.run_id,
                    goal=goal[:48] if goal else "—",
                    status=entry.status or "complete",
                    source=entry.source or "—",
                    created_at=float(entry.created_at or 0.0),
                    duration=_format_duration(float(entry.created_at or 0.0)),
                    summary=entry.summary or "",
                )
            )
        return rows

    for item in snap.execution_runs:
        if not isinstance(item, ExecutionRunItem):
            continue
        rows.append(
            _RunRow(
                run_id=item.run_id or item.request_id,
                request_id=item.request_id or item.run_id,
                goal=item.summary or "—",
                status="complete",
                source=item.source or "—",
                created_at=float(item.created_at or 0.0),
                duration=_format_duration(float(item.created_at or 0.0)),
                summary=item.summary or "",
            )
        )
    return rows


def sort_execution_rows(rows: list[_RunRow]) -> list[_RunRow]:
    """Failures-first operator sort: Active → Failed → Waiting → Complete."""
    return sorted(
        rows,
        key=lambda r: (
            _STATUS_RANK.get(str(r.status).lower(), 5),
            -float(r.created_at or 0.0),
        ),
    )


class ExecutionListPanel(ctk.CTkFrame):
    """Browse and select executions from execution_library."""

    def __init__(
        self,
        master: Any,
        *,
        on_select: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.EXECUTION_BLUE,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        self._on_select = on_select
        self._rows: list[_RunRow] = []
        self._selected_id = ""
        self._search = ""
        self._status_filter = "all"
        self._sort_mode = "operator"

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text="Execution List",
            font=T.FONT_HEADER,
            text_color=T.EXECUTION_BLUE,
            anchor="w",
        ).pack(side="left")

        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.pack(fill="x", padx=T.PAD, pady=(0, 6))
        self._search_entry = ctk.CTkEntry(
            filters,
            placeholder_text="Search run / goal…",
            font=T.FONT_SMALL,
            height=28,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
        )
        self._search_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._search_entry.bind("<KeyRelease>", lambda _e: self._on_filters_changed())

        self._status_menu = ctk.CTkOptionMenu(
            filters,
            values=["all", "active", "failed", "waiting", "complete"],
            width=110,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            button_color=T.EXECUTION_BLUE,
            command=lambda _v: self._on_filters_changed(),
        )
        self._status_menu.set("all")
        self._status_menu.pack(side="left", padx=(0, 6))

        self._sort_menu = ctk.CTkOptionMenu(
            filters,
            values=["operator", "newest", "status"],
            width=100,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            button_color=T.EXECUTION_BLUE,
            command=lambda _v: self._on_filters_changed(),
        )
        self._sort_menu.set("operator")
        self._sort_menu.pack(side="left")

        self._list = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, border_width=0, corner_radius=T.SMALL_RADIUS
        )
        self._list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_snapshot(self, snap: AppState, *, selected_request_id: str = "") -> None:
        self._rows = _rows_from_snapshot(snap)
        self._selected_id = selected_request_id
        self._render()

    def clear_status_filter(self) -> None:
        self._status_menu.set("all")
        self._status_filter = "all"
        self._render()

    def _on_filters_changed(self) -> None:
        self._search = str(self._search_entry.get() or "").lower()
        self._status_filter = str(self._status_menu.get() or "all")
        self._sort_mode = str(self._sort_menu.get() or "operator")
        self._render()

    def _filtered(self) -> list[_RunRow]:
        rows = list(self._rows)
        filt = self._status_filter
        if filt == "active":
            rows = [r for r in rows if _STATUS_RANK.get(r.status.lower(), 5) == 0]
        elif filt == "failed":
            rows = [r for r in rows if _STATUS_RANK.get(r.status.lower(), 5) == 1]
        elif filt == "waiting":
            rows = [r for r in rows if _STATUS_RANK.get(r.status.lower(), 5) == 2]
        elif filt == "complete":
            rows = [r for r in rows if _STATUS_RANK.get(r.status.lower(), 5) == 3]
        if self._search:
            rows = [
                r for r in rows
                if self._search in r.run_id.lower()
                or self._search in r.request_id.lower()
                or self._search in r.goal.lower()
                or self._search in r.source.lower()
            ]
        if self._sort_mode == "newest":
            rows.sort(key=lambda r: -float(r.created_at or 0.0))
        elif self._sort_mode == "status":
            rows.sort(key=lambda r: (r.status.lower(), -float(r.created_at or 0.0)))
        else:
            rows = sort_execution_rows(rows)
        return rows

    def _render(self) -> None:
        clear_children(self._list)
        rows = self._filtered()
        if not rows:
            ctk.CTkLabel(
                self._list,
                text="No executions match filters.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).pack(pady=24)
            return
        for row in rows:
            self._render_row(row)

    def _render_row(self, row: _RunRow) -> None:
        selected = row.request_id == self._selected_id or row.run_id == self._selected_id
        fg, _bg = execution_state_color(row.status)
        frame = ctk.CTkFrame(
            self._list,
            fg_color=T.BG_INPUT if selected else T.BG_GLASS,
            border_color=T.EXECUTION_BLUE if selected else T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
        )
        frame.pack(fill="x", pady=2)
        rid = row.request_id or row.run_id
        frame.bind("<Button-1>", lambda _e, i=rid: self._click(i))

        created = (
            time.strftime("%H:%M:%S", time.localtime(row.created_at))
            if row.created_at
            else "—"
        )
        cells = (
            (row.run_id[:16] or "—", T.TEXT_PRIMARY),
            (row.goal[:28], T.TEXT_SECONDARY),
            (row.status, fg),
            (row.source, T.EXECUTION_BLUE),
            (created, T.TEXT_MUTED),
            (row.duration, T.TEXT_MUTED),
        )
        for text, color in cells:
            lbl = ctk.CTkLabel(
                frame, text=text, font=T.FONT_SMALL, text_color=color, anchor="w"
            )
            lbl.pack(side="left", padx=6, pady=6)
            lbl.bind("<Button-1>", lambda _e, i=rid: self._click(i))

    def _click(self, request_id: str) -> None:
        if self._on_select:
            self._on_select(request_id)


# Re-export for tests
__all__ = ["ExecutionListPanel", "sort_execution_rows", "ExecutionRunEntry"]
