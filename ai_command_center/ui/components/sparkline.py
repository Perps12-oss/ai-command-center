"""Smooth sparkline — rolling deque + canvas line."""

from __future__ import annotations

import collections
import tkinter as tk

from ai_command_center.ui.design_system import theme_v2 as T


class Sparkline(tk.Canvas):
    def __init__(
        self,
        master,
        *,
        chart_width: int = 200,
        chart_height: int = 48,
        maxlen: int = 40,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            width=chart_width,
            height=chart_height,
            highlightthickness=0,
            bd=0,
            bg=T.GLASS_BG,
            **kwargs,
        )
        self._chart_w = chart_width
        self._chart_h = chart_height
        self._values: collections.deque[float] = collections.deque(maxlen=maxlen)

    def push(self, value: float) -> None:
        self._values.append(max(0.0, value))
        self._redraw()

    def set_values(self, values: list[float]) -> None:
        self._values.clear()
        for v in values[-40:]:
            self._values.append(max(0.0, float(v)))
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        if len(self._values) < 2:
            return
        vals = list(self._values)
        vmax = max(max(vals), 1.0)
        pad = 4
        inner_w = self._chart_w - pad * 2
        inner_h = self._chart_h - pad * 2
        step = inner_w / max(len(vals) - 1, 1)
        coords: list[float] = []
        for i, v in enumerate(vals):
            x = pad + i * step
            y = pad + inner_h - (v / vmax) * inner_h
            coords.extend([x, y])
        self.create_line(*coords, fill=T.ACCENT_PRIMARY, width=2, smooth=True)
