"""Canvas text with shadow pass for legibility over blurred backgrounds."""

from __future__ import annotations

import tkinter as tk

from ai_command_center.ui.design_system import theme_v2 as T


class ShadowLabel(tk.Canvas):
    def __init__(
        self,
        master,
        text: str = "",
        *,
        font=None,
        fill: str | None = None,
        anchor: str = "w",
        height: int = 24,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            highlightthickness=0,
            bd=0,
            bg=T.GLASS_BG,
            height=height,
            **kwargs,
        )
        self._text = text
        self._font = font or T.FONT_HEADER
        self._fill = fill or T.TEXT_HEADING
        self._anchor = anchor
        self.bind("<Configure>", self._redraw, add="+")
        self.after_idle(self._redraw)

    def configure(self, **kwargs) -> None:
        if "text" in kwargs:
            self._text = str(kwargs.pop("text"))
        if "font" in kwargs:
            self._font = kwargs.pop("font")
        if "fill" in kwargs:
            self._fill = kwargs.pop("fill")
        if "text_color" in kwargs:
            self._fill = kwargs.pop("text_color")
        if kwargs:
            super().configure(**kwargs)
        self._redraw()

    config = configure

    def _redraw(self, _event=None) -> None:
        self.delete("all")
        h = max(self.winfo_height(), 20)
        w = max(self.winfo_width(), 1)
        if self._anchor in ("w", "nw", "sw"):
            x, y = 2, h // 2
        elif self._anchor in ("e", "ne", "se"):
            x, y = w - 2, h // 2
        else:
            x, y = w // 2, h // 2
        self.create_text(x - 1, y - 1, text=self._text, font=self._font, fill=T.TEXT_SHADOW, anchor=self._anchor)
        self.create_text(x, y, text=self._text, font=self._font, fill=self._fill, anchor=self._anchor)
