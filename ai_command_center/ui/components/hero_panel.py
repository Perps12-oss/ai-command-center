"""Hero panel — LIVE_CORE static asset + overlay bars (HeroPanel only may use HERO_CYAN)."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from ai_command_center.services.asset_service import AssetService
from ai_command_center.ui.theme import tokens as T

_ASSET = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "hero_core.png"
)


class HeroPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        self._assets = AssetService()
        super().__init__(
            master,
            height=200,
            fg_color=T.BG_GLASS,
            border_color=T.HERO_BORDER_IDLE,
            border_width=1,
            corner_radius=T.HERO_RADIUS,
            **kwargs,
        )
        self.pack_propagate(False)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=T.PAD, pady=T.PAD)

        if _ASSET.is_file():
            try:
                from PIL import Image

                pil = self._assets.load_image(_ASSET)
                pil = pil.resize((320, 80), Image.Resampling.LANCZOS)
                img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(320, 80))
                ctk.CTkLabel(inner, text="", image=img).pack(pady=(8, 4))
            except Exception:
                self._draw_battery(inner)
        else:
            self._draw_battery(inner)

        ctk.CTkLabel(
            inner,
            text="ARTIFICIAL INTELLIGENCE",
            font=(T.FONT_FAMILY, 14, "bold"),
            text_color=T.HERO_CYAN,
        ).pack(pady=(4, 8))

        bars = ctk.CTkFrame(inner, fg_color="transparent")
        bars.pack(fill="x", padx=40)
        self._segments: list[ctk.CTkProgressBar] = []
        for _ in range(3):
            seg = ctk.CTkProgressBar(
                bars,
                height=40,
                width=60,
                progress_color=T.HERO_CYAN,
                fg_color=T.BG_INPUT,
                corner_radius=8,
            )
            seg.pack(side="left", expand=True, fill="x", padx=4)
            seg.set(0.3)
            self._segments.append(seg)

        self.bind("<Enter>", lambda _e: self.configure(border_color=T.HERO_BORDER_HOVER))
        self.bind("<Leave>", lambda _e: self.configure(border_color=T.HERO_BORDER_IDLE))

    def _draw_battery(self, parent) -> None:
        shell = ctk.CTkFrame(
            parent,
            width=280,
            height=70,
            fg_color=T.BG_INPUT,
            border_color=T.HERO_CYAN_DIM,
            border_width=2,
            corner_radius=16,
        )
        shell.pack(pady=8)
        shell.pack_propagate(False)
        row = ctk.CTkFrame(shell, fg_color="transparent")
        row.pack(expand=True, fill="both", padx=12, pady=10)
        for _ in range(3):
            ctk.CTkFrame(
                row,
                fg_color=T.HERO_CYAN_DIM,
                corner_radius=6,
                width=70,
                height=40,
            ).pack(side="left", expand=True, fill="both", padx=3)

    def set_live(self, cpu: float, ram: float, model_load: float, glow: float = 0.5) -> None:
        values = [cpu, ram, model_load]
        for seg, val in zip(self._segments, values, strict=False):
            seg.set(max(0.05, min(1.0, val / 100.0)))
        border = T.HERO_BORDER_HOVER if glow > 0.6 else T.HERO_BORDER_IDLE
        self.configure(border_color=border)
