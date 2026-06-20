"""Shell-level backdrop — blurred global wallpaper via tk.Canvas + create_window."""

from __future__ import annotations

import tkinter as tk
from typing import Any

from ai_command_center.ui.layer.background_image import paint_canvas
from ai_command_center.ui.layer.background_spec import get_page_background, resolve_image_path
from ai_command_center.ui.layer.layer_stack import PAGE_VIEW_MARGIN_X, PAGE_VIEW_MARGIN_Y
from ai_command_center.ui.spatial.canvas_zones import CanvasZoneMount
from ai_command_center.ui.theme import tokens as T


class ShellBackdrop(tk.Frame):
    """
    Pure tk host on the right panel.

    Canvas paints blurred JPG full-bleed. UI mounts via create_window (inset for
    full pages, zoned for home) so uncovered canvas shows the wallpaper.
    """

    def __init__(self, master, page_id: str = "home", **kwargs) -> None:
        super().__init__(master, highlightthickness=0, bd=0, **kwargs)
        self.page_id = page_id
        self._photo: object | None = None
        self._last_size = (0, 0)
        self._blur_cache: tuple[int, int, float, float] | None = None
        spec = get_page_background(page_id)
        self._blur_spec = dict(spec.get("blur", {}))
        self._image_path = resolve_image_path(
            str(spec.get("image", "backgrounds/command_center_bg.jpg"))
        )

        self.canvas = tk.Canvas(
            self,
            highlightthickness=0,
            bd=0,
            bg=T.CANVAS_FALLBACK,
            relief="flat",
        )
        self.canvas.pack(fill="both", expand=True)

        self._zones = CanvasZoneMount(self.canvas, page_id)
        self._page_win_id: int | None = None
        self._page_widget: tk.Misc | None = None

        self.bind("<Configure>", self._on_resize, add="+")
        self.bind("<Map>", lambda _e: self.after_idle(self.refresh), add="+")
        self.after_idle(self.refresh)

    @property
    def page_host(self) -> tk.Frame:
        """Master for non-home PageLayerStack views (direct child of shell)."""
        return self

    def get_zone_host(self, zone_id: str) -> tk.Frame:
        host = tk.Frame(self, highlightthickness=0, bd=0)
        self.embed_zone_widget(host, zone_id)
        return host

    def embed_zone_widget(self, widget: Any, zone_id: str, **kwargs) -> None:
        self._zones.embed_zone_widget(widget, zone_id, **kwargs)

    def set_zones_visible(self, visible: bool) -> None:
        self._zones.set_zones_visible(visible)

    def set_home_zones_visible(self, visible: bool) -> None:
        self.set_zones_visible(visible)

    @property
    def home_zones_visible(self) -> bool:
        return self._zones.zones_visible

    def clear_zone_motion(self) -> None:
        for item in self.canvas.find_withtag("zone_motion"):
            self.canvas.delete(item)

    def mount_page_view(self, widget: tk.Misc) -> None:
        """Non-home: embed page root directly — no opaque page wrapper."""
        self._zones.set_zones_visible(False)
        self.clear_zone_motion()
        self._page_widget = widget
        self._sync_page_window()

    def unmount_page_view(self) -> None:
        self.clear_zone_motion()
        self._page_widget = None
        if self._page_win_id is not None:
            self.canvas.delete(self._page_win_id)
            self._page_win_id = None

    def _page_window_geometry(self) -> tuple[int, int, int, int]:
        w = max(self.canvas.winfo_width(), 1)
        h = max(self.canvas.winfo_height(), 1)
        mx = PAGE_VIEW_MARGIN_X
        my = PAGE_VIEW_MARGIN_Y
        ww = max(int(w * (1.0 - 2 * mx)), 120)
        wh = max(int(h * (1.0 - 2 * my)), 80)
        cx = w // 2
        cy = h // 2
        return cx, cy, ww, wh

    def _sync_page_window(self) -> None:
        if self._page_widget is None:
            return
        self.update_idletasks()
        w = max(self.canvas.winfo_width(), 1)
        h = max(self.canvas.winfo_height(), 1)
        if w <= 1 or h <= 1:
            self.after(50, self._sync_page_window)
            return
        cx, cy, ww, wh = self._page_window_geometry()
        if self._page_win_id is None:
            self._page_win_id = self.canvas.create_window(
                cx,
                cy,
                window=self._page_widget,
                anchor="center",
                tags=("page_view",),
            )
        else:
            self.canvas.coords(self._page_win_id, cx, cy)
        self.canvas.itemconfigure(
            self._page_win_id,
            width=ww,
            height=wh,
            state="normal",
        )
        self.canvas.tag_raise(self._page_win_id)

    def refresh(self) -> None:
        if not self.winfo_exists():
            return
        try:
            if not self.canvas.winfo_exists():
                return
        except Exception:
            return
        self.update_idletasks()
        w = max(self.winfo_width(), 1)
        h = max(self.winfo_height(), 1)
        if w <= 1 or h <= 1:
            self.after(50, self.refresh)
            return
        if self._image_path is None:
            return

        blur_enabled = bool(self._blur_spec.get("enabled", True))
        radius = float(self._blur_spec.get("radius", 12)) if blur_enabled else 0.0
        vignette = float(self._blur_spec.get("vignette_dim", 0)) if blur_enabled else 0.0
        cache_key = (w, h, radius, vignette)
        if cache_key != self._blur_cache or self._photo is None:
            photo = paint_canvas(
                self.canvas,
                self._image_path,
                (w, h),
                blur_radius=radius,
                vignette_dim=vignette,
            )
            if photo is not None:
                self._photo = photo
                self._last_size = (w, h)
                self._blur_cache = cache_key

        self._zones.reposition()
        if self._page_widget is not None:
            self._sync_page_window()
        if self._zones.zones_visible:
            for item in self.canvas.find_withtag("zone_ui"):
                self.canvas.tag_raise(item)
        if self._page_win_id is not None:
            self.canvas.tag_raise(self._page_win_id)

    def _on_resize(self, event) -> None:
        if event.widget is not self:
            return
        size = (max(event.width, 1), max(event.height, 1))
        if size != self._last_size and size[0] > 1 and size[1] > 1:
            self._blur_cache = None
            self.refresh()

    @property
    def image_loaded(self) -> bool:
        return self._photo is not None

    def show(self) -> None:
        self.pack(fill="both", expand=True)
        self.refresh()

    def hide(self) -> None:
        self.pack_forget()


ContentBackdrop = ShellBackdrop
