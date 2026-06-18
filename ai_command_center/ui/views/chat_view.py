"""Minimal streaming chat view — Phase 3B (full markdown in Phase 3D)."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.markdown_plain import format_assistant_markdown
from ai_command_center.ui.theme import tokens as T


class ChatView(ctk.CTkFrame):
    def __init__(self, master, on_cancel, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_cancel = on_cancel
        self._request_id: str | None = None
        self._streaming = False
        self._assistant_start: str | None = None

        card = GlassCard(self)
        card.pack(fill="both", expand=True, padx=T.PAD, pady=T.PAD)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        ctk.CTkLabel(
            header,
            text="Chat",
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")

        self._status = ctk.CTkLabel(
            header,
            text="Idle",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        )
        self._status.pack(side="left", padx=(12, 0))

        self._cancel_btn = ctk.CTkButton(
            header,
            text="Cancel",
            width=80,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            hover_color=T.STATUS_ERROR,
            state="disabled",
            command=self._handle_cancel,
        )
        self._cancel_btn.pack(side="right")

        self._text = ctk.CTkTextbox(
            card,
            font=T.FONT_BODY,
            fg_color=T.BG_DEEP,
            text_color=T.TEXT_PRIMARY,
            wrap="word",
            activate_scrollbars=True,
        )
        self._text.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        self._text.configure(state="disabled")

    def load_history(self, messages: list[dict]) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        for item in messages:
            role = str(item.get("role", ""))
            content = str(item.get("content", ""))
            if role == "assistant":
                content = format_assistant_markdown(content)
                self._text.insert("end", f"Assistant\n{content}\n\n")
            elif role == "user":
                self._text.insert("end", f"You\n{content}\n\n")
        self._text.see("end")
        self._text.configure(state="disabled")
        if messages:
            self._status.configure(text="History loaded", text_color=T.TEXT_MUTED)

    def _handle_cancel(self) -> None:
        if self._request_id:
            self._on_cancel(self._request_id)

    def show_user_message(self, text: str) -> None:
        self._append_block(f"You\n{text}\n\n")

    def begin_assistant(self, request_id: str) -> None:
        self._request_id = request_id
        self._streaming = True
        self._assistant_start = self._text.index("end-1c")
        self._append_block("Assistant\n")
        self._status.configure(text="Streaming…", text_color=T.STATUS_BUSY)
        self._cancel_btn.configure(state="normal")

    def append_chunk(self, text: str) -> None:
        if not self._streaming:
            return
        self._append_inline(text)

    def finish_assistant(self, text: str) -> None:
        display = format_assistant_markdown(text)
        if self._streaming and self._assistant_start:
            self._replace_from(self._assistant_start, f"Assistant\n{display}\n\n")
        else:
            self._append_block(f"Assistant\n{display}\n\n")
        self._end_stream("Complete")

    def show_cancelled(self) -> None:
        self._append_inline("\n[cancelled]\n\n")
        self._end_stream("Cancelled")

    def show_error(self, message: str) -> None:
        self._append_block(f"Error\n{message}\n\n")
        self._end_stream("Error", error=True)

    def show_tool_output(self, tool: str, output: str, *, success: bool = True) -> None:
        label = "Tool" if success else "Tool error"
        self._append_block(f"{label} ({tool})\n{output}\n\n")
        color = T.TEXT_MUTED if success else T.STATUS_ERROR
        self._status.configure(text="Tool complete" if success else "Tool failed", text_color=color)

    def show_system_message(self, message: str) -> None:
        self._append_block(f"System\n{message}\n\n")
        self._status.configure(text="Ready", text_color=T.TEXT_MUTED)

    def _end_stream(self, label: str, *, error: bool = False) -> None:
        self._streaming = False
        self._request_id = None
        self._assistant_start = None
        color = T.STATUS_ERROR if error else T.TEXT_MUTED
        self._status.configure(text=label, text_color=color)
        self._cancel_btn.configure(state="disabled")

    def _append_block(self, text: str) -> None:
        self._text.configure(state="normal")
        self._text.insert("end", text)
        self._text.see("end")
        self._text.configure(state="disabled")

    def _append_inline(self, text: str) -> None:
        self._text.configure(state="normal")
        self._text.insert("end", text)
        self._text.see("end")
        self._text.configure(state="disabled")

    def _replace_from(self, start_index: str, text: str) -> None:
        self._text.configure(state="normal")
        self._text.delete(start_index, "end")
        self._text.insert(start_index, text)
        self._text.see("end")
        self._text.configure(state="disabled")
