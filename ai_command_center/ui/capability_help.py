"""Command capability cheat sheet (capability_completion sprint)."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

_HELP_TEXT = """Commands (type in the box at top)

Chat
  Ask anything in plain language

Shell
  > echo hello
  (or start with echo, dir, cd, type, ls — prefix added automatically)

Notes (requires vault path in Settings)
  note: keyword
  new note: title | body text

Memory
  remember: label | content
  memory: keyword

Navigate
  go settings   — or just: settings
  go chat       — or just: chat
  go notes

Clipboard
  Copy text first, then:
  Summarize this clipboard

Help
  ? or help

Tips
  • Set Obsidian vault path in Settings → Save
  • Shell commands need > or a shell verb (echo, dir, …)
  • Answers are local via Ollama — no web search
"""


def show_capability_help(parent: ctk.CTk) -> None:
    dialog = ctk.CTkToplevel(parent)
    dialog.title("Command help")
    dialog.geometry("520x480")
    dialog.configure(fg_color=T.BG_DEEP)
    dialog.transient(parent)
    dialog.grab_set()

    ctk.CTkLabel(
        dialog,
        text="AI Command Center",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=T.TEXT_PRIMARY,
    ).pack(anchor="w", padx=16, pady=(16, 8))

    box = ctk.CTkTextbox(
        dialog,
        font=T.FONT_SMALL,
        fg_color=T.BG_GLASS,
        text_color=T.TEXT_SECONDARY,
        wrap="word",
    )
    box.pack(fill="both", expand=True, padx=16, pady=(0, 8))
    box.insert("1.0", _HELP_TEXT)
    box.configure(state="disabled")

    ctk.CTkButton(dialog, text="Close", width=100, command=dialog.destroy).pack(
        anchor="e", padx=16, pady=(0, 16)
    )

    dialog.focus_set()
