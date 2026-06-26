"""Command palette — Ctrl+K fuzzy-search overlay over all app commands."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

Command = tuple[str, str, Callable[[], None]]


class CommandPalette(ctk.CTkToplevel):
    """Floating command palette.

    Usage::
        palette = CommandPalette(root)
        palette.show(commands)   # list of (label, description, action)
    """

    def __init__(self, master) -> None:
        super().__init__(master)
        self._master_ref = master
        self._commands: list[Command] = []
        self._filtered: list[Command] = []
        self._selected = 0

        self.withdraw()
        self.overrideredirect(True)
        self.configure(fg_color=T.BG_GLASS_BORDER)
        self.resizable(False, False)

        inner = ctk.CTkFrame(self, fg_color=T.BG_GLASS, corner_radius=T.CORNER_RADIUS)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        search_row = ctk.CTkFrame(inner, fg_color="transparent")
        search_row.pack(fill="x", padx=12, pady=(12, 4))

        ctk.CTkLabel(
            search_row,
            text="⌘",
            font=(T.FONT_FAMILY, 16),
            text_color=T.ACCENT_DEFAULT,
            width=22,
        ).pack(side="left")

        self._entry = ctk.CTkEntry(
            search_row,
            placeholder_text="Type a command…",
            font=T.FONT_BODY,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
            height=36,
        )
        self._entry.pack(fill="x", expand=True, side="left", padx=(8, 0))

        ctk.CTkFrame(inner, height=1, fg_color=T.BG_GLASS_BORDER).pack(
            fill="x", padx=8, pady=(8, 0)
        )

        self._list_frame = ctk.CTkScrollableFrame(
            inner, fg_color="transparent", height=280, corner_radius=0
        )
        self._list_frame.pack(fill="both", expand=True, pady=(0, 4))

        hint = ctk.CTkFrame(inner, fg_color="transparent")
        hint.pack(fill="x", padx=12, pady=(0, 10))
        for key, desc in [("↑↓", "navigate"), ("↵", "execute"), ("Esc", "close")]:
            ctk.CTkLabel(
                hint,
                text=key,
                font=T.FONT_MONO,
                text_color=T.ACCENT_DEFAULT,
                width=30,
            ).pack(side="left")
            ctk.CTkLabel(
                hint,
                text=f"{desc}   ",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).pack(side="left")

        self._entry.bind("<KeyRelease>", self._on_key)
        self._entry.bind("<Return>", self._on_enter)
        self._entry.bind("<Up>", self._on_up)
        self._entry.bind("<Down>", self._on_down)
        self._entry.bind("<Escape>", lambda _: self.hide())
        self.bind("<FocusOut>", self._on_focus_out)

    def show(self, commands: list[Command]) -> None:
        self._commands = commands
        self._selected = 0
        self._entry.delete(0, "end")
        self._filter("")

        mx = self._master_ref.winfo_x()
        my = self._master_ref.winfo_y()
        mw = self._master_ref.winfo_width()
        w, h = 560, 420
        x = mx + (mw - w) // 2
        y = my + 70
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.deiconify()
        self.lift()
        self.focus_force()
        self._entry.focus_set()

    def hide(self) -> None:
        self.withdraw()

    def _filter(self, query: str) -> None:
        q = query.lower()
        if q:
            self._filtered = [
                c for c in self._commands
                if q in c[0].lower() or q in c[1].lower()
            ]
        else:
            self._filtered = list(self._commands)
        self._selected = min(self._selected, max(0, len(self._filtered) - 1))
        self._render_list()

    def _render_list(self) -> None:
        for w in self._list_frame.winfo_children():
            w.destroy()

        if not self._filtered:
            ctk.CTkLabel(
                self._list_frame,
                text="No commands found",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).pack(padx=16, pady=20)
            return

        for i, (label, desc, _) in enumerate(self._filtered):
            is_sel = i == self._selected
            row = ctk.CTkFrame(
                self._list_frame,
                fg_color=T.BG_PANEL if is_sel else "transparent",
                corner_radius=T.SMALL_RADIUS,
                height=44,
            )
            row.pack(fill="x", padx=8, pady=2)
            row.pack_propagate(False)

            ctk.CTkLabel(
                row,
                text=label,
                font=T.FONT_BODY,
                text_color=T.TEXT_PRIMARY if is_sel else T.TEXT_SECONDARY,
                anchor="w",
            ).pack(side="left", padx=12, pady=4)

            ctk.CTkLabel(
                row,
                text=desc,
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="e",
            ).pack(side="right", padx=12, pady=4)

            idx = i
            for widget in (row,):
                widget.bind("<Button-1>", lambda e, i=idx: self._execute(i))

    def _on_key(self, event) -> None:
        if event.keysym not in ("Up", "Down", "Return", "Escape"):
            self._filter(self._entry.get())

    def _on_up(self, event) -> None:
        self._selected = max(0, self._selected - 1)
        self._render_list()

    def _on_down(self, event) -> None:
        self._selected = min(len(self._filtered) - 1, self._selected + 1)
        self._render_list()

    def _on_enter(self, event) -> None:
        self._execute(self._selected)

    def _execute(self, idx: int) -> None:
        if 0 <= idx < len(self._filtered):
            self.hide()
            _, _, action = self._filtered[idx]
            try:
                action()
            except Exception:
                pass

    def _on_focus_out(self, event) -> None:
        self.after(150, self._check_focus)

    def _check_focus(self) -> None:
        try:
            if self.winfo_exists() and self.focus_get() is None:
                self.hide()
        except Exception:
            pass
