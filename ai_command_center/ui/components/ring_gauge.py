"""Animated ring gauge — tk.Canvas arc with smooth fill."""



from __future__ import annotations




import tkinter as tk



from ai_command_center.ui.design_system import theme_v2 as T





class RingGauge(tk.Canvas):

    def __init__(self, master, size: int = 72, **kwargs) -> None:

        super().__init__(

            master,

            width=size,

            height=size,

            highlightthickness=0,

            bd=0,

            bg=T.GLASS_BG,

            **kwargs,

        )

        self._size = size

        self._target_pct = 0.0

        self._current_pct = 0.0

        self._label = "—"

        self._animating = False



    def set_value(self, pct: float, label: str | None = None) -> None:

        self._target_pct = max(0.0, min(100.0, pct))

        if label is not None:

            self._label = label

        if not self._animating:

            self._animating = True

            self._animate()



    def _animate(self) -> None:

        diff = self._target_pct - self._current_pct

        if abs(diff) < 0.5:

            self._current_pct = self._target_pct

            self._draw()

            self._animating = False

            return

        step = 1.5 if diff > 0 else -1.5

        self._current_pct += step

        self._draw()

        self.after(16, self._animate)



    def _draw(self) -> None:

        self.delete("all")

        s = self._size

        pad = 6

        extent = -360 * (self._current_pct / 100.0)

        self.create_arc(

            pad,

            pad,

            s - pad,

            s - pad,

            start=90,

            extent=extent,

            style="arc",

            outline=T.HERO_CYAN,

            width=4,

        )

        self.create_arc(

            pad,

            pad,

            s - pad,

            s - pad,

            start=90,

            extent=-360,

            style="arc",

            outline=T.GLASS_BORDER,

            width=2,

        )

        cx, cy = s // 2, s // 2

        self.create_text(cx - 1, cy - 1, text=self._label, font=T.FONT_SMALL, fill=T.TEXT_SHADOW)

        self.create_text(cx, cy, text=self._label, font=T.FONT_SMALL, fill=T.TEXT_HEADING)


