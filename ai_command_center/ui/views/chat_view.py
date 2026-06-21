"""Chat view — modern mobile-style messaging UI, consumer-facing only."""
from __future__ import annotations

import time
from typing import Callable

import customtkinter as ctk

from ai_command_center.ui.markdown_plain import format_assistant_markdown
from ai_command_center.ui.theme import tokens as T

# ── Layout constants ───────────────────────────────────────────────────────────
_BUBBLE_RADIUS   = 18
_BUBBLE_WRAP     = 540
_BUBBLE_TBX_W    = 560
_SIDE_PAD        = 12
_PILL_MAX_LINES  = 4        # growing input: max lines before it scrolls
_LINE_H          = 22       # approximate px per line in the input textbox
_PLACEHOLDER     = "Message…"
_HINT_TEXT       = "⏎ send  ·  Shift+⏎ new line  ·  Ctrl+K commands  ·  ? shortcuts"


def _hhmm() -> str:
    return time.strftime("%H:%M")


# ─────────────────────────────────────────────────────────────────────────────
#  1. Copy micro-button
# ─────────────────────────────────────────────────────────────────────────────

class _CopyBtn(ctk.CTkButton):
    """Clipboard button — flashes ✓ for 1.5 s then resets."""

    def __init__(self, master, get_text: Callable[[], str]) -> None:
        super().__init__(
            master,
            text="⎘",
            width=26, height=20,
            font=(T.FONT_FAMILY, 11),
            fg_color="transparent",
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=4,
            command=self._copy,
        )
        self._get = get_text

    def _copy(self) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(self._get())
            self.configure(text="✓", text_color=T.STATUS_READY)
            self.after(1500, lambda: self.configure(text="⎘", text_color=T.TEXT_MUTED))
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  2. User bubble  (right-aligned)
# ─────────────────────────────────────────────────────────────────────────────

class _UserBubble(ctk.CTkFrame):
    def __init__(self, master, text: str) -> None:
        super().__init__(
            master,
            fg_color=T.ACCENT_DEFAULT,
            corner_radius=_BUBBLE_RADIUS,
            border_width=0,
        )
        self._text = text
        ctk.CTkLabel(
            self, text=text,
            font=T.FONT_BODY,
            text_color="#FFFFFF",
            wraplength=_BUBBLE_WRAP,
            justify="left", anchor="w",
        ).pack(padx=18, pady=12)


# ─────────────────────────────────────────────────────────────────────────────
#  3. Assistant bubble  (left-aligned, streaming + animated cursor)
# ─────────────────────────────────────────────────────────────────────────────

class _AssistantBubble(ctk.CTkFrame):
    """Soft surface pill — streams text in, blinks cursor while generating."""

    _BLINK_ON  = 550   # ms cursor is visible
    _BLINK_OFF = 400   # ms cursor is hidden

    def __init__(self, master) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            corner_radius=_BUBBLE_RADIUS,
            border_width=0,
        )
        self._raw       = ""
        self._live      = False   # True while streaming
        self._cur_vis   = True    # cursor currently shown?

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
        self._write("●  ●  ●")
        # Start cursor blink immediately (shows on the ellipsis)
        self._live = True
        self._blink()

    # ── internal ───────────────────────────────────────────────────────────────

    def _write(self, text: str) -> None:
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.insert("1.0", text)
        self._textbox.configure(state="disabled")
        self._resize()

    def _resize(self) -> None:
        lines = int(self._textbox.index("end-1c").split(".")[0])
        h = max(40, min(lines * 20 + 20, 500))
        self._textbox.configure(height=h)

    def _blink(self) -> None:
        if not self._live:
            return
        if self._cur_vis:
            self._write(self._raw + "▌")
        else:
            self._write(self._raw)
        self._cur_vis = not self._cur_vis
        delay = self._BLINK_ON if self._cur_vis else self._BLINK_OFF
        self.after(delay, self._blink)

    # ── public ─────────────────────────────────────────────────────────────────

    def append_raw(self, chunk: str) -> None:
        self._raw += chunk
        # cursor blink loop handles display; force immediate flush
        if self._cur_vis:
            self._write(self._raw + "▌")

    def finalize(self, full_text: str) -> None:
        self._live  = False
        self._raw   = full_text
        self._write(format_assistant_markdown(full_text))


