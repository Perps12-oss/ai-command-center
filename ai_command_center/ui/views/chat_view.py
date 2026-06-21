"""Chat view — mobile-style messaging UI, strictly isolated to conversation display."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ai_command_center.ui.markdown_plain import format_assistant_markdown
from ai_command_center.ui.theme import tokens as T

# ── Layout constants ───────────────────────────────────────────────────────────
_BUBBLE_RADIUS  = 18
_BUBBLE_WRAP    = 560   # wraplength for label text (px)
_BUBBLE_TBX_W   = 580   # textbox width for assistant bubble (px)
_BUBBLE_MAX_PAD = 80    # horizontal spacer that pushes bubbles left/right
_SIDE_PAD       = 12    # outer horizontal padding on each message row


# ─────────────────────────────────────────────────────────────────────────────
#  User bubble  (right-aligned, accent colour)
# ─────────────────────────────────────────────────────────────────────────────

class _UserBubble(ctk.CTkFrame):
    """Solid accent-colour pill — right side of the conversation."""

    def __init__(self, master, text: str) -> None:
        super().__init__(
            master,
            fg_color=T.ACCENT_DEFAULT,
            corner_radius=_BUBBLE_RADIUS,
            border_width=0,
        )
        ctk.CTkLabel(
            self,
            text=text,
            font=T.FONT_BODY,
            text_color="#FFFFFF",
            wraplength=_BUBBLE_WRAP,
            justify="left",
            anchor="w",
        ).pack(padx=18, pady=12)


# ─────────────────────────────────────────────────────────────────────────────
#  Assistant bubble  (left-aligned, soft surface colour, supports streaming)
# ─────────────────────────────────────────────────────────────────────────────

class _AssistantBubble(ctk.CTkFrame):
    """Soft surface pill — left side, streams text in, auto-sizes."""

    def __init__(self, master) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            corner_radius=_BUBBLE_RADIUS,
            border_width=0,
        )
        self._raw = ""

        self._textbox = ctk.CTkTextbox(
            self,
            font=T.FONT_BODY,
            fg_color="transparent",
            text_color=T.TEXT_PRIMARY,
            wrap="word",
            activate_scrollbars=False,
            width=_BUBBLE_TBX_W,
            height=44,
        )
        self._textbox.pack(padx=14, pady=12)
        self._textbox.configure(state="disabled")
        self._set("●  ●  ●")

    # ── internal ───────────────────────────────────────────────────────────────

    def _set(self, text: str) -> None:
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.insert("1.0", text)
        self._textbox.configure(state="disabled")
        self._resize()

    def _resize(self) -> None:
        lines = int(self._textbox.index("end-1c").split(".")[0])
        h = max(40, min(lines * 20 + 20, 500))
        self._textbox.configure(height=h)

    # ── public ─────────────────────────────────────────────────────────────────

    def append_raw(self, chunk: str) -> None:
        self._raw += chunk
        self._set(self._raw)

    def finalize(self, full_text: str) -> None:
        self._raw = full_text
        self._set(format_assistant_markdown(full_text))


# ─────────────────────────────────────────────────────────────────────────────
#  System strip  (thin notice bar — errors, tool results, cancelled)
# ─────────────────────────────────────────────────────────────────────────────

class _SystemStrip(ctk.CTkFrame):
    """Minimal inline notice — not a chat bubble, never shows developer paths."""

    _PALETTE: dict[str, tuple[str, str]] = {
        "error":     ("#3A1010", T.STATUS_ERROR),
        "tool":      ("#0F2010", T.STATUS_READY),
        "cancelled": ("#1E1E10", T.TEXT_MUTED),
        "system":    ("transparent", T.TEXT_MUTED),
    }

    def __init__(self, master, kind: str, label: str, body: str) -> None:
        bg, fg = self._PALETTE.get(kind, self._PALETTE["system"])
        super().__init__(master, fg_color=bg, corner_radius=8, border_width=0)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=7)

        dot = {"error": "✕", "tool": "✓", "cancelled": "◼", "system": "ℹ"}.get(kind, "·")
        ctk.CTkLabel(
            inner,
            text=f"{dot}  {label or kind.upper()}",
            font=(T.FONT_FAMILY, 11, "bold"),
            text_color=fg,
            anchor="w",
        ).pack(side="left")

        if body:
            ctk.CTkLabel(
                self,
                text=body,
                font=T.FONT_SMALL,
                text_color=fg,
                wraplength=660,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=14, pady=(0, 7))


# ─────────────────────────────────────────────────────────────────────────────
#  Input pill  (modern mobile-style bar at the bottom of the view)
# ─────────────────────────────────────────────────────────────────────────────

class _InputPill(ctk.CTkFrame):
    """Pill-shaped input bar — attachment icon · text field · send/stop button."""

    def __init__(self, master, on_send: Callable[[str], None] | None, on_stop: Callable[[], None]) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            corner_radius=0,
        )
        self._on_send = on_send
        self._on_stop = on_stop
        self._streaming = False

        # Outer pill wrapper
        pill = ctk.CTkFrame(
            self,
            fg_color=T.BG_GLASS,
            corner_radius=28,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
        )
        pill.pack(fill="x", padx=16, pady=10)

        # ── Attachment / plugin icon ───────────────────────────────────────────
        ctk.CTkButton(
            pill,
            text="⊕",
            width=36,
            height=36,
            font=(T.FONT_FAMILY, 17),
            fg_color="transparent",
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=18,
            command=lambda: None,
        ).pack(side="left", padx=(8, 0), pady=6)

        # ── Text entry ─────────────────────────────────────────────────────────
        self._entry = ctk.CTkEntry(
            pill,
            placeholder_text="Message…",
            font=T.FONT_BODY,
            fg_color="transparent",
            border_width=0,
            text_color=T.TEXT_PRIMARY,
            placeholder_text_color=T.TEXT_MUTED,
            height=36,
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=6, pady=6)
        self._entry.bind("<Return>", self._submit)

        # ── Send / Stop button ─────────────────────────────────────────────────
        self._action_btn = ctk.CTkButton(
            pill,
            text="▶",
            width=36,
            height=36,
            font=(T.FONT_FAMILY, 14, "bold"),
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=18,
            command=self._on_action,
        )
        self._action_btn.pack(side="right", padx=(0, 8), pady=6)

        # ── Status micro-label ─────────────────────────────────────────────────
        self._status_lbl = ctk.CTkLabel(
            self,
            text="",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
        )
        self._status_lbl.pack(side="right", padx=20, pady=(0, 4))

    def _submit(self, _event=None) -> None:
        text = self._entry.get().strip()
        if not text:
            return
        if self._on_send:
            self._entry.delete(0, "end")
            self._on_send(text)

    def _on_action(self) -> None:
        if self._streaming:
            self._on_stop()
        else:
            self._submit()

    def set_streaming(self, streaming: bool) -> None:
        self._streaming = streaming
        if streaming:
            self._action_btn.configure(
                text="■",
                fg_color=T.STATUS_ERROR,
                hover_color="#8B0000",
            )
            self._status_lbl.configure(text="Generating…", text_color=T.STATUS_BUSY)
        else:
            self._action_btn.configure(
                text="▶",
                fg_color=T.ACCENT_DEFAULT,
                hover_color=T.ACCENT_HOVER,
            )
            self._status_lbl.configure(text="", text_color=T.TEXT_MUTED)

    def set_status(self, text: str, color: str = "") -> None:
        self._status_lbl.configure(
            text=text,
            text_color=color or T.TEXT_MUTED,
        )

    def focus_input(self) -> None:
        self._entry.focus_set()


# ─────────────────────────────────────────────────────────────────────────────
#  ChatView  (public)
# ─────────────────────────────────────────────────────────────────────────────

class ChatView(ctk.CTkFrame):
    """Consumer-facing streaming chat.

    Architecture contract
    ─────────────────────
    • Receives data only via the public methods listed below (called from
      UIQueue on the main thread).
    • No EventBus, service, or backend imports.
    • No developer logs, token counts, pipeline paths, or system telemetry.

    Callbacks (all optional except on_cancel)
    ─────────────────────────────────────────
    on_cancel(request_id)      — stop streaming
    on_export(history)         — export conversation list[dict]
    on_regenerate()            — re-run last prompt
    on_send(text)              — submit text from the inline input pill
    """

    def __init__(
        self,
        master,
        on_cancel: Callable,
        on_export:     Callable[[list[dict]], None] | None = None,
        on_regenerate: Callable[[], None]            | None = None,
        on_send:       Callable[[str], None]         | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_cancel     = on_cancel
        self._on_export     = on_export
        self._on_regenerate = on_regenerate
        self._on_send       = on_send

        self._request_id:       str | None             = None
        self._streaming:        bool                   = False
        self._streaming_bubble: _AssistantBubble | None = None
        self._chunk_buffer:     str                    = ""
        self._flush_pending:    bool                   = False
        self._history:          list[dict]             = []

        self._build()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Message scroll area
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=T.BG_DEEP,
            corner_radius=0,
        )
        self._scroll.pack(fill="both", expand=True)
        self._scroll.columnconfigure(0, weight=1)

        # Input pill at the bottom
        self._pill = _InputPill(
            self,
            on_send=self._on_send,
            on_stop=self._handle_stop,
        )
        self._pill.pack(fill="x", side="bottom")

    # ── row helpers ───────────────────────────────────────────────────────────

    def _row_right(self) -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
        """Return (row_frame, right_slot) — bubble packs into right_slot."""
        row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        row.pack(fill="x", padx=_SIDE_PAD, pady=(0, 6))
        spacer = ctk.CTkFrame(row, fg_color="transparent", width=_BUBBLE_MAX_PAD)
        spacer.pack(side="left", fill="x", expand=True)
        slot = ctk.CTkFrame(row, fg_color="transparent")
        slot.pack(side="right")
        return row, slot

    def _row_left(self) -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
        """Return (row_frame, left_slot) — bubble packs into left_slot."""
        row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        row.pack(fill="x", padx=_SIDE_PAD, pady=(0, 6))
        slot = ctk.CTkFrame(row, fg_color="transparent")
        slot.pack(side="left")
        spacer = ctk.CTkFrame(row, fg_color="transparent", width=_BUBBLE_MAX_PAD)
        spacer.pack(side="right", fill="x", expand=True)
        return row, slot

    # ── public API ─────────────────────────────────────────────────────────────

    def load_history(self, messages: list[dict]) -> None:
        """Populate from a saved conversation list."""
        self._clear()
        self._history = list(messages)
        for item in messages:
            role    = str(item.get("role", ""))
            content = str(item.get("content", ""))
            if role == "user":
                self._add_user(content)
            elif role == "assistant":
                _, slot = self._row_left()
                bubble  = _AssistantBubble(slot)
                bubble.pack()
                bubble.finalize(content)
        self._scroll_to_bottom()

    def show_user_message(self, text: str) -> None:
        """Add a user message bubble (right-aligned)."""
        self._history.append({"role": "user", "content": text})
        self._add_user(text)
        self._scroll_to_bottom()

    def begin_assistant(self, request_id: str) -> None:
        """Start a streaming assistant response bubble."""
        self._request_id  = request_id
        self._streaming   = True
        self._chunk_buffer = ""
        _, slot = self._row_left()
        self._streaming_bubble = _AssistantBubble(slot)
        self._streaming_bubble.pack()
        self._pill.set_streaming(True)
        self._scroll_to_bottom()

    def append_chunk(self, text: str) -> None:
        """Buffer a streaming chunk; flush on next idle tick."""
        if not self._streaming:
            return
        self._chunk_buffer += text
        if not self._flush_pending:
            self._flush_pending = True
            self.after(T.CHUNK_FLUSH_MS, self._flush_chunks)

    def finish_assistant(self, text: str) -> None:
        """Finalise the streaming bubble with the complete response."""
        self._flush_pending = False
        self._chunk_buffer  = ""
        if self._streaming_bubble:
            self._streaming_bubble.finalize(text)
        self._history.append({"role": "assistant", "content": text})
        self._end_stream()
        self._scroll_to_bottom()

    def show_cancelled(self) -> None:
        """Mark the current bubble as cancelled."""
        self._flush_pending = False
        self._chunk_buffer  = ""
        if self._streaming_bubble:
            self._streaming_bubble.finalize(self._streaming_bubble._raw or "…")
        self._add_system("cancelled", "Stopped", "Generation was cancelled.")
        self._end_stream()
        self._scroll_to_bottom()

    def show_error(self, message: str) -> None:
        """Show an error strip and clear the in-progress bubble."""
        self._flush_pending = False
        self._chunk_buffer  = ""
        if self._streaming_bubble:
            self._streaming_bubble.pack_forget()
            self._streaming_bubble = None
        self._add_system("error", "Error", message)
        self._end_stream(error=True)
        self._scroll_to_bottom()

    def show_tool_output(self, tool: str, output: str, *, success: bool = True) -> None:
        """Show a tool result strip below the conversation."""
        kind  = "tool" if success else "error"
        label = f"Tool: {tool}"
        self._add_system(kind, label, output)
        self._scroll_to_bottom()

    def show_system_message(self, message: str) -> None:
        """Show a neutral system info strip."""
        self._add_system("system", "", message)
        self._scroll_to_bottom()

    # ── internal ──────────────────────────────────────────────────────────────

    def _flush_chunks(self) -> None:
        self._flush_pending = False
        if self._chunk_buffer and self._streaming_bubble:
            self._streaming_bubble.append_raw(self._chunk_buffer)
            self._chunk_buffer = ""
            self._scroll_to_bottom()

    def _add_user(self, text: str) -> None:
        _, slot = self._row_right()
        _UserBubble(slot, text).pack()

    def _add_system(self, kind: str, label: str, body: str) -> None:
        strip = _SystemStrip(self._scroll, kind, label, body)
        strip.pack(fill="x", padx=_SIDE_PAD + 4, pady=(0, 4))

    def _clear(self) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()
        self._streaming_bubble = None
        self._streaming        = False
        self._history          = []

    def _handle_stop(self) -> None:
        if self._request_id:
            self._on_cancel(self._request_id)

    def _end_stream(self, *, error: bool = False) -> None:
        self._streaming        = False
        self._request_id       = None
        self._streaming_bubble = None
        self._pill.set_streaming(False)
        if error:
            self._pill.set_status("Error — try again", T.STATUS_ERROR)
            self.after(3000, lambda: self._pill.set_status(""))

    def _scroll_to_bottom(self) -> None:
        self.after(10, lambda: self._scroll._parent_canvas.yview_moveto(1.0))
