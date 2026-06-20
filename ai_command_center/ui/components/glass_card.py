"""Translucent floating panel — subtle slate glass border, clean corners."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from ai_command_center.ui.layer.background_image import create_drop_shadow
from ai_command_center.ui.theme import tokens as T


class GlassCard(ctk.CTkFrame):
    """Floating glass pane — 1px slate border, 16px radius, transparent children."""

    def __init__(self, master, *, with_shadow: bool = False, **kwargs) -> None:
        corner = kwargs.pop("corner_radius", T.CARD_RADIUS)
        fg = kwargs.pop("fg_color", T.GLASS_BG)
        border_w = kwargs.pop("border_width", 1)
        border = kwargs.pop("border_color", T.GLASS_BORDER)
        if border_w == 0:
            border = fg

        self._outer = ctk.CTkFrame(master, fg_color="transparent", corner_radius=0)
        self._shadow_label: tk.Label | None = None
        self._shadow_photo = None
        self._with_shadow = with_shadow

        super().__init__(
            self._outer,
            fg_color=fg,
            border_color=border,
            border_width=border_w,
            corner_radius=corner,
            **kwargs,
        )
        super().pack(fill="both", expand=True)

        if with_shadow:
            self.bind("<Configure>", self._sync_shadow, add="+")
            self.after_idle(self._sync_shadow)

    @property
    def outer(self) -> ctk.CTkFrame:
        return self._outer

    def pack(self, **kwargs):
        return self._outer.pack(**kwargs)

    def grid(self, **kwargs):
        return self._outer.grid(**kwargs)

    def place(self, **kwargs):
        return self._outer.place(**kwargs)

    def pack_forget(self):
        return self._outer.pack_forget()

    def grid_forget(self):
        return self._outer.grid_forget()

    def place_forget(self):
        return self._outer.place_forget()

    def _sync_shadow(self, _event=None) -> None:
        if not self._with_shadow:
            return
        self.update_idletasks()
        w = max(self.winfo_width(), 80)
        h = max(self.winfo_height(), 40)
        try:
            self._shadow_photo = create_drop_shadow(w, h, corner_radius=T.CARD_RADIUS)
        except Exception:
            return
        if self._shadow_label is None:
            self._shadow_label = tk.Label(
                self._outer,
                borderwidth=0,
                highlightthickness=0,
                bg=T.CANVAS_FALLBACK,
            )
            self._shadow_label.place(x=10, y=10)
            super().lift()
        self._shadow_label.configure(image=self._shadow_photo)
        super().lift()
