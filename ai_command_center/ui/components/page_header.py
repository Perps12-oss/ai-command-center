"""Page header — title + subtitle."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.theme import tokens as T


class PageHeader(ctk.CTkFrame):
    def __init__(
        self,
        master,
        title: str,
        subtitle: str = "",
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        ctk.CTkLabel(
            self,
            text=title,
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x")
        if subtitle:
            ctk.CTkLabel(
                self,
                text=subtitle,
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", pady=(4, 0))
