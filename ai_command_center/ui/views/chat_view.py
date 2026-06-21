"""Chat view — modern mobile-style messaging UI, strictly isolated to conversation display."""
from __future__ import annotations

import time
from typing import Callable

import customtkinter as ctk

from ai_command_center.ui.markdown_plain import format_assistant_markdown
from ai_command_center.ui.theme import tokens as T

# ── Layout constants ───────────────────────────────────────────────────────────
_BUBBLE_RADIUS  = 18
_BUBBLE_WRAP    = 540   # wraplength for label text (px)
_BUBBLE_TBX_W   = 560   # textbox width for assistant bubble (px)
_BUBBLE_MAX_PAD = 80    # minimum spacer that pushes bubbles away from the far side
_SIDE_PAD       = 12    # outer horizontal padding on message rows


def _hhmm() -> str:
    return time.strftime("%H:%M")


# ─────────────────────────────────────────────────────────────────────────────
#  Copy micro-button  (shared by both bubble types)
# ─────────────────────────────────────────────────────────────────────────────

class _CopyBtn(ctk.CTkButton):
    """Tiny clipboard button — flashes ✓ for 1.5 s then resets."""

    def __init__(self, master, get_text: Callable[[], str]) -> None:
        super().__init__(
            master,
            text="⎘",
            width=24,
            height=20,
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


# ─────────────────────────────────────────────────────────────────────────────
#  User bubble  (right-aligned, accent colour)
# ─────────────────────────────────────────────────────────────────────────────

class _UserBubble(ctk.CTkFrame):
    """Solid accent-colour pill, right side.  Timestamp + copy sit below it."""

    def __init__(self, master, text: str) -> None:
        super().__init__(
            master,
            fg_color=T.ACCENT_DEFAULT,
            corner_radius=_BUBBLE_RADIUS,
            border_width=0,
        )
        self._text = text
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
#  Assistant bubble  (left-aligned, soft surface colour, streaming-aware)
# ─────────────────────────────────────────────────────────────────────────────

class _AssistantBubble(ctk.CTkFrame):
    """Soft surface pill, left side — streams text in, auto-sizes."""

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

    def append_raw(self, chunk: str) -> None:
        self._raw += chunk
        self._set(self._raw)

    def finalize(self, full_text: str) -> None:
        self._raw = full_text
        self._set(format_assistant_markdown(full_text))


# ─────────────────────────────────────────────────────────────────────────────
#  System strip  (errors, tool results, cancellations — not a chat bubble)
# ─────────────────────────────────────────────────────────────────────────────

class _SystemStrip(ctk.CTkFrame):
    _PALETTE: dict[str, tuple[str, str]] = {
        "error":     ("#3A1010", T.STATUS_ERROR),
        "tool":      ("#0F2010", T.STATUS_READY),
        "cancelled": ("#1E1E10", T.TEXT_MUTED),
        "system":    ("transparent", T.TEXT_MUTED),
    }
    _DOT = {"error": "✕", "tool": "✓", "cancelled": "◼", "system": "ℹ"}

    def __init__(self, master, kind: str, label: str, body: str) -> None:
        bg, fg = self._PALETTE.get(kind, self._PALETTE["system"])
        super().__init__(master, fg_color=bg, corner_radius=8, border_width=0)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=7)
        dot = self._DOT.get(kind, "·")
        ctk.CTkLabel(
            hdr,
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
    """Pill-shaped input bar: attachment icon · text field · round send/stop button."""

    def __init__(
        self,
        master,
        on_send: Callable[[str], None] | None,
        on_stop: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0)
        self._on_send   = on_send
        self._on_stop   = on_stop
        self._streaming = False

        pill = ctk.CTkFrame(
            self,
            fg_color=T.BG_GLASS,
            corner_radius=28,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
        )
        pill.pack(fill="x", padx=16, pady=10)

        # Attachment / plugin icon
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

        # Text entry
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

        # Send / Stop round button
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

        # Status micro-label (right of pill)
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
            self._status_lbl.configure(text="")

    def set_status(self, text: str, color: str = "") -> None:
        self._status_lbl.configure(text=text, text_color=color or T.TEXT_MUTED)

    def focus_input(self) -> None:
        self._entry.focus_set()


# ─────────────────────────────────────────────────────────────────────────────
#  ChatView  (public)
# ─────────────────────────────────────────────────────────────────────────────

class ChatView(ctk.CTkFrame):
    """Consumer-facing streaming chat.

    Architecture contract
    ─────────────────────
    • Data arrives only via the public methods listed below, called from
      UIQueue on the main thread.
    • No EventBus, service, or backend imports.
    • No developer logs, pipeline paths, or system telemetry on screen.

    Callbacks (on_cancel required; rest optional)
    ─────────────────────────────────────────────
    on_cancel(request_id)   — stop streaming
    on_export(history)      — list[dict] export
    on_regenerate()         — re-run last prompt
    on_send(text)           — submit text from the inline input pill
    """

    def __init__(
        self,
        master,
        on_cancel:     Callable,
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

        self._request_id:        str | None              = None
        self._streaming:         bool                    = False
        self._streaming_bubble:  _AssistantBubble | None = None
        self._chunk_buffer:      str                     = ""
        self._flush_pending:     bool                    = False
        self._history:           list[dict]              = []

        self._build()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True)
        self._scroll.columnconfigure(0, weight=1)

        self._pill = _InputPill(
            self,
            on_send=self._on_send,
            on_stop=self._handle_stop,
        )
        self._pill.pack(fill="x", side="bottom")

    # ── row helpers  (right = user, left = assistant) ──────────────────────────

    def _user_row(self, text: str) -> None:
        """Right-aligned user bubble + [copy ⎘] [HH:MM] metadata below."""
        outer = ctk.CTkFrame(self._scroll, fg_color="transparent")
        outer.pack(fill="x", padx=_SIDE_PAD, pady=(0, 2))

        # Bubble row
        brow = ctk.CTkFrame(outer, fg_color="transparent")
        brow.pack(fill="x")
        ctk.CTkFrame(brow, fg_color="transparent").pack(
            side="left", fill="x", expand=True
        )
        bubble = _UserBubble(brow, text)
        bubble.pack(side="right", anchor="e")

        # Metadata row (right-aligned: copy · timestamp)
        mrow = ctk.CTkFrame(outer, fg_color="transparent")
        mrow.pack(fill="x", pady=(2, 6))
        ctk.CTkFrame(mrow, fg_color="transparent").pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            mrow,
            text=_hhmm(),
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
        ).pack(side="right", padx=(0, 4))
        _CopyBtn(mrow, lambda t=text: t).pack(side="right")

    def _assistant_row(self) -> _AssistantBubble:
        """Left-aligned assistant bubble; returns bubble for streaming.
        Metadata (copy + timestamp) appended when finalized."""
        outer = ctk.CTkFrame(self._scroll, fg_color="transparent")
        outer.pack(fill="x", padx=_SIDE_PAD, pady=(0, 2))
        outer._meta_pending = True  # type: ignore[attr-defined]
        outer._ts            = _hhmm()  # type: ignore[attr-defined]

        brow = ctk.CTkFrame(outer, fg_color="transparent")
        brow.pack(fill="x")
        bubble = _AssistantBubble(brow)
        bubble.pack(side="left", anchor="w")
        ctk.CTkFrame(brow, fg_color="transparent").pack(
            side="right", fill="x", expand=True
        )

        # Keep reference so we can add metadata after finalize()
        self._last_assistant_outer = outer
        return bubble

    def _finalize_assistant_meta(self, bubble: _AssistantBubble) -> None:
        """Attach copy + timestamp metadata row after streaming completes."""
        outer = getattr(self, "_last_assistant_outer", None)
        if outer is None:
            return
        mrow = ctk.CTkFrame(outer, fg_color="transparent")
        mrow.pack(fill="x", pady=(2, 6))
        _CopyBtn(mrow, lambda: bubble._raw).pack(side="left")
        ctk.CTkLabel(
            mrow,
            text=getattr(outer, "_ts", _hhmm()),
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
        ).pack(side="left", padx=(4, 0))
        self._last_assistant_outer = None

    # ── public API ─────────────────────────────────────────────────────────────

    def load_history(self, messages: list[dict]) -> None:
        """Populate from a saved conversation."""
        self._clear()
        self._history = list(messages)
        for item in messages:
            role    = str(item.get("role", ""))
            content = str(item.get("content", ""))
            if role == "user":
                self._user_row(content)
            elif role == "assistant":
                bubble = self._assistant_row()
                bubble.finalize(content)
                self._finalize_assistant_meta(bubble)
        self._scroll_to_bottom()

    def show_user_message(self, text: str) -> None:
        self._history.append({"role": "user", "content": text})
        self._user_row(text)
        self._scroll_to_bottom()

    def begin_assistant(self, request_id: str) -> None:
        self._request_id   = request_id
        self._streaming    = True
        self._chunk_buffer = ""
        self._streaming_bubble = self._assistant_row()
        self._pill.set_streaming(True)
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
            self._finalize_assistant_meta(self._streaming_bubble)
        self._history.append({"role": "assistant", "content": text})
        self._end_stream()
        self._scroll_to_bottom()

    def show_cancelled(self) -> None:
        self._flush_pending = False
        self._chunk_buffer  = ""
        if self._streaming_bubble:
            self._streaming_bubble.finalize(self._streaming_bubble._raw or "…")
            self._finalize_assistant_meta(self._streaming_bubble)
        self._add_strip("cancelled", "Stopped", "Generation was cancelled.")
        self._end_stream()
        self._scroll_to_bottom()

    def show_error(self, message: str) -> None:
        self._flush_pending = False
        self._chunk_buffer  = ""
        if self._streaming_bubble:
            self._streaming_bubble.pack_forget()
            self._streaming_bubble = None
        self._add_strip("error", "Error", message)
        self._end_stream(error=True)
        self._scroll_to_bottom()

    def show_tool_output(self, tool: str, output: str, *, success: bool = True) -> None:
        kind  = "tool" if success else "error"
        label = f"Tool: {tool}"
        self._add_strip(kind, label, output)
        self._scroll_to_bottom()

    def show_system_message(self, message: str) -> None:
        self._add_strip("system", "", message)
        self._scroll_to_bottom()

    # ── internal ──────────────────────────────────────────────────────────────

    def _flush_chunks(self) -> None:
        self._flush_pending = False
        if self._chunk_buffer and self._streaming_bubble:
            self._streaming_bubble.append_raw(self._chunk_buffer)
            self._chunk_buffer = ""
            self._scroll_to_bottom()

    def _add_strip(self, kind: str, label: str, body: str) -> None:
        _SystemStrip(self._scroll, kind, label, body).pack(
            fill="x", padx=_SIDE_PAD + 4, pady=(0, 4)
        )

    def _clear(self) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()
        self._streaming_bubble         = None
        self._streaming                = False
        self._history                  = []
        self._last_assistant_outer     = None  # type: ignore[assignment]

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
