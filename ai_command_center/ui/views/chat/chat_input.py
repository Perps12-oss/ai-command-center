"""Input pill, templates overlay, and send/stop wiring."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.chat.stream_renderer import CLR_META

_PILL_MAX_LINES = 4
_LINE_H = 22
_PLACEHOLDER = "Message…"
_HINT_TEXT = "⏎ send  ·  Shift+⏎ new line  ·  Ctrl+K  ·  ?"

PROMPT_TEMPLATES: list[tuple[str, str, str]] = [
    ("Summarise",        "Summarise the following: ",             "Condense into key points"),
    ("Explain simply",   "Explain this like I'm 5: ",             "Plain-language explanation"),
    ("Bullet points",    "Give me bullet points for: ",           "List format"),
    ("Pros & cons",      "List the pros and cons of: ",           "Balanced analysis"),
    ("Action items",     "Extract action items from: ",           "Task extraction"),
    ("Write email",      "Write a professional email about: ",    "Email draft"),
    ("Debug help",       "Help me debug this issue: ",            "Code / logic debugging"),
    ("Compare",          "Compare and contrast: ",                "Side-by-side comparison"),
]

CLR_HINT = "#2E2E48"   # keyboard hint — barely visible


class TemplatesOverlay(ctk.CTkFrame):
    """Floating chip grid of prompt templates — shown/hidden above the input pill."""

    def __init__(self, master, on_select: Callable[[str], None]) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.CARD_RADIUS,
        )
        self._on_select = on_select
        self._visible = False
        ctk.CTkLabel(
            self,
            text="PROMPT TEMPLATES",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=12, pady=(8, 4))
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=8, pady=(0, 8))
        for col in range(2):
            grid.columnconfigure(col, weight=1)
        for i, (label, prefix, hint) in enumerate(PROMPT_TEMPLATES):
            chip = ctk.CTkFrame(
                grid,
                fg_color=T.BG_GLASS,
                border_color=T.BG_GLASS_BORDER,
                border_width=1,
                corner_radius=T.SMALL_RADIUS,
            )
            chip.grid(row=i // 2, column=i % 2, sticky="ew", padx=4, pady=2)
            ctk.CTkLabel(
                chip, text=label, font=T.FONT_SMALL, text_color=T.TEXT_PRIMARY, anchor="w"
            ).pack(side="left", padx=(8, 4), pady=4)
            ctk.CTkLabel(
                chip, text=hint, font=(T.FONT_FAMILY, 9), text_color=T.TEXT_MUTED, anchor="e"
            ).pack(side="right", padx=(0, 8), pady=4)
            chip.bind("<Button-1>", lambda _e, p=prefix: self._pick(p))
            for w in chip.winfo_children():
                w.bind("<Button-1>", lambda _e, p=prefix: self._pick(p))

    def _pick(self, prefix: str) -> None:
        self._on_select(prefix)
        self.hide()

    def show_above(self, anchor_widget) -> None:
        if self._visible:
            self.hide()
            return
        self._visible = True
        self.place(
            in_=anchor_widget,
            relx=0.0, rely=0.0,
            anchor="sw",
            bordermode="outside",
        )
        self.lift()

    def hide(self) -> None:
        self._visible = False
        self.place_forget()


class InputPill(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_send: Callable[[str], None] | None,
        on_stop: Callable[[], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            corner_radius=0,
        )
        self._on_send = on_send
        self._on_stop = on_stop
        self._streaming = False
        self._ph_active = True

        pill = ctk.CTkFrame(
            self,
            fg_color=T.BG_GLASS,
            corner_radius=28,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
        )
        pill.pack(fill="x", padx=16, pady=(10, 4))

        self._tmpl_btn = ctk.CTkButton(
            pill, text="⊞",
            width=34, height=34,
            font=(T.FONT_FAMILY, 16),
            fg_color="transparent",
            hover_color=T.BG_GLASS_BORDER,
            text_color=CLR_META,
            corner_radius=17,
            command=self._toggle_templates,
        )
        self._tmpl_btn.pack(side="left", padx=(8, 0), pady=5)
        self._templates_overlay: TemplatesOverlay | None = None

        self._tb = ctk.CTkTextbox(
            pill,
            font=T.FONT_BODY,
            fg_color="transparent",
            text_color=T.TEXT_PRIMARY,
            wrap="word",
            activate_scrollbars=False,
            height=34,
            border_width=0,
            corner_radius=0,
        )
        self._tb.pack(side="left", fill="x", expand=True, padx=6, pady=5)
        self._tb.insert("1.0", _PLACEHOLDER)
        self._tb.configure(text_color=CLR_META)
        self._tb.bind("<FocusIn>",    self._focus_in)
        self._tb.bind("<FocusOut>",   self._focus_out)
        self._tb.bind("<Return>",     self._on_enter)
        self._tb.bind("<KeyRelease>", self._grow)

        self._btn = ctk.CTkButton(
            pill, text="▶",
            width=34, height=34,
            font=(T.FONT_FAMILY, 13, "bold"),
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=17,
            command=self._action,
        )
        self._btn.pack(side="right", padx=(0, 8), pady=5)

        ctk.CTkLabel(
            self,
            text=_HINT_TEXT,
            font=(T.FONT_FAMILY, 9),
            text_color=CLR_HINT,
        ).pack(side="left", padx=20, pady=(0, 5))

        self._status = ctk.CTkLabel(
            self, text="",
            font=(T.FONT_FAMILY, 10),
            text_color=CLR_META,
        )
        self._status.pack(side="right", padx=20, pady=(0, 5))

    def _focus_in(self, _=None) -> None:
        if self._ph_active:
            self._tb.delete("1.0", "end")
            self._tb.configure(text_color=T.TEXT_PRIMARY)
            self._ph_active = False

    def _focus_out(self, _=None) -> None:
        if not self._tb.get("1.0", "end-1c").strip():
            self._tb.insert("1.0", _PLACEHOLDER)
            self._tb.configure(text_color=CLR_META)
            self._ph_active = True
            self._tb.configure(height=34)

    def _grow(self, _=None) -> None:
        if self._ph_active:
            return
        lines = int(self._tb.index("end-1c").split(".")[0])
        h = max(34, min(lines * _LINE_H, _PILL_MAX_LINES * _LINE_H))
        self._tb.configure(height=h)

    def _on_enter(self, event) -> str:
        if event.state & 0x1:   # Shift → newline
            return ""
        self._submit()
        return "break"

    def _submit(self) -> None:
        if self._ph_active:
            return
        text = self._tb.get("1.0", "end-1c").strip()
        if not text:
            return
        if self._on_send:
            self._tb.delete("1.0", "end")
            self._tb.configure(height=34)
            self._focus_out()
            self._on_send(text)

    def _action(self) -> None:
        if self._streaming:
            self._on_stop()
        else:
            self._submit()

    def set_streaming(self, active: bool) -> None:
        self._streaming = active
        if active:
            self._btn.configure(
                text="■", fg_color=T.STATUS_ERROR, hover_color="#8B0000"
            )
            self._status.configure(text="Generating…", text_color=T.STATUS_BUSY)
        else:
            self._btn.configure(
                text="▶", fg_color=T.ACCENT_DEFAULT, hover_color=T.ACCENT_HOVER
            )
            self._status.configure(text="")

    def set_status(self, text: str, color: str = "") -> None:
        self._status.configure(text=text, text_color=color or CLR_META)

    def focus_input(self) -> None:
        self._tb.focus_set()
        self._focus_in()

    def set_templates_overlay(self, overlay: TemplatesOverlay) -> None:
        self._templates_overlay = overlay

    def _toggle_templates(self) -> None:
        if self._templates_overlay:
            self._templates_overlay.show_above(self._tmpl_btn)

    def insert_template(self, prefix: str) -> None:
        self._focus_in()
        current = self._tb.get("1.0", "end-1c")
        self._tb.delete("1.0", "end")
        self._tb.insert("1.0", prefix + current)
        self._tb.mark_set("insert", "end")
        self._tb.focus_set()
        self._grow()
