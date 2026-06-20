"""4-layer rendering stack — compiler-mandated z-order."""

from __future__ import annotations

import tkinter as tk

from ai_command_center.ui.layer.background_canvas import BackgroundCanvas
from ai_command_center.ui.layer.background_spec import Z_INDEX

SHELL_BACKDROP_ACTIVE = True

# Uncovered canvas margin around non-home page hosts (wallpaper visible in gaps).
PAGE_VIEW_MARGIN_X = 0.06
PAGE_VIEW_MARGIN_Y = 0.055


class DepthLayer(tk.Frame):
    """L2 — glass elevation host (non-interactive shell)."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, highlightthickness=0, bd=0, **kwargs)


class PageLayerStack(tk.Frame):
    """
    Transparent tk page root embedded in canvas create_window.

    Uses tk.Frame (no painted panel) so uncovered canvas shows the wallpaper.
    """

    def __init__(self, master, page_id: str, **kwargs) -> None:
        super().__init__(master, highlightthickness=0, bd=0, **kwargs)
        self.page_id = page_id

        self.background_canvas = BackgroundCanvas(self, page_id)
        self.background_canvas.place_forget()

        self.ui_layer = tk.Frame(self, highlightthickness=0, bd=0)
        self.ui_layer.pack(anchor="n", fill="x")

        self._z = Z_INDEX

    def hide_background_for_compact(self) -> None:
        self.background_canvas.place_forget()
        self.background_canvas.canvas.place_forget()

    def show_background(self) -> None:
        if SHELL_BACKDROP_ACTIVE:
            self.background_canvas.place_forget()
            return
        self.background_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.background_canvas.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.background_canvas.lower()
        self.background_canvas.refresh()
