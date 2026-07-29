"""Universal command input — dominant Mission Control command surface."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.mission_control.action_chips import ActionChips


class CommandBox(ctk.CTkFrame):
    """Persistent command bar with interactive chips and focus-only hints."""

    def __init__(
        self,
        master,
        on_submit,
        on_help=None,
        on_palette: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_submit = on_submit
        self._on_help = on_help
        self._on_palette = on_palette

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")

        ctk.CTkLabel(
            row,
            text="⌘",
            font=(T.FONT_FAMILY, 16),
            text_color=T.ACCENT_DEFAULT,
            width=22,
        ).pack(side="left", padx=(0, 6))

        self._entry = ctk.CTkEntry(
            row,
            placeholder_text="What would you like to accomplish today?",
            height=44,
            font=T.FONT_BODY,
            fg_color=T.BG_INPUT,
            border_width=1,
            border_color=T.GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        self._entry.pack(side="left", fill="x", expand=True)
        self._entry.bind("<Return>", self._submit)
        self._entry.bind("<FocusIn>", self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._entry.bind("<Control-k>", self._open_palette)
        self._entry.bind("<Control-K>", self._open_palette)

        if on_palette is not None:
            ctk.CTkButton(
                row,
                text="Ctrl+K",
                width=64,
                height=44,
                font=T.FONT_SMALL,
                fg_color=T.BG_GLASS,
                hover_color=T.LIGHT_GLASS,
                text_color=T.TEXT_MUTED,
                border_width=1,
                border_color=T.GLASS_BORDER,
                command=on_palette,
            ).pack(side="right", padx=(8, 0))

        if on_help is not None:
            ctk.CTkButton(
                row,
                text="?",
                width=36,
                height=44,
                font=T.FONT_BODY,
                command=on_help,
            ).pack(side="right", padx=(8, 0))

        # Syntax hints — only visible on focus (never a permanent wall of text)
        self._hint = ctk.CTkLabel(
            self,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._hint.pack(fill="x", pady=(4, 0))
        self._hint_visible = False

        self._chips = ActionChips(self, on_chip=self.prefill)
        self._chips.pack(fill="x", pady=(6, 0))

    def _open_palette(self, _event=None) -> str | None:
        if self._on_palette is not None:
            self._on_palette()
        return "break"

    def _on_focus_in(self, _event=None) -> None:
        self._hint.configure(
            text="Hints: natural language · > shell · note: · remember: · memory: · go settings · goal:"
        )
        self._hint_visible = True
        try:
            self._entry.configure(border_color=T.FOCUS_RING)
        except Exception:
            pass

    def _on_focus_out(self, _event=None) -> None:
        self._hint.configure(text="")
        self._hint_visible = False
        try:
            self._entry.configure(border_color=T.GLASS_BORDER)
        except Exception:
            pass

    def prefill(self, text: str) -> None:
        """Pre-fill the entry from an action chip; focus for continued typing."""
        self._entry.delete(0, "end")
        self._entry.insert(0, text)
        self.focus()
        # Auto-submit complete phrases (no trailing space / pipe prompt)
        stripped = text.strip()
        if stripped and not text.endswith((" ", "| ", ": ")):
            # leave in box for edit; user presses Enter
            pass

    def set_text(self, text: str) -> None:
        self.prefill(text)

    def _submit(self, _event=None) -> None:
        text = self._entry.get().strip()
        if text:
            self._on_submit(text)
        self._entry.delete(0, "end")

    def focus(self) -> None:
        self._entry.focus_set()
