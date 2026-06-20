"""Streaming chat view — message bubbles, batching, copy, timestamps, export."""
from __future__ import annotations

import time
from typing import Callable

import customtkinter as ctk

from ai_command_center.ui.markdown_plain import format_assistant_markdown
from ai_command_center.ui.theme import tokens as T


# ──────────────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _now_hhmm() -> str:
    return time.strftime("%H:%M")


def _approx_tokens(text: str) -> int:
    return max(1, len(text.split()))


# ──────────────────────────────────────────────────────────────────────────────
#  Role label
# ──────────────────────────────────────────────────────────────────────────────

class _RoleLabel(ctk.CTkFrame):
    def __init__(self, master, role: str, color: str) -> None:
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(
            self, text=role, font=T.FONT_ROLE, text_color=color
        ).pack(side="left")


# ──────────────────────────────────────────────────────────────────────────────
#  Copy button (reusable)
# ──────────────────────────────────────────────────────────────────────────────

class _CopyBtn(ctk.CTkButton):
    """Small copy-to-clipboard button — flashes ✓ on success."""

    def __init__(self, master, get_text: Callable[[], str]) -> None:
        super().__init__(
            master,
            text="⎘",
            width=26,
            height=22,
            font=(T.FONT_FAMILY, 11),
            fg_color="transparent",
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=4,
            command=self._copy,
        )
        self._get_text = get_text

    def _copy(self) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(self._get_text())
            self.configure(text="✓", text_color=T.STATUS_READY)
            self.after(1500, lambda: self.configure(text="⎘", text_color=T.TEXT_MUTED))
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
#  Message bubbles
# ──────────────────────────────────────────────────────────────────────────────

class UserBubble(ctk.CTkFrame):
    """User message — blue-tinted, full-width, with copy button."""

    def __init__(self, master, text: str) -> None:
        super().__init__(
            master,
            fg_color=T.MSG_USER_BG,
            border_color=T.MSG_USER_BORDER,
            border_width=1,
            corner_radius=8,
        )
        self._text = text

        # Header row: role + copy + timestamp
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8, 0))
        _RoleLabel(hdr, "YOU", T.ACCENT_DEFAULT).pack(side="left")
        ctk.CTkLabel(
            hdr,
            text=_now_hhmm(),
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
        ).pack(side="right", padx=(0, 2))
        _CopyBtn(hdr, lambda: self._text).pack(side="right", padx=(0, 4))

        ctk.CTkLabel(
            self,
            text=text,
            font=T.FONT_BODY,
            text_color=T.MSG_USER_TEXT,
            wraplength=680,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=10, pady=(2, 10))


