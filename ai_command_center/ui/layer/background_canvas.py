"""L1 Background canvas — spatial map image plane (non-interactive)."""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from ai_command_center.ui.layer.background_image import paint_canvas
from ai_command_center.ui.layer.background_spec import get_page_background, resolve_image_path, tint_palette
from ai_command_center.ui.spatial.canvas_zones import CanvasZoneMount
from ai_command_center.ui.theme import tokens as T

_log = logging.getLogger(__name__)


def _is_exact_image_mode(spec: dict) -> bool:
    if spec.get("image_mode") == "exact":
        return True
    tint = spec.get("overlay_tint")
    return tint in (None, "", "none", "transparent")


class BackgroundCanvas(ctk.CTkFrame):
    """Paints spatial map on tk.Canvas; optional zone mounts for non-home pages."""

    def __init__(self, master, page_id: str, **kwargs) -> None:
        self._page_id = page_id
        self._spec = get_page_background(page_id)
        self._exact = _is_exact_image_mode(self._spec)
        super().__init__(master, fg_color="transparent", corner_radius=0, **kwargs)

        self._modulation_disabled = (
            self._exact or str(self._spec.get("modulation", "")).lower() == "disabled"
        )
        self._tints = tint_palette()
        self._tint_step = 0 if self._exact else 1
        self._photo: object | None = None
        self._last_size = (0, 0)
        self._image_path: Path | None = resolve_image_path(
            str(self._spec.get("image", "backgrounds/command_center_bg.jpg"))
        )
        if self._image_path is None:
            _log.error("Background image missing for page %s", page_id)

        self.canvas = tk.Canvas(
            self,
            highlightthickness=0,
            bd=0,
            bg=T.CANVAS_FALLBACK,
            relief="flat",
        )
        self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._zones = CanvasZoneMount(self.canvas, page_id)

        self._tint: ctk.CTkFrame | None = None
        if not self._exact:
            self._tint = ctk.CTkFrame(
                self, fg_color=self._tints[self._tint_step], corner_radius=0
            )
            self._tint.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.canvas.bind("<Button-1>", lambda e: "break")
        self.bind("<Configure>", self._on_resize, add="+")
        self.bind("<Map>", lambda _e: self.after_idle(self._refresh_image), add="+")
        self.after_idle(self._refresh_image)

    def embed_zone_widget(self, widget, zone_id: str, **kwargs) -> None:
        self._zones.embed_zone_widget(widget, zone_id, **kwargs)

    def _refresh_image(self) -> None:
        self.update_idletasks()
        w = max(self.winfo_width(), 1)
        h = max(self.winfo_height(), 1)
        if w <= 1 or h <= 1:
            self.after(50, self._refresh_image)
            return
        self._load_image((w, h))

    def _on_resize(self, event) -> None:
        if event.widget is not self:
            return
        size = (max(event.width, 1), max(event.height, 1))
        if size != self._last_size and size[0] > 1 and size[1] > 1:
            self._last_size = size
            self._load_image(size)

    def _load_image(self, size: tuple[int, int]) -> None:
        if self._image_path is None:
            return
        photo = paint_canvas(self.canvas, self._image_path, size)
        if photo is not None:
            self._photo = photo
        self._zones.reposition()

    def refresh(self) -> None:
        self._refresh_image()

    @property
    def image_loaded(self) -> bool:
        return self._photo is not None

    def set_modulation(self, *, tint_step: int | None = None, desaturate: bool = False, dim: float = 0.0, flicker: float = 0.0) -> None:
        if self._modulation_disabled or self._tint is None:
            return
        step = self._tint_step if tint_step is None else max(0, min(len(self._tints) - 1, tint_step))
        if desaturate or dim > 0:
            step = min(len(self._tints) - 1, step + 1)
        if flicker > 0:
            step = min(len(self._tints) - 1, step + 1)
        self._tint_step = step
        self._tint.configure(fg_color=self._tints[step])

    @property
    def page_id(self) -> str:
        return self._page_id
