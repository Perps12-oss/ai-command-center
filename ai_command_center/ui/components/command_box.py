"""Universal command input — Esc to clear, cycling placeholder hints."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.theme import tokens as T

_HINTS: tuple[str, ...] = (
    "Ask anything…",
    "note: keyword  — search Obsidian vault",
    "new note: Title  — create a note",
    "remember: label | content  — store a fact",
    "memory: keyword  — recall stored facts",
    "> shell command  — run in terminal",
    "summarize clipboard  — process copied text",
    "go settings  — open settings panel",
)


class CommandBox(ctk.CTkFrame):
    """Universal command input with:
    - Enter  → submit
    - Esc    → clear or lose focus
    - placeholder cycling every 4 s when idle
    """

    _CYCLE_MS = 4000

    def __init__(self, master, on_submit, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_submit = on_submit
        self._hint_index = 0
        self._cycle_job: str | None = None

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")

        self._entry = ctk.CTkEntry(
            row,
            placeholder_text=_HINTS[0],
            height=44,
            font=T.FONT_BODY,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            text_color=T.TEXT_PRIMARY,
            corner_radius=8,
        )
        self._entry.pack(fill="x", expand=True, side="left")

        submit_btn = ctk.CTkButton(
            row,
            text="↵",
            width=44,
            height=44,
            font=(T.FONT_FAMILY, 16),
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_PRIMARY,
            corner_radius=8,
            command=self._submit,
        )
        submit_btn.pack(side="left", padx=(6, 0))

        self._hint_label = ctk.CTkLabel(
            self,
            text="Enter to submit  ·  Esc to clear",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._hint_label.pack(fill="x", pady=(3, 0))

        self._entry.bind("<Return>", self._submit)
        self._entry.bind("<Escape>", self._escape)
        self._entry.bind("<FocusIn>", self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)

        self._start_cycling()

    # ── event handlers ────────────────────────────────────────────────────────

    def _submit(self, _event=None) -> None:
        text = self._entry.get().strip()
        if text:
            self._on_submit(text)
        self._entry.delete(0, "end")
        self._hint_index = 0
        self._start_cycling()

    def _escape(self, _event=None) -> None:
        text = self._entry.get()
        if text:
            self._entry.delete(0, "end")
        else:
            self._entry.tk_focusNext().focus()

    def _on_focus_in(self, _event=None) -> None:
        self._stop_cycling()
        self._hint_label.configure(text="Enter to submit  ·  Esc to clear")

    def _on_focus_out(self, _event=None) -> None:
        if not self._entry.get():
            self._start_cycling()

    # ── hint cycling ──────────────────────────────────────────────────────────

    def _start_cycling(self) -> None:
        self._stop_cycling()
        self._cycle_job = self.after(self._CYCLE_MS, self._cycle_hint)

    def _stop_cycling(self) -> None:
        if self._cycle_job:
            self.after_cancel(self._cycle_job)
            self._cycle_job = None

    def _cycle_hint(self) -> None:
        self._hint_index = (self._hint_index + 1) % len(_HINTS)
        hint = _HINTS[self._hint_index]
        try:
            self._entry.configure(placeholder_text=hint)
        except Exception:
            pass
        self._cycle_job = self.after(self._CYCLE_MS, self._cycle_hint)

    # ── public API ────────────────────────────────────────────────────────────

    def focus(self) -> None:
        self._entry.focus_set()
