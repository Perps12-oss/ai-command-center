"""Keyboard shortcut overlay — press ? to open, Esc or click to close."""
from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

_SHORTCUTS: tuple[tuple[str, str], ...] = (
    ("Ctrl+K",        "Open command palette"),
    ("?",             "Show this overlay"),
    ("Alt+Space",     "Show / hide window"),
    ("Esc",           "Clear command box"),
    ("↑ / ↓",        "Cycle command hints"),
    ("Enter",         "Submit command"),
    ("note: …",       "Search vault"),
    ("remember: …",   "Store a memory"),
    ("memory: …",     "Recall stored facts"),
    ("> …",           "Run shell command"),
    ("summarize …",   "Summarize clipboard"),
    ("⟨ / ⟩",        "Collapse / expand sidebar"),
)


class ShortcutOverlay(ctk.CTkToplevel):
    """Translucent overlay listing all keyboard shortcuts.

    Call show() to open; Escape or clicking anywhere closes it.
    """

    def __init__(self, master) -> None:
        super().__init__(master)
        self._master_ref = master
        self.withdraw()
        self.overrideredirect(True)
        self.configure(fg_color=T.BG_GLASS_BORDER)

        inner = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=12)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        hdr = ctk.CTkFrame(inner, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(16, 8))
        ctk.CTkLabel(
            hdr,
            text="Keyboard Shortcuts",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")
        ctk.CTkButton(
            hdr,
            text="✕",
            width=28,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            hover_color=T.STATUS_ERROR,
            text_color=T.TEXT_MUTED,
            corner_radius=6,
            command=self.hide,
        ).pack(side="right")

        ctk.CTkFrame(inner, height=1, fg_color=T.BG_GLASS_BORDER).pack(
            fill="x", padx=12, pady=(0, 12)
        )

        grid = ctk.CTkFrame(inner, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        cols = 2
        for i, (key, desc) in enumerate(_SHORTCUTS):
            row_f = ctk.CTkFrame(grid, fg_color="transparent")
            row_f.grid(row=i // cols, column=i % cols, sticky="w", padx=10, pady=5)

            key_lbl = ctk.CTkFrame(
                row_f,
                fg_color=T.BG_GLASS,
                corner_radius=4,
                height=24,
            )
            key_lbl.pack(side="left")
            key_lbl.pack_propagate(False)
            ctk.CTkLabel(
                key_lbl,
                text=key,
                font=T.FONT_MONO,
                text_color=T.ACCENT_DEFAULT,
                width=max(80, len(key) * 8 + 16),
            ).pack(padx=6, pady=2)

            ctk.CTkLabel(
                row_f,
                text=f"  {desc}",
                font=T.FONT_SMALL,
                text_color=T.TEXT_SECONDARY,
            ).pack(side="left")

        self.bind("<Escape>", lambda _: self.hide())
        inner.bind("<Button-1>", lambda _: self.hide())

    def show(self) -> None:
        mx = self._master_ref.winfo_x()
        my = self._master_ref.winfo_y()
        mw = self._master_ref.winfo_width()
        mh = self._master_ref.winfo_height()
        w, h = 640, 440
        x = mx + (mw - w) // 2
        y = my + (mh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.deiconify()
        self.lift()
        self.focus_force()

    def hide(self) -> None:
        self.withdraw()
