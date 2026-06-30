"""Command history drawer — slide-in panel showing last 50 cross-session commands."""
from __future__ import annotations

import time
from collections import deque

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

_MAX_HISTORY = 50


class _HistoryRow(ctk.CTkFrame):
    def __init__(self, master, text: str, ts: str, on_rerun) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            corner_radius=T.SMALL_RADIUS,
        )
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(
            inner,
            text=ts,
            font=T.FONT_MONO,
            text_color=T.TEXT_MUTED,
            width=54,
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            inner,
            text=text[:80] + ("…" if len(text) > 80 else ""),
            font=T.FONT_SMALL,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
            wraplength=220,
            justify="left",
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        ctk.CTkButton(
            inner,
            text="↩",
            width=24, height=22,
            font=(T.FONT_FAMILY, 11),
            fg_color="transparent",
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=T.SMALL_RADIUS,
            command=lambda t=text: on_rerun(t),
        ).pack(side="right")


class CommandHistoryDrawer(ctk.CTkFrame):
    """Slide-in panel of last 50 commands, accessible via Ctrl+H.

    Architecture contract:
      • No EventBus, service, or backend imports.
      • push(text) — add a command from UIQueue callback in app.py.
      • show() / hide() — called from app.py on Ctrl+H.
    """

    def __init__(self, master, *, on_rerun=None, **kwargs) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=0,
            width=320,
            **kwargs,
        )
        self._on_rerun = on_rerun
        self._entries: deque[tuple[str, str]] = deque(maxlen=_MAX_HISTORY)
        self._visible = False

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        ctk.CTkLabel(
            hdr,
            text="COMMAND HISTORY",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(side="left")

        ctk.CTkButton(
            hdr, text="✕",
            width=22, height=22,
            font=T.FONT_SMALL,
            fg_color="transparent",
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=T.SMALL_RADIUS,
            command=self.hide,
        ).pack(side="right")

        # Clear button
        ctk.CTkButton(
            self, text="Clear history",
            height=24,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=T.SMALL_RADIUS,
            command=self._clear,
        ).pack(fill="x", padx=T.PAD, pady=(0, 4))

        # Scrollable list
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True, padx=0, pady=0)

        self._render()

    # ── public API ──────────────────────────────────────────────────────────

    def push(self, text: str) -> None:
        ts = time.strftime("%H:%M")
        self._entries.appendleft((text, ts))
        self._render()

    def show(self) -> None:
        if not self._visible:
            self._visible = True
            self.pack(fill="y", side="right", before=None)
            self.lift()

    def hide(self) -> None:
        if self._visible:
            self._visible = False
            self.pack_forget()

    def toggle(self) -> None:
        if self._visible:
            self.hide()
        else:
            self.show()

    # ── internal ────────────────────────────────────────────────────────────

    def _clear(self) -> None:
        self._entries.clear()
        self._render()

    def _render(self) -> None:
        for w in self._scroll.winfo_children():
            w.destroy()
        if not self._entries:
            ctk.CTkLabel(
                self._scroll,
                text="No commands yet.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=T.PAD, pady=8)
            return
        for text, ts in self._entries:
            row = _HistoryRow(self._scroll, text, ts, self._rerun)
            row.pack(fill="x", padx=4, pady=2)

    def _rerun(self, text: str) -> None:
        self.hide()
        if self._on_rerun:
            self._on_rerun(text)