# ─────────────────────────────────────────────────────────────────────────────
#  4. System strip  (errors, tool results, cancellations)
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
        dot = self._DOT.get(kind, "·")
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=7)
        ctk.CTkLabel(
            hdr, text=f"{dot}  {label or kind.upper()}",
            font=(T.FONT_FAMILY, 11, "bold"), text_color=fg, anchor="w",
        ).pack(side="left")
        if body:
            ctk.CTkLabel(
                self, text=body,
                font=T.FONT_SMALL, text_color=fg,
                wraplength=660, justify="left", anchor="w",
            ).pack(fill="x", padx=14, pady=(0, 7))


# ─────────────────────────────────────────────────────────────────────────────
#  5. Empty state  (shown when conversation is blank)
# ─────────────────────────────────────────────────────────────────────────────

class _EmptyState(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(
            inner, text="◇",
            font=(T.FONT_FAMILY, 48),
            text_color=T.BG_GLASS_BORDER,
        ).pack()
        ctk.CTkLabel(
            inner, text="Start a conversation",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=T.TEXT_MUTED,
        ).pack(pady=(10, 4))
        ctk.CTkLabel(
            inner,
            text="Ask anything, search your notes, run commands, or store memories.",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            wraplength=340,
            justify="center",
        ).pack()

        chips_row = ctk.CTkFrame(inner, fg_color="transparent")
        chips_row.pack(pady=(18, 0))
        for hint in ("Ask a question", "note: keyword", "remember: …", "> shell cmd"):
            ctk.CTkLabel(
                chips_row, text=hint,
                font=(T.FONT_FAMILY, 11),
                text_color=T.TEXT_MUTED,
                fg_color=T.BG_GLASS,
                corner_radius=12,
                padx=10, pady=4,
            ).pack(side="left", padx=4)


# ─────────────────────────────────────────────────────────────────────────────
#  6. Session info bar  (slim top strip: model + message count + export)
# ─────────────────────────────────────────────────────────────────────────────

class _SessionBar(ctk.CTkFrame):
    def __init__(self, master, on_export: Callable | None) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, height=38)
        self.pack_propagate(False)

        self._model_lbl = ctk.CTkLabel(
            self, text="",
            font=(T.FONT_FAMILY, 11),
            text_color=T.TEXT_MUTED,
        )
        self._model_lbl.pack(side="left", padx=14, pady=8)

        self._count_lbl = ctk.CTkLabel(
            self, text="",
            font=(T.FONT_FAMILY, 11),
            text_color=T.TEXT_MUTED,
        )
        self._count_lbl.pack(side="left", padx=(0, 8), pady=8)

        if on_export:
            ctk.CTkButton(
                self, text="⬇ Export",
                width=76, height=24,
                font=(T.FONT_FAMILY, 11),
                fg_color=T.BG_GLASS,
                hover_color=T.BG_GLASS_BORDER,
                text_color=T.TEXT_SECONDARY,
                corner_radius=6,
                command=on_export,
            ).pack(side="right", padx=10, pady=7)

    def update(self, model: str, count: int) -> None:
        self._model_lbl.configure(
            text=f"◈  {model}" if model else "",
        )
        if count > 0:
            self._count_lbl.configure(
                text=f"·  {count} message{'s' if count != 1 else ''}"
            )
        else:
            self._count_lbl.configure(text="")


# ─────────────────────────────────────────────────────────────────────────────
#  7. Input pill  (multi-line growing textbox + hint + send/stop)
# ─────────────────────────────────────────────────────────────────────────────

