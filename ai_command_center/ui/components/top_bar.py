"""Top bar: logo, model status, actions."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.theme import tokens as T


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

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=T.PAD, pady=8)

        ctk.CTkLabel(
            left,
            text="◇ AI Command Center",
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")

        self._status = ctk.CTkLabel(
            left,
            text="● Ready",
            font=T.FONT_SMALL,
            text_color=T.STATUS_READY,
        )
        self._status.pack(side="left", padx=(16, 0))

        self._model_label = ctk.CTkLabel(
            left,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        )
        self._model_label.pack(side="left", padx=(12, 0))

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=T.PAD, pady=8)

        ctk.CTkButton(
            right,
            text="⚙",
            width=36,
            height=36,
            font=T.FONT_BODY,
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            command=on_settings,
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            right,
            text="✕",
            width=36,
            height=36,
            font=T.FONT_BODY,
            fg_color=T.BG_GLASS,
            hover_color=T.STATUS_ERROR,
            command=on_close,
        ).pack(side="right", padx=4)

    def update_status(self, phase: str, model: str) -> None:
        if phase in {"starting", "busy"}:
            self._status.configure(text="● Busy", text_color=T.STATUS_BUSY)
        elif phase in {"error", "stopped"}:
            self._status.configure(text="● Error", text_color=T.STATUS_ERROR)
        else:
            self._status.configure(text="● Ready", text_color=T.STATUS_READY)
        self._model_label.configure(text=f"Model: {model}" if model else "")
