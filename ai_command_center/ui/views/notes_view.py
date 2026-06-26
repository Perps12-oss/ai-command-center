"""Obsidian note search results — Phase 3C."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T


class NotesView(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_select,
        on_search=None,
        on_create=None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_select = on_select
        self._on_search = on_search
        self._on_create = on_create

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

        if self._on_create is not None:
            ctk.CTkButton(
                header,
                text="+ New note",
                width=90,
                height=28,
                font=T.FONT_SMALL,
                fg_color=T.ACCENT_DEFAULT,
                hover_color=T.ACCENT_HOVER,
                text_color="white",
                corner_radius=T.SMALL_RADIUS,
                command=self._show_create_dialog,
            ).pack(side="right")

        self._search = ctk.CTkEntry(
            card,
            placeholder_text="Search notes…",
            font=T.FONT_BODY,
            height=32,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        self._search.pack(fill="x", padx=T.PAD, pady=(0, 8))
        self._search.bind("<Return>", lambda _e: self._publish_search())

        self._selected = ctk.CTkLabel(
            card,
            text="",
            font=T.FONT_SMALL,
            text_color=T.STATUS_READY,
            anchor="w",
            justify="left",
        )
        self._selected.pack(fill="x", padx=T.PAD, pady=(0, 8))

        self._scroll = ctk.CTkScrollableFrame(card, fg_color=T.BG_DEEP, height=220)
        self._scroll.pack(fill="x", padx=T.PAD, pady=(0, 8))
        self._scroll.pack_propagate(False)

        self._preview = ctk.CTkFrame(card, fg_color=T.BG_GLASS, corner_radius=T.CARD_RADIUS)
        self._preview.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        self._preview_title = ctk.CTkLabel(
            self._preview,
            text="Preview",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._preview_title.pack(fill="x", padx=12, pady=(10, 4))
        self._preview_path = ctk.CTkLabel(
            self._preview,
            text="Select a note to preview",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._preview_path.pack(fill="x", padx=12)
        self._preview_text = ctk.CTkTextbox(
            self._preview,
            font=T.FONT_BODY,
            fg_color="transparent",
            text_color=T.TEXT_SECONDARY,
            wrap="word",
            activate_scrollbars=True,
        )
        self._preview_text.pack(fill="both", expand=True, padx=12, pady=(4, 10))
        self._preview_text.configure(state="disabled")

    def _publish_search(self) -> None:
        query = self._search.get().strip()
        if query and self._on_search is not None:
            self._on_search(query)

    def load_from_appstate(self, snap) -> None:
        """Render notes catalog and selected note from AppState projection."""
        results = [
            {"path": item.path, "title": item.title, "snippet": item.snippet}
            for item in snap.notes_catalog
        ]
        self.show_results("", results)
        selected = snap.note_selected
        if selected:
            self.show_preview(selected.path, selected.title, selected.snippet)

    def show_results(self, query: str, results: list[dict]) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()

        if not results:
            self._status.configure(
                text='No results',
                text_color=T.TEXT_MUTED,
            )
            return

        self._status.configure(
            text=f'{len(results)} note(s)',
            text_color=T.TEXT_SECONDARY,
        )
        for item in results:
            path = str(item.get("path", ""))
            title = str(item.get("title", path))
            snippet = str(item.get("snippet", ""))
            row = ctk.CTkFrame(self._scroll, fg_color=T.BG_GLASS, corner_radius=T.CARD_RADIUS)
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
                command=lambda p=path, t=title: self._on_select(p, t),
            ).pack(anchor="e", padx=12, pady=(0, 8))

            row.bind("<Button-1>", lambda _e, p=path, t=title: self._on_select(p, t))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda _e, p=path, t=title: self._on_select(p, t))

    def show_preview(self, path: str, title: str, body: str) -> None:
        self._preview_title.configure(text=title or "Preview")
        self._preview_path.configure(text=path)
        self._preview_text.configure(state="normal")
        self._preview_text.delete("1.0", "end")
        self._preview_text.insert("1.0", body[:2000] or "No preview available.")
        self._preview_text.configure(state="disabled")

    def _show_create_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("New note")
        dialog.configure(fg_color=T.BG_PANEL)
        dialog.geometry("440x320")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Title / filename",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 2))
        title_entry = ctk.CTkEntry(
            dialog,
            font=T.FONT_BODY,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        title_entry.pack(fill="x", padx=T.PAD)

        ctk.CTkLabel(
            dialog,
            text="Content",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(8, 2))
        content_box = ctk.CTkTextbox(
            dialog,
            font=T.FONT_BODY,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
            wrap="word",
            height=120,
        )
        content_box.pack(fill="x", padx=T.PAD, pady=(0, 8))

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(padx=T.PAD, pady=(0, 12))

        def _cancel() -> None:
            dialog.destroy()

        def _confirm() -> None:
            title = title_entry.get().strip()
            content = content_box.get("1.0", "end").strip()
            if title and content and self._on_create is not None:
                self._on_create(title, content)
            dialog.destroy()

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
            command=_cancel,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_row,
            text="Create",
            font=T.FONT_SMALL,
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color="white",
            command=_confirm,
        ).pack(side="left")

    def show_selected(self, path: str, title: str) -> None:
        self._selected.configure(text=f"Injecting into next chat: {title} ({path})")

    def show_error(self, message: str) -> None:
        self._status.configure(text=message, text_color=T.STATUS_ERROR)

    def show_created(self, path: str, title: str) -> None:
        self._status.configure(
            text=f'Created "{title}" at {path}',
            text_color=T.STATUS_READY,
        )