class AssistantBubble(ctk.CTkFrame):
    """Assistant message — streaming + markdown, copy, token count, regenerate."""

    def __init__(self, master, on_regenerate: Callable[[], None] | None = None) -> None:
        super().__init__(
            master,
            fg_color=T.MSG_ASSISTANT_BG,
            border_color=T.MSG_ASSISTANT_BORDER,
            border_width=1,
            corner_radius=8,
        )
        self._raw           = ""
        self._on_regenerate = on_regenerate

        # Header row
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8, 0))
        _RoleLabel(hdr, "ASSISTANT", T.TEXT_SECONDARY).pack(side="left")
        self._ts_lbl = ctk.CTkLabel(
            hdr,
            text=_now_hhmm(),
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
        )
        self._ts_lbl.pack(side="right", padx=(0, 2))
        _CopyBtn(hdr, lambda: self._raw).pack(side="right", padx=(0, 4))

        # Textbox
        self._textbox = ctk.CTkTextbox(
            self,
            font=T.FONT_BODY,
            fg_color="transparent",
            text_color=T.MSG_ASSISTANT_TEXT,
            wrap="word",
            activate_scrollbars=False,
            height=80,
        )
        self._textbox.pack(fill="x", padx=6, pady=(2, 0))
        self._textbox.configure(state="disabled")

        # Footer row: token count + regenerate
        self._footer = ctk.CTkFrame(self, fg_color="transparent")
        self._footer.pack(fill="x", padx=10, pady=(2, 6))

        self._token_lbl = ctk.CTkLabel(
            self._footer,
            text="",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._token_lbl.pack(side="left")

        if on_regenerate:
            ctk.CTkButton(
                self._footer,
                text="↺ Regenerate",
                width=90,
                height=22,
                font=(T.FONT_FAMILY, 10),
                fg_color="transparent",
                hover_color=T.BG_GLASS_BORDER,
                text_color=T.TEXT_MUTED,
                corner_radius=4,
                command=on_regenerate,
            ).pack(side="right")

        self._set_text("●   ●   ●")

    def _set_text(self, text: str) -> None:
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.insert("1.0", text)
        self._textbox.configure(state="disabled")
        self._auto_height()

    def _auto_height(self) -> None:
        lines = int(self._textbox.index("end-1c").split(".")[0])
        h = max(40, min(lines * 20 + 24, 500))
        self._textbox.configure(height=h)

    def append_raw(self, chunk: str) -> None:
        self._raw += chunk
        self._set_text(self._raw)

    def finalize(self, full_text: str) -> None:
        self._raw = full_text
        formatted = format_assistant_markdown(full_text)
        self._set_text(formatted)
        tokens = _approx_tokens(full_text)
        self._token_lbl.configure(text=f"~{tokens} tokens")


class SystemBubble(ctk.CTkFrame):
    """System / memory / tool / error notification strip."""

    KIND_COLORS = {
        "system":    (T.MSG_SYSTEM_BG,  "#444444",             T.MSG_SYSTEM_TEXT,    "SYSTEM"),
        "error":     (T.MSG_ERROR_BG,   T.MSG_ERROR_BORDER,    T.MSG_ERROR_TEXT,     "ERROR"),
        "tool":      (T.MSG_TOOL_BG,    T.MSG_TOOL_BORDER,     T.MSG_TOOL_TEXT,      "TOOL"),
        "cancelled": (T.MSG_SYSTEM_BG,  "#333333",             T.MSG_CANCELLED_TEXT, "CANCELLED"),
    }

    def __init__(self, master, kind: str, label: str, text: str) -> None:
        colors = self.KIND_COLORS.get(kind, self.KIND_COLORS["system"])
        bg, border, fg, default_label = colors
        super().__init__(
            master,
            fg_color=bg,
            border_color=border,
            border_width=1,
            corner_radius=6,
        )
        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(
            header_row,
            text=label or default_label,
            font=T.FONT_ROLE,
            text_color=fg,
        ).pack(side="left")

        if text:
            ctk.CTkLabel(
                self,
                text=text,
                font=T.FONT_SMALL,
                text_color=fg,
                wraplength=660,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=10, pady=(2, 8))


# ──────────────────────────────────────────────────────────────────────────────
#  Chat view
# ──────────────────────────────────────────────────────────────────────────────

class ChatView(ctk.CTkFrame):
    """Single-session streaming chat.

    Architecture contract:
      - Receives data only via public methods called from UIQueue (main thread).
      - No EventBus or service imports.
      - on_cancel: called when Stop is clicked.
      - on_export: called with list[dict] of {role, content} when Export clicked.
      - on_regenerate: called when ↺ Regenerate is clicked on last bubble.
    """

    def __init__(
        self,
        master,
        on_cancel,
        on_export: Callable[[list[dict]], None] | None = None,
        on_regenerate: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_cancel      = on_cancel
        self._on_export      = on_export
        self._on_regenerate  = on_regenerate
        self._request_id: str | None = None
        self._streaming      = False
        self._streaming_bubble: AssistantBubble | None = None
        self._chunk_buffer   = ""
        self._flush_pending  = False
        self._history: list[dict] = []
        self._total_tokens   = 0

        self._build_header()
        self._build_messages()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_header(self) -> None:
        header = ctk.CTkFrame(
            self, fg_color=T.BG_PANEL, corner_radius=0, height=44
        )
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="Chat", font=T.FONT_HEADER, text_color=T.TEXT_PRIMARY
        ).pack(side="left", padx=T.PAD, pady=10)

        self._status = ctk.CTkLabel(
            header, text="Idle", font=T.FONT_SMALL, text_color=T.TEXT_MUTED
        )
        self._status.pack(side="left", pady=10)

        self._cancel_btn = ctk.CTkButton(
            header,
            text="■ Stop",
            width=80,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            hover_color=T.STATUS_ERROR,
            text_color=T.STATUS_ERROR,
            state="disabled",
            command=self._handle_cancel,
        )
        self._cancel_btn.pack(side="right", padx=(4, T.PAD), pady=8)

        if self._on_export:
            ctk.CTkButton(
                header,
                text="⬇ Export",
                width=80,
                height=28,
                font=T.FONT_SMALL,
                fg_color=T.BG_GLASS,
                hover_color=T.BG_GLASS_BORDER,
                text_color=T.TEXT_SECONDARY,
                corner_radius=6,
                command=self._handle_export,
            ).pack(side="right", padx=4, pady=8)

        self._token_counter = ctk.CTkLabel(
            header,
            text="",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
        )
        self._token_counter.pack(side="right", padx=8)

    def _build_messages(self) -> None:
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True)
        self._scroll.columnconfigure(0, weight=1)

    # ── public API ─────────────────────────────────────────────────────────────

    def load_history(self, messages: list[dict]) -> None:
        self._clear()
        self._history = list(messages)
        for item in messages:
            role    = str(item.get("role", ""))
            content = str(item.get("content", ""))
            if role == "user":
                self._add_user(content)
            elif role == "assistant":
                b = AssistantBubble(self._scroll, on_regenerate=self._on_regenerate)
                b.pack(fill="x", padx=T.PAD, pady=(0, 8))
                b.finalize(content)
        self._scroll_to_bottom()
        self._status.configure(
            text=f"{len(messages)} messages", text_color=T.TEXT_MUTED
        )

    def show_user_message(self, text: str) -> None:
        self._history.append({"role": "user", "content": text})
        self._add_user(text)
        self._scroll_to_bottom()

    def begin_assistant(self, request_id: str) -> None:
        self._request_id     = request_id
        self._streaming      = True
        self._chunk_buffer   = ""
        self._streaming_bubble = AssistantBubble(
            self._scroll, on_regenerate=self._on_regenerate
        )
        self._streaming_bubble.pack(fill="x", padx=T.PAD, pady=(0, 8))
        self._status.configure(text="Streaming…", text_color=T.STATUS_BUSY)
        self._cancel_btn.configure(state="normal")
        self._scroll_to_bottom()

    def append_chunk(self, text: str) -> None:
        if not self._streaming:
            return
        self._chunk_buffer += text
        if not self._flush_pending:
            self._flush_pending = True
            self.after(T.CHUNK_FLUSH_MS, self._flush_chunks)

    def finish_assistant(self, text: str) -> None:
        self._flush_pending = False
        self._chunk_buffer  = ""
        if self._streaming_bubble:
            self._streaming_bubble.finalize(text)
        self._history.append({"role": "assistant", "content": text})
        tokens = _approx_tokens(text)
        self._total_tokens += tokens
        self._token_counter.configure(
            text=f"~{self._total_tokens} tokens total"
        )
        self._end_stream("Ready")
        self._scroll_to_bottom()

    def show_cancelled(self) -> None:
        self._flush_pending = False
        self._chunk_buffer  = ""
        if self._streaming_bubble:
            current = self._streaming_bubble._raw or "…"
            self._streaming_bubble.finalize(current)
        self._add_system("cancelled", "", "[Generation stopped]")
        self._end_stream("Cancelled")
        self._scroll_to_bottom()

    def show_error(self, message: str) -> None:
        self._flush_pending = False
        self._chunk_buffer  = ""
        if self._streaming_bubble:
            self._streaming_bubble.pack_forget()
            self._streaming_bubble = None
        self._add_system("error", "ERROR", message)
        self._end_stream("Error", error=True)
        self._scroll_to_bottom()

    def show_tool_output(self, tool: str, output: str, *, success: bool = True) -> None:
        kind  = "tool" if success else "error"
        label = f"TOOL › {tool}" if success else f"TOOL ERROR › {tool}"
        self._add_system(kind, label, output)
        self._scroll_to_bottom()
        color = T.MSG_TOOL_TEXT if success else T.MSG_ERROR_TEXT
        self._status.configure(
            text="Tool complete" if success else "Tool failed",
            text_color=color,
        )

    def show_system_message(self, message: str) -> None:
        self._add_system("system", "SYSTEM", message)
        self._scroll_to_bottom()
        self._status.configure(text="Ready", text_color=T.TEXT_MUTED)

    # ── internal helpers ───────────────────────────────────────────────────────

    def _flush_chunks(self) -> None:
        self._flush_pending = False
        if self._chunk_buffer and self._streaming_bubble:
            self._streaming_bubble.append_raw(self._chunk_buffer)
            self._chunk_buffer = ""
            self._scroll_to_bottom()

    def _add_user(self, text: str) -> None:
        UserBubble(self._scroll, text).pack(fill="x", padx=T.PAD, pady=(0, 8))

    def _add_system(self, kind: str, label: str, text: str) -> None:
        SystemBubble(self._scroll, kind, label, text).pack(
            fill="x", padx=T.PAD, pady=(0, 4)
        )

    def _clear(self) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()
        self._streaming_bubble = None
        self._streaming        = False
        self._history          = []
        self._total_tokens     = 0
        self._token_counter.configure(text="")

    def _handle_cancel(self) -> None:
        if self._request_id:
            self._on_cancel(self._request_id)

    def _handle_export(self) -> None:
        if self._on_export:
            self._on_export(list(self._history))

    def _end_stream(self, label: str, *, error: bool = False) -> None:
        self._streaming        = False
        self._request_id       = None
        self._streaming_bubble = None
        color = T.STATUS_ERROR if error else T.TEXT_MUTED
        self._status.configure(text=label, text_color=color)
        self._cancel_btn.configure(state="disabled")

    def _scroll_to_bottom(self) -> None:
        self.after(10, lambda: self._scroll._parent_canvas.yview_moveto(1.0))