class _InputPill(ctk.CTkFrame):
    """Pill-shaped input: ⊕ attachment · growing text area · ▶/■ button."""

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
        self._has_focus = False

        pill = ctk.CTkFrame(
            self,
            fg_color=T.BG_GLASS,
            corner_radius=26,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
        )
        pill.pack(fill="x", padx=14, pady=(8, 2))

        # ── Attachment icon ────────────────────────────────────────────────────
        ctk.CTkButton(
            pill, text="⊕",
            width=34, height=34,
            font=(T.FONT_FAMILY, 17),
            fg_color="transparent",
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=17,
            command=lambda: None,
        ).pack(side="left", padx=(8, 0), pady=5)

        # ── Growing textbox ────────────────────────────────────────────────────
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
        # Insert placeholder
        self._placeholder_active = True
        self._tb.insert("1.0", _PLACEHOLDER)
        self._tb.configure(text_color=T.TEXT_MUTED)
        # Bindings
        self._tb.bind("<FocusIn>",    self._on_focus_in)
        self._tb.bind("<FocusOut>",   self._on_focus_out)
        self._tb.bind("<Return>",     self._on_enter)
        self._tb.bind("<KeyRelease>", self._adjust_height)

        # ── Send / Stop round button ───────────────────────────────────────────
        self._btn = ctk.CTkButton(
            pill, text="▶",
            width=34, height=34,
            font=(T.FONT_FAMILY, 13, "bold"),
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=17,
            command=self._on_action,
        )
        self._btn.pack(side="right", padx=(0, 8), pady=5)

        # ── Keyboard hint ──────────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text=_HINT_TEXT,
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
        ).pack(side="left", padx=18, pady=(0, 6))

        # ── Status micro-label ─────────────────────────────────────────────────
        self._status = ctk.CTkLabel(
            self, text="",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
        )
        self._status.pack(side="right", padx=18, pady=(0, 6))

    # ── placeholder ────────────────────────────────────────────────────────────

    def _on_focus_in(self, _event=None) -> None:
        if self._placeholder_active:
            self._tb.delete("1.0", "end")
            self._tb.configure(text_color=T.TEXT_PRIMARY)
            self._placeholder_active = False

    def _on_focus_out(self, _event=None) -> None:
        if not self._tb.get("1.0", "end-1c").strip():
            self._tb.insert("1.0", _PLACEHOLDER)
            self._tb.configure(text_color=T.TEXT_MUTED)
            self._placeholder_active = True
            self._tb.configure(height=34)

    # ── auto-grow ──────────────────────────────────────────────────────────────

    def _adjust_height(self, _event=None) -> None:
        if self._placeholder_active:
            return
        lines = int(self._tb.index("end-1c").split(".")[0])
        h = max(34, min(lines * _LINE_H, _PILL_MAX_LINES * _LINE_H))
        self._tb.configure(height=h)

    # ── submit ─────────────────────────────────────────────────────────────────

    def _on_enter(self, event) -> str:
        if event.state & 0x1:    # Shift held — insert newline
            return ""            # let Tk handle it
        self._submit()
        return "break"           # suppress default newline

    def _submit(self) -> None:
        if self._placeholder_active:
            return
        text = self._tb.get("1.0", "end-1c").strip()
        if not text:
            return
        if self._on_send:
            self._tb.delete("1.0", "end")
            self._tb.configure(height=34)
            self._on_focus_out()   # restore placeholder
            self._on_send(text)

    def _on_action(self) -> None:
        if self._streaming:
            self._on_stop()
        else:
            self._submit()

    # ── streaming state ────────────────────────────────────────────────────────

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
        self._status.configure(text=text, text_color=color or T.TEXT_MUTED)

    def focus_input(self) -> None:
        self._tb.focus_set()
        self._on_focus_in()


# ─────────────────────────────────────────────────────────────────────────────
#  ChatView  (public)
# ─────────────────────────────────────────────────────────────────────────────

