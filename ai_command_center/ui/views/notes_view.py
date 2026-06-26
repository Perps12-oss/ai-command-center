"""Obsidian note search results — Phase 3C."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.theme import tokens as T


class NotesView(ctk.CTkFrame):
    def __init__(self, master, on_select, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_select = on_select

        card = GlassCard(self)
        card.pack(fill="both", expand=True, padx=T.PAD, pady=T.PAD)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        ctk.CTkLabel(
            header,
            text="Notes",
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")

        self._status = ctk.CTkLabel(
            header,
            text="Search with note: query",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        )
        self._status.pack(side="left", padx=(12, 0))

        self._selected = ctk.CTkLabel(
            card,
            text="",
            font=T.FONT_SMALL,
            text_color=T.STATUS_READY,
            anchor="w",
            justify="left",
        )
        self._selected.pack(fill="x", padx=T.PAD, pady=(0, 8))

        self._scroll = ctk.CTkScrollableFrame(card, fg_color=T.BG_DEEP)
        self._scroll.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))

    def show_results(self, query: str, results: list[dict]) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()

        if not results:
            self._status.configure(
                text=f'No results for "{query}"',
                text_color=T.TEXT_MUTED,
            )
            return

        self._status.configure(
            text=f'{len(results)} result(s) for "{query}"',
            text_color=T.TEXT_SECONDARY,
        )
        for item in results:
            path = str(item.get("path", ""))
            title = str(item.get("title", path))
            snippet = str(item.get("snippet", ""))
            row = ctk.CTkFrame(self._scroll, fg_color=T.BG_GLASS, corner_radius=8)
            row.pack(fill="x", pady=4)

            ctk.CTkLabel(
                row,
                text=title,
                font=T.FONT_HEADER,
                text_color=T.TEXT_PRIMARY,
                anchor="w",
            ).pack(fill="x", padx=12, pady=(8, 0))

            ctk.CTkLabel(
                row,
                text=path,
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=12)

            if snippet:
                ctk.CTkLabel(
                    row,
                    text=snippet,
                    font=T.FONT_BODY,
                    text_color=T.TEXT_SECONDARY,
                    anchor="w",
                    justify="left",
                    wraplength=640,
                ).pack(fill="x", padx=12, pady=(0, 4))

            ctk.CTkButton(
                row,
                text="Use in chat",
                width=100,
                height=28,
                font=T.FONT_SMALL,
                command=lambda p=path: self._on_select(p),
            ).pack(anchor="e", padx=12, pady=(0, 8))

    def show_selected(self, path: str, title: str) -> None:
        self._selected.configure(text=f"Injecting into next chat: {title} ({path})")

    def show_error(self, message: str) -> None:
        self._status.configure(text=message, text_color=T.STATUS_ERROR)

    def show_created(self, path: str, title: str) -> None:
        self._status.configure(
            text=f'Created "{title}" at {path}',
            text_color=T.STATUS_READY,
        )
