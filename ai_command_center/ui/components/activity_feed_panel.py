"""Scrolling terminal activity feed — deque-backed activity bus."""

from __future__ import annotations

import collections

import customtkinter as ctk

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import SYSTEM_EVENTS
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.theme import tokens as T


class ActivityFeedPanel(GlassCard):
    def __init__(self, master, *, bus: EventBus | None = None, **kwargs) -> None:
        super().__init__(
            master,
            with_shadow=False,
            fg_color=T.LIGHT_GLASS,
            corner_radius=T.CARD_RADIUS,
            **kwargs,
        )

        self._bus = bus
        self._lines: collections.deque[str] = collections.deque(maxlen=100)
        self._unsub = None

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(8, 4))
        ctk.CTkLabel(
            header,
            text="Activity Feed",
            font=T.FONT_HEADER,
            text_color=T.TEXT_HEADING,
        ).pack(side="left")

        self._text = ctk.CTkTextbox(
            self,
            font=T.FONT_MONO,
            fg_color="transparent",
            text_color=T.TEXT_LOG,
            height=160,
            wrap="none",
            activate_scrollbars=True,
        )
        self._text.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        self._text.configure(state="disabled")
        self._text.tag_config("success", foreground=T.HERO_CYAN)
        self._text.tag_config("warning", foreground=T.STATUS_BUSY)
        self._text.tag_config("muted", foreground=T.TEXT_MUTED)

        if bus is not None:
            self.mount_bus(bus)

    def mount_bus(self, bus: EventBus) -> None:
        if self._unsub is not None:
            self._unsub()
        self._bus = bus
        self._unsub = bus.subscribe(SYSTEM_EVENTS, self._on_activity)

    def _on_activity(self, event: Event) -> None:
        kind = str(event.payload.get("event", event.payload.get("kind", "event")))
        tag = "success"
        if "warn" in kind.lower() or "error" in kind.lower():
            tag = "warning"
        self.append_line(kind, tag=tag)

    def append_line(self, line: str, *, tag: str = "muted") -> None:
        text = line.strip()
        if not text:
            return
        self._lines.append(text)
        self._text.configure(state="normal")
        self._text.insert("end", text + "\n", tag)
        self._text.see("end")
        self._text.configure(state="disabled")

    def push_command(self, detail: str) -> None:
        self.append_line(f"cmd · {detail}", tag="muted")

    def clear(self) -> None:
        self._lines.clear()
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")

    def destroy(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        super().destroy()