class ChatView(ctk.CTkFrame):
    """Consumer-facing streaming chat.

    Architecture contract
    ─────────────────────
    • Data arrives only via the public methods below (UIQueue → main thread).
    • No EventBus, service, or backend imports.
    • No developer logs, pipeline paths, or system telemetry.

    Callbacks (on_cancel required; rest optional)
    ─────────────────────────────────────────────
    on_cancel(request_id)   — stop streaming
    on_export(history)      — list[dict] markdown export
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

        self._request_id:       str | None              = None
        self._streaming:        bool                    = False
        self._streaming_bubble: _AssistantBubble | None = None
        self._last_asst_outer:  ctk.CTkFrame | None     = None
        self._chunk_buffer:     str                     = ""
        self._flush_pending:    bool                    = False
        self._history:          list[dict]              = []
        self._model:            str                     = ""

        self._build()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # ① Slim session bar at top
        self._session_bar = _SessionBar(self, on_export=self._handle_export)
        self._session_bar.pack(fill="x", side="top")

        # ② Scroll area (messages live here)
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True)
        self._scroll.columnconfigure(0, weight=1)

        # ③ Empty state (inside scroll, hidden once messages arrive)
        self._empty = _EmptyState(self._scroll)
        self._empty.pack(fill="both", expand=True, pady=40)

        # ④ Scroll-to-bottom floating button (placed over content area)
        self._scroll_btn = ctk.CTkButton(
            self,
            text="↓",
            width=36, height=36,
            font=(T.FONT_FAMILY, 16, "bold"),
            fg_color=T.BG_GLASS,
            hover_color=T.ACCENT_DEFAULT,
            text_color=T.TEXT_SECONDARY,
            corner_radius=18,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            command=self._scroll_to_bottom_now,
        )
        # starts hidden; shown only when user scrolls up
        self._scroll_btn_visible = False

        # ⑤ Input pill at bottom
        self._pill = _InputPill(
            self,
            on_send=self._on_send,
            on_stop=self._handle_stop,
        )
        self._pill.pack(fill="x", side="bottom")

        # Bind scroll-position checks
        canvas = self._scroll._parent_canvas
        canvas.bind("<MouseWheel>",  self._on_canvas_scroll)
        canvas.bind("<Button-4>",    self._on_canvas_scroll)   # Linux up
        canvas.bind("<Button-5>",    self._on_canvas_scroll)   # Linux down
        canvas.bind("<Configure>",   self._on_canvas_scroll)

    # ── scroll-to-bottom button ───────────────────────────────────────────────

    def _on_canvas_scroll(self, _event=None) -> None:
        self.after(60, self._check_scroll_pos)

    def _check_scroll_pos(self) -> None:
        try:
            _, end = self._scroll._parent_canvas.yview()
            at_bottom = end >= 0.995
        except Exception:
            at_bottom = True
        if at_bottom and self._scroll_btn_visible:
            self._scroll_btn.place_forget()
            self._scroll_btn_visible = False
        elif not at_bottom and not self._scroll_btn_visible:
            self._scroll_btn.place(relx=0.97, rely=0.94, anchor="se")
            self._scroll_btn_visible = True

    def _scroll_to_bottom_now(self) -> None:
        self._scroll._parent_canvas.yview_moveto(1.0)
        self.after(80, self._check_scroll_pos)

    # ── session bar ───────────────────────────────────────────────────────────

    def _refresh_session(self) -> None:
        msg_count = sum(1 for m in self._history if m.get("role") == "user")
        self._session_bar.update(self._model, msg_count)

    # ── row helpers ───────────────────────────────────────────────────────────

    def _hide_empty(self) -> None:
        if self._empty.winfo_ismapped():
            self._empty.pack_forget()

    def _user_row(self, text: str) -> None:
        """Right-aligned bubble + [⎘] [HH:MM] metadata below."""
        self._hide_empty()
        outer = ctk.CTkFrame(self._scroll, fg_color="transparent")
        outer.pack(fill="x", padx=_SIDE_PAD, pady=(0, 2))

        brow = ctk.CTkFrame(outer, fg_color="transparent")
        brow.pack(fill="x")
        ctk.CTkFrame(brow, fg_color="transparent").pack(side="left", fill="x", expand=True)
        bubble = _UserBubble(brow, text)
        bubble.pack(side="right", anchor="e")

        mrow = ctk.CTkFrame(outer, fg_color="transparent")
        mrow.pack(fill="x", pady=(2, 6))
        ctk.CTkFrame(mrow, fg_color="transparent").pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            mrow, text=_hhmm(),
            font=(T.FONT_FAMILY, 10), text_color=T.TEXT_MUTED,
        ).pack(side="right", padx=(0, 4))
        _CopyBtn(mrow, lambda t=text: t).pack(side="right")

    def _assistant_row(self) -> _AssistantBubble:
        """Left-aligned bubble; metadata (copy · ts · regen) added by _finalize_meta."""
        self._hide_empty()
        outer = ctk.CTkFrame(self._scroll, fg_color="transparent")
        outer.pack(fill="x", padx=_SIDE_PAD, pady=(0, 2))
        outer._ts = _hhmm()  # type: ignore[attr-defined]

        brow = ctk.CTkFrame(outer, fg_color="transparent")
        brow.pack(fill="x")
        bubble = _AssistantBubble(brow)
        bubble.pack(side="left", anchor="w")
        ctk.CTkFrame(brow, fg_color="transparent").pack(side="right", fill="x", expand=True)

        self._last_asst_outer = outer
        return bubble

    def _finalize_meta(self, bubble: _AssistantBubble) -> None:
        """Attach copy · timestamp · ↺ Regenerate below the assistant bubble."""
        outer = self._last_asst_outer
        if outer is None:
            return
        mrow = ctk.CTkFrame(outer, fg_color="transparent")
        mrow.pack(fill="x", pady=(2, 8))

        _CopyBtn(mrow, lambda: bubble._raw).pack(side="left")
        ctk.CTkLabel(
            mrow, text=getattr(outer, "_ts", _hhmm()),
            font=(T.FONT_FAMILY, 10), text_color=T.TEXT_MUTED,
        ).pack(side="left", padx=(4, 0))

        if self._on_regenerate:
            ctk.CTkButton(
                mrow,
                text="↺ Regenerate",
                width=90, height=20,
                font=(T.FONT_FAMILY, 10),
                fg_color="transparent",
                hover_color=T.BG_GLASS_BORDER,
                text_color=T.TEXT_MUTED,
                corner_radius=4,
                command=self._on_regenerate,
            ).pack(side="left", padx=(10, 0))

        self._last_asst_outer = None

    # ── public API ─────────────────────────────────────────────────────────────

    def set_model(self, name: str) -> None:
        """Update the model name shown in the session bar."""
        self._model = name
        self._refresh_session()

    def load_history(self, messages: list[dict]) -> None:
        self._clear()
        self._history = list(messages)
        for item in messages:
            role    = str(item.get("role", ""))
            content = str(item.get("content", ""))
            if role == "user":
                self._user_row(content)
            elif role == "assistant":
                b = self._assistant_row()
                b.finalize(content)
                self._finalize_meta(b)
        self._refresh_session()
        self._scroll_to_bottom()

    def show_user_message(self, text: str) -> None:
        self._history.append({"role": "user", "content": text})
        self._user_row(text)
        self._refresh_session()
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
            self._finalize_meta(self._streaming_bubble)
        self._history.append({"role": "assistant", "content": text})
        self._refresh_session()
        self._end_stream()
        self._scroll_to_bottom()

    def show_cancelled(self) -> None:
        self._flush_pending = False
        self._chunk_buffer  = ""
        if self._streaming_bubble:
            self._streaming_bubble.finalize(self._streaming_bubble._raw or "…")
            self._finalize_meta(self._streaming_bubble)
        self._add_strip("cancelled", "Stopped", "Generation was cancelled.")
        self._end_stream()
        self._scroll_to_bottom()

    def show_error(self, message: str) -> None:
        self._flush_pending = False
        self._chunk_buffer  = ""
        if self._streaming_bubble:
            self._streaming_bubble._live = False
            self._streaming_bubble.pack_forget()
            self._streaming_bubble = None
        self._add_strip("error", "Error", message)
        self._end_stream(error=True)
        self._scroll_to_bottom()

    def show_tool_output(self, tool: str, output: str, *, success: bool = True) -> None:
        kind  = "tool" if success else "error"
        self._add_strip(kind, f"Tool: {tool}", output)
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
        self._streaming_bubble = None
        self._last_asst_outer  = None
        self._streaming        = False
        self._history          = []
        # Restore empty state
        self._empty = _EmptyState(self._scroll)
        self._empty.pack(fill="both", expand=True, pady=40)

    def _handle_stop(self) -> None:
        if self._request_id:
            self._on_cancel(self._request_id)

    def _handle_export(self) -> None:
        if self._on_export:
            self._on_export(list(self._history))

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
