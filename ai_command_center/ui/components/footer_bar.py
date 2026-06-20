"""Footer bar — Ollama URL, vault path, version."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.theme import tokens as T


class FooterBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master,
            height=T.FOOTER_H,
            fg_color="transparent",
            corner_radius=0,
            **kwargs,
        )
        self.pack_propagate(False)
        self._left = ctk.CTkLabel(
            self,
            text="● System Online",
            font=T.FONT_SMALL,
            text_color=T.STATUS_READY,
            anchor="w",
        )
        self._left.pack(side="left", padx=T.PAD, pady=6)
        self._right = ctk.CTkLabel(
            self,
            text="v1.0.0",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="e",
        )
        self._right.pack(side="right", padx=T.PAD, pady=6)

    def update_info(
        self,
        *,
        ollama_url: str = "",
        vault_path: str = "",
        online: bool = True,
    ) -> None:
        parts = []
        if online:
            parts.append("● System Online")
        else:
            parts.append("● Offline")
        if ollama_url:
            parts.append(ollama_url)
        if vault_path:
            parts.append(vault_path)
        self._left.configure(
            text="  ".join(parts),
            text_color=T.STATUS_READY if online else T.STATUS_ERROR,
        )
