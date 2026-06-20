"""Top bar: logo, phase-colored status dot, model label, actions."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.theme import tokens as T

_PHASE_MAP: dict[str, tuple[str, str]] = {
    "starting": ("◉ Starting", T.STATUS_BUSY),
    "busy":     ("◉ Busy",     T.STATUS_BUSY),
    "ready":    ("◉ Ready",    T.STATUS_READY),
    "error":    ("◉ Error",    T.STATUS_ERROR),
    "stopped":  ("◉ Stopped",  T.STATUS_ERROR),
}


class TopBar(ctk.CTkFrame):
    def __init__(self, master, on_settings, on_close, **kwargs) -> None:
        super().__init__(
            master,
            height=T.TOP_BAR_HEIGHT,
            fg_color=T.BG_PANEL,
            corner_radius=0,
            **kwargs,
        )
        self.pack_propagate(False)

        # ── Left section ───────────────────────────────────────────────────────
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=T.PAD, pady=8)

        ctk.CTkLabel(
            left,
            text="◇",
            font=(T.FONT_FAMILY, 18, "bold"),
            text_color=T.ACCENT_DEFAULT,
        ).pack(side="left")

        ctk.CTkLabel(
            left,
            text=" AI Command Center",
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")

        # Divider
        ctk.CTkFrame(left, width=1, height=24, fg_color=T.BG_GLASS_BORDER).pack(
            side="left", padx=16
        )

        self._status = ctk.CTkLabel(
            left,
            text="◉ Ready",
            font=T.FONT_SMALL,
            text_color=T.STATUS_READY,
        )
        self._status.pack(side="left")

        self._model_label = ctk.CTkLabel(
            left,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        )
        self._model_label.pack(side="left", padx=(12, 0))

        # ── Right section ──────────────────────────────────────────────────────
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=T.PAD, pady=8)

        ctk.CTkButton(
            right,
            text="⚙",
            width=36,
            height=36,
            font=(T.FONT_FAMILY, 14),
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_SECONDARY,
            corner_radius=6,
            command=on_settings,
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            right,
            text="✕",
            width=36,
            height=36,
            font=(T.FONT_FAMILY, 14),
            fg_color=T.BG_GLASS,
            hover_color=T.STATUS_ERROR,
            text_color=T.TEXT_SECONDARY,
            corner_radius=6,
            command=on_close,
        ).pack(side="right", padx=4)

    def update_status(self, phase: str, model: str) -> None:
        text, color = _PHASE_MAP.get(phase, ("◉ Ready", T.STATUS_READY))
        self._status.configure(text=text, text_color=color)
        if model:
            self._model_label.configure(text=f"  ›  {model}")
        else:
            self._model_label.configure(text="")
