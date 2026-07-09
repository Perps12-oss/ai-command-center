"""ExecutionTimelineScrubber — event index pointer for execution replay.

Architecture contract: pure display widget, no bus/service imports.
Actions publish via on_scrub callback (UI → UIController → bus).
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class ExecutionTimelineScrubber(ctk.CTkFrame):
    """Slider + step controls for scrubbing through execution events.

    ┌──────────────────────────────────────────────────────────┐
    │  ◀   Event 3 / 12 — chat.complete          ▶            │
    │  [━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━]            │
    └──────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        master: Any,
        *,
        on_scrub: Callable[[int], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_scrub = on_scrub or (lambda _index: None)
        self._count = 0
        self._index = 0
        self._labels: list[str] = []
        self._build()

    def _build(self) -> None:
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x")

        btn_cfg: dict[str, Any] = dict(
            width=28,
            height=24,
            font=(T.FONT_FAMILY, 11),
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=T.SMALL_RADIUS,
        )
        self._prev_btn = ctk.CTkButton(
            controls,
            text="◀",
            command=self._step_prev,
            **btn_cfg,
        )
        self._prev_btn.pack(side="left")

        self._label = ctk.CTkLabel(
            controls,
            text="No events",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        self._label.pack(side="left", fill="x", expand=True, padx=8)

        self._next_btn = ctk.CTkButton(
            controls,
            text="▶",
            command=self._step_next,
            **btn_cfg,
        )
        self._next_btn.pack(side="right")

        self._slider = ctk.CTkSlider(
            self,
            from_=0,
            to=1,
            number_of_steps=1,
            command=self._on_slider,
            fg_color=T.BG_GLASS,
            progress_color=T.ACCENT_DEFAULT,
            button_color=T.ACCENT_DEFAULT,
            button_hover_color=T.ACCENT_HOVER,
        )
        self._slider.pack(fill="x", pady=(6, 0))
        self._slider.set(0)
        self._update_controls()

    def set_timeline(
        self,
        labels: list[str],
        *,
        active_index: int = 0,
    ) -> None:
        """Configure scrubber range and labels from execution event types."""
        self._labels = list(labels)
        self._count = len(labels)
        if self._count <= 1:
            self._slider.configure(to=max(1, self._count), number_of_steps=max(0, self._count - 1))
        else:
            self._slider.configure(to=self._count - 1, number_of_steps=self._count - 1)
        self._index = max(0, min(active_index, max(0, self._count - 1)))
        if self._count:
            self._slider.set(self._index)
        self._refresh_label()
        self._update_controls()

    def _refresh_label(self) -> None:
        if not self._count:
            self._label.configure(text="No events")
            return
        label = self._labels[self._index] if self._index < len(self._labels) else ""
        self._label.configure(
            text=f"Event {self._index + 1} / {self._count} — {label}"
        )

    def _update_controls(self) -> None:
        enabled = self._count > 0
        state = "normal" if enabled else "disabled"
        self._prev_btn.configure(state=state)
        self._next_btn.configure(state=state)
        if not enabled:
            self._slider.configure(state="disabled")
        else:
            self._slider.configure(state="normal")

    def _emit_scrub(self, index: int) -> None:
        if not self._count:
            return
        self._index = max(0, min(index, self._count - 1))
        self._slider.set(self._index)
        self._refresh_label()
        self._on_scrub(self._index)

    def _step_prev(self) -> None:
        self._emit_scrub(self._index - 1)

    def _step_next(self) -> None:
        self._emit_scrub(self._index + 1)

    def _on_slider(self, value: float) -> None:
        self._emit_scrub(int(round(value)))
