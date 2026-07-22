"""Mission Control pipeline stage strip (PR-UI-E11)."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

# Canonical Mission Control stages (acceptance: pipeline stages visible).
MISSION_STAGES: tuple[str, ...] = (
    "Planner",
    "Router",
    "Executor",
    "Verifier",
    "Receipt",
)


def resolve_active_stage_index(
    *,
    pipeline_stage: str = "",
    truth_valid: bool = False,
    has_receipt: bool = False,
) -> int:
    """Map AppState signals onto the Mission Control stage strip."""
    stage = str(pipeline_stage or "").strip().lower()
    if has_receipt and (truth_valid or stage in {"complete", "done", "receipt"}):
        return 4
    if truth_valid or stage in {"verify", "verifier", "validation", "truth"}:
        return 3
    if stage in {"execute", "executor", "running", "tool", "tools"}:
        return 2
    if stage in {"route", "router", "routing"}:
        return 1
    if stage in {"plan", "planner", "planning", "research"}:
        return 0
    if stage in {"complete", "done"}:
        return 4
    if stage:
        return 2
    return 0


class PipelineStageStrip(ctk.CTkFrame):
    """Horizontal Planner→…→Receipt stage indicators."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.EXECUTION_BLUE,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
            **kwargs,
        )
        ctk.CTkLabel(
            self,
            text="Pipeline Stages",
            font=T.FONT_HEADER,
            text_color=T.EXECUTION_BLUE,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(10, 4))
        self._row = ctk.CTkFrame(self, fg_color="transparent")
        self._row.pack(fill="x", padx=8, pady=(0, 10))
        self._labels: list[ctk.CTkLabel] = []
        for index, name in enumerate(MISSION_STAGES):
            lbl = ctk.CTkLabel(
                self._row,
                text=name,
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                fg_color=T.BG_GLASS,
                corner_radius=T.SMALL_RADIUS,
                padx=10,
                pady=6,
            )
            lbl.pack(side="left", padx=(0 if index == 0 else 6, 0))
            self._labels.append(lbl)
        self._hint = ctk.CTkLabel(
            self,
            text="stage: —",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._hint.pack(fill="x", padx=T.PAD, pady=(0, 8))

    def apply_active_index(self, active_index: int, *, detail: str = "") -> None:
        active = max(0, min(int(active_index), len(self._labels) - 1))
        for index, label in enumerate(self._labels):
            if index < active:
                label.configure(
                    text_color=T.STATUS_READY,
                    fg_color=T.BG_GLASS,
                )
            elif index == active:
                label.configure(
                    text_color=T.TEXT_PRIMARY,
                    fg_color=T.HERO_CYAN_DIM,
                )
            else:
                label.configure(
                    text_color=T.TEXT_MUTED,
                    fg_color=T.BG_GLASS,
                )
        stage_name = MISSION_STAGES[active]
        self._hint.configure(
            text=f"stage: {stage_name}" + (f" · {detail}" if detail else "")
        )


__all__ = ["MISSION_STAGES", "PipelineStageStrip", "resolve_active_stage_index"]
