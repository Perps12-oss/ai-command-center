"""Chat view — premium minimalist messaging UI, consumer-facing only."""
from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

import customtkinter as ctk

from ai_command_center.ui.components.chat_history_panel import ChatHistoryPanel
from ai_command_center.ui.markdown_plain import format_assistant_markdown
from ai_command_center.ui.markdown_view import parse_markdown
from ai_command_center.ui.design_system import theme_v2 as T

# ── Layout constants ───────────────────────────────────────────────────────────
_BUBBLE_RADIUS  = T.BUBBLE_RADIUS
_BUBBLE_WRAP    = 520
_BUBBLE_TBX_W   = 540
_SIDE_PAD       = 16
_PILL_MAX_LINES = 4
_LINE_H         = 22
_PLACEHOLDER    = "Message…"
_HINT_TEXT      = "⏎ send  ·  Shift+⏎ new line  ·  Ctrl+K  ·  ?"

# Fader palette — for non-intrusive action elements
_CLR_META      = "#404060"   # timestamps, copy icon at rest
_CLR_REGEN     = "#3A3A5A"   # regenerate text at rest
_CLR_HINT      = "#2E2E48"   # keyboard hint — barely visible

_logger = logging.getLogger(__name__)


def _hhmm() -> str:
    return time.strftime("%H:%M")


def _new_sid() -> str:
    return uuid.uuid4().hex[:8]


# ─────────────────────────────────────────────────────────────────────────────
#  Copy micro-button
# ─────────────────────────────────────────────────────────────────────────────

class _CopyBtn(ctk.CTkButton):
    def __init__(self, master, get_text: Callable[[], str]) -> None:
        super().__init__(
            master,
            text="⎘",
            width=22, height=18,
            font=T.FONT_SMALL,
            fg_color="transparent",
            hover_color="transparent",
            text_color=_CLR_META,
            corner_radius=T.SMALL_RADIUS,
            command=self._copy,
        )
        self._get = get_text

    def _copy(self) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(self._get())
            self.configure(text="✓", text_color=T.STATUS_READY)
            self.after(1400, lambda: self.configure(text="⎘", text_color=_CLR_META))
        except Exception as e:
            _logger.warning("Copy failed: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
#  User bubble  (right-aligned, accent colour)
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
            self,
            text=text,
            font=T.FONT_BODY,
            text_color="#FFFFFF",
            wraplength=_BUBBLE_WRAP,
            justify="left",
            anchor="w",
        ).pack(padx=20, pady=14)


# ─────────────────────────────────────────────────────────────────────────────
#  Assistant bubble  (left-aligned, streaming + animated cursor)
# ─────────────────────────────────────────────────────────────────────────────

class _AssistantBubble(ctk.CTkFrame):
    _BLINK_ON  = 550
    _BLINK_OFF = 400

    def __init__(self, master) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            corner_radius=_BUBBLE_RADIUS,
            border_width=0,
        )
        self._raw     = ""
        self._live    = False
        self._cur_vis = True
        self._outer   = None          # will be set by ChatView
        self._timestamp = ""          # will be set by ChatView
        self._blink_job = None        # for after() cancellation

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
        self._textbox.pack(padx=16, pady=13)
        # Markdown tags
        self._textbox.tag_config("bold", font=(T.FONT_FAMILY, 14, "bold"))
        self._textbox.tag_config("italic", font=(T.FONT_FAMILY, 14, "italic"))
        self._textbox.tag_config(
            "code", font=(T.FONT_FAMILY, 13), foreground=T.CODE_TEXT, background=T.CODE_BG
        )
        self._textbox.tag_config(
            "code_block",
            font=(T.FONT_MONO, 12),
            foreground=T.CODE_TEXT,
            background=T.CODE_BG,
            lmargin1=8,
            lmargin2=8,
        )
        self._textbox.tag_config("header", font=(T.FONT_FAMILY, 16, "bold"), foreground=T.TEXT_HEADING)
        self._textbox.tag_config("list", foreground=T.TEXT_PRIMARY)
        self._textbox.configure(state="disabled")
        self._write("●  ●  ●")
        self._live = True
        self._blink()

    def _write(self, text: str, segments: list[tuple[str, str | None]] | None = None) -> None:
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        if segments:
            for seg, tag in segments:
                self._textbox.insert("end", seg, tag)
        else:
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
        self._write(self._raw + ("▌" if self._cur_vis else ""))
        self._cur_vis = not self._cur_vis
        self._blink_job = self.after(
            self._BLINK_ON if self._cur_vis else self._BLINK_OFF,
            self._blink
        )

    def append_raw(self, chunk: str) -> None:
        self._raw += chunk
        if self._cur_vis:
            self._write(self._raw + "▌")

    def finalize(self, full_text: str) -> None:
        self._live = False
        self._raw  = full_text
        self._write("", segments=parse_markdown(full_text))

    def get_raw_text(self) -> str:
        """Expose the raw markdown content without breaking encapsulation."""
        return self._raw

    def destroy(self) -> None:
        """Cancel any pending blink callback before destroying the widget."""
        if self._blink_job:
            self.after_cancel(self._blink_job)
        super().destroy()


# ─────────────────────────────────────────────────────────────────────────────
#  System strip  (errors, tool results, cancellations)
# ─────────────────────────────────────────────────────────────────────────────

class _SystemStrip(ctk.CTkFrame):
    _PALETTE: dict[str, tuple[str, str]] = {
        "error":     ("#3A1010", T.STATUS_ERROR),
        "tool":      ("#0F2010", T.STATUS_READY),
        "cancelled": ("#1E1E10", T.TEXT_MUTED),
        "system":    ("transparent", _CLR_META),
    }
    _DOT = {"error": "✕", "tool": "✓", "cancelled": "◼", "system": "ℹ"}

    def __init__(self, master, kind: str, label: str, body: str) -> None:
        bg, fg = self._PALETTE.get(kind, self._PALETTE["system"])
        super().__init__(
            master,
            fg_color=bg,
            corner_radius=T.CARD_RADIUS,
            border_width=0,
        )
        dot = self._DOT.get(kind, "·")
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(8, 0))
        ctk.CTkLabel(
            hdr,
            text=f"{dot}  {label or kind.upper()}",
            font=(T.FONT_FAMILY, 10, "bold"),
            text_color=fg,
            anchor="w",
        ).pack(side="left")
        if body:
            ctk.CTkLabel(
                self,
                text=body,
                font=T.FONT_SMALL,
                text_color=fg,
                wraplength=620,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=14, pady=(3, 8))
        else:
            ctk.CTkFrame(self, height=6, fg_color="transparent").pack()


# ─────────────────────────────────────────────────────────────────────────────
#  Empty state
# ─────────────────────────────────────────────────────────────────────────────

class _EmptyState(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.place(relx=0.5, rely=0.44, anchor="center")

        ctk.CTkLabel(
            inner, text="◇",
            font=(T.FONT_FAMILY, 52),
            text_color=T.BG_GLASS_BORDER,
        ).pack()
        ctk.CTkLabel(
            inner, text="Start a conversation",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=T.TEXT_MUTED,
        ).pack(pady=(12, 5))
        ctk.CTkLabel(
            inner,
            text="Ask anything · search notes · run commands · store memories",
            font=(T.FONT_FAMILY, 11),
            text_color=_CLR_META,
            justify="center",
        ).pack()

        chips = ctk.CTkFrame(inner, fg_color="transparent")
        chips.pack(pady=(20, 0))
        for hint in ("Ask anything", "note: …", "remember: …", "> shell"):
            ctk.CTkLabel(
                chips,
                text=hint,
                font=(T.FONT_FAMILY, 11),
                text_color=T.TEXT_MUTED,
                fg_color=T.BG_GLASS,
                corner_radius=14,
                padx=12, pady=5,
            ).pack(side="left", padx=5)


# ─────────────────────────────────────────────────────────────────────────────
#  Session bar  (slim top strip)
# ─────────────────────────────────────────────────────────────────────────────

class _SessionBar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_export:         Callable | None,
        on_toggle_history: Callable,
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, height=40)
        self.pack_propagate(False)

        # History toggle button (left)
        self._toggle_btn = ctk.CTkButton(
            self,
            text="◧",
            width=30, height=26,
            font=(T.FONT_FAMILY, 14),
            fg_color="transparent",
            hover_color=T.BG_GLASS,
            text_color=T.TEXT_MUTED,
            corner_radius=T.SMALL_RADIUS,
            command=on_toggle_history,
        )
        self._toggle_btn.pack(side="left", padx=(10, 4), pady=7)

        # Divider
        ctk.CTkFrame(self, width=1, height=18, fg_color=T.BG_GLASS_BORDER).pack(
            side="left", pady=11
        )

        self._model_lbl = ctk.CTkLabel(
            self,
            text="",
            font=(T.FONT_FAMILY, 11),
            text_color=T.TEXT_SECONDARY,
        )
        self._model_lbl.pack(side="left", padx=(8, 0), pady=9)

        self._count_lbl = ctk.CTkLabel(
            self,
            text="",
            font=(T.FONT_FAMILY, 11),
            text_color=_CLR_META,
        )
        self._count_lbl.pack(side="left", padx=(6, 0), pady=9)

        if on_export:
            ctk.CTkButton(
                self,
                text="⬇ Export",
                width=72, height=24,
                font=(T.FONT_FAMILY, 10),
                fg_color=T.BG_GLASS,
                hover_color=T.BG_GLASS_BORDER,
                text_color=_CLR_META,
                corner_radius=T.SMALL_RADIUS,
                command=on_export,
            ).pack(side="right", padx=10, pady=8)

    def update(self, model: str, count: int, history_open: bool) -> None:
        self._model_lbl.configure(
            text=f"◈  {model}" if model else ""
        )
        self._count_lbl.configure(
            text=f"·  {count} message{'s' if count != 1 else ''}" if count else ""
        )
        self._toggle_btn.configure(
            text="◧" if history_open else "▣",
            text_color=T.ACCENT_DEFAULT if history_open else T.TEXT_MUTED,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Input pill  (multi-line growing textbox + hint + send/stop)
# ─────────────────────────────────────────────────────────────────────────────

class _InputPill(ctk.CTkFrame):
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
        self._on_send       = on_send
        self._on_stop       = on_stop
        self._streaming     = False
        self._ph_active     = True

        # Floating pill wrapper
        pill = ctk.CTkFrame(
            self,
            fg_color=T.BG_GLASS,
            corner_radius=28,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
        )
        pill.pack(fill="x", padx=16, pady=(10, 4))

        # Attachment icon
        ctk.CTkButton(
            pill, text="⊕",
            width=34, height=34,
            font=(T.FONT_FAMILY, 16),
            fg_color="transparent",
            hover_color=T.BG_GLASS_BORDER,
            text_color=_CLR_META,
            corner_radius=17,
            command=lambda: None,
        ).pack(side="left", padx=(8, 0), pady=5)

        # Growing textbox
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
        self._tb.configure(text_color=_CLR_META)
        self._tb.bind("<FocusIn>",    self._focus_in)
        self._tb.bind("<FocusOut>",   self._focus_out)
        self._tb.bind("<Return>",     self._on_enter)
        self._tb.bind("<KeyRelease>", self._grow)

        # Send / Stop round button
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

        # Keyboard hint — very faint
        ctk.CTkLabel(
            self,
            text=_HINT_TEXT,
            font=(T.FONT_FAMILY, 9),
            text_color=_CLR_HINT,
        ).pack(side="left", padx=20, pady=(0, 5))

        # Status micro-label
        self._status = ctk.CTkLabel(
            self, text="",
            font=(T.FONT_FAMILY, 10),
            text_color=_CLR_META,
        )
        self._status.pack(side="right", padx=20, pady=(0, 5))

    # ── placeholder ────────────────────────────────────────────────────────────

    def _focus_in(self, _=None) -> None:
        if self._ph_active:
            self._tb.delete("1.0", "end")
            self._tb.configure(text_color=T.TEXT_PRIMARY)
            self._ph_active = False

    def _focus_out(self, _=None) -> None:
        if not self._tb.get("1.0", "end-1c").strip():
            self._tb.insert("1.0", _PLACEHOLDER)
            self._tb.configure(text_color=_CLR_META)
            self._ph_active = True
            self._tb.configure(height=34)

    # ── grow ───────────────────────────────────────────────────────────────────

    def _grow(self, _=None) -> None:
        if self._ph_active:
            return
        lines = int(self._tb.index("end-1c").split(".")[0])
        h = max(34, min(lines * _LINE_H, _PILL_MAX_LINES * _LINE_H))
        self._tb.configure(height=h)

    # ── submit ─────────────────────────────────────────────────────────────────

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

    # ── state ──────────────────────────────────────────────────────────────────

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
        self._status.configure(text=text, text_color=color or _CLR_META)

    def focus_input(self) -> None:
        self._tb.focus_set()
        self._focus_in()


# ─────────────────────────────────────────────────────────────────────────────
#  ChatView  (public)
# ─────────────────────────────────────────────────────────────────────────────

class ChatView(ctk.CTkFrame):
    """Consumer-facing streaming chat.

    Architecture contract
    ─────────────────────
    • Data arrives only via the public methods below (UIQueue → main thread).
    • No EventBus, service, or backend imports.
    • No developer logs, pipeline paths, or runtime metrics collection.
    • The view does NOT manage session persistence beyond the current conversation.
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
        self._chunk_buffer:     str                     = ""
        self._flush_pending:    bool                    = False
        self._history:          list[dict]              = []   # current conversation
        self._model:            str                     = ""

        # In-memory session store (owner is the view, but could be moved)
        self._sessions:         dict[str, list[dict]]   = {}
        self._session_id:       str                     = _new_sid()
        self._history_open:     bool                    = True

        self._build()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # ① Session bar (top, full width)
        self._session_bar = _SessionBar(
            self,
            on_export=self._handle_export,
            on_toggle_history=self._toggle_history,
        )
        self._session_bar.pack(fill="x", side="top")

        # ② Input pill (bottom, full width)
        self._pill = _InputPill(
            self,
            on_send=self._on_send,
            on_stop=self._handle_stop,
        )
        self._pill.pack(fill="x", side="bottom")

        # ③ Middle: history panel + scroll area
        middle = ctk.CTkFrame(self, fg_color="transparent")
        middle.pack(fill="both", expand=True)

        self._history_panel = ChatHistoryPanel(
            middle,
            on_new=self._new_session,
            on_select=self._load_session,
            on_delete=self._delete_session,
        )
        self._history_panel.pack(fill="y", side="left")

        # Vertical divider
        ctk.CTkFrame(
            middle, width=1, fg_color=T.BG_GLASS_BORDER
        ).pack(fill="y", side="left")

        self._scroll = ctk.CTkScrollableFrame(
            middle, fg_color=T.BG_DEEP, corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True)
        self._scroll.columnconfigure(0, weight=1)

        # ④ Empty state (inside scroll)
        self._empty = _EmptyState(self._scroll)
        self._empty.pack(fill="both", expand=True, pady=30)

        # ⑤ Scroll-to-bottom floating button
        self._scroll_btn = ctk.CTkButton(
            self,
            text="↓",
            width=34, height=34,
            font=(T.FONT_FAMILY, 15, "bold"),
            fg_color=T.BG_GLASS,
            hover_color=T.ACCENT_DEFAULT,
            text_color=T.TEXT_SECONDARY,
            corner_radius=17,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            command=self._scroll_to_bottom_now,
        )
        self._scroll_btn_visible = False

        # Bind scroll-position checks (add="+" to not override others)
        canvas = self._scroll._parent_canvas
        for event in ("<MouseWheel>", "<Button-4>", "<Button-5>", "<Configure>"):
            canvas.bind(event, self._on_canvas_scroll, add="+")

        # Context bar: sources · token estimate (AppState-driven)
        self._context_bar = ctk.CTkLabel(
            self,
            text="Sources: — · Tokens: —",
            font=(T.FONT_FAMILY, 10),
            text_color=_CLR_META,
            anchor="w",
        )
        self._context_bar.pack(fill="x", side="bottom", padx=20, pady=(0, 4))

        self._refresh_session_bar()

    # ── history toggle ────────────────────────────────────────────────────────

    def _toggle_history(self) -> None:
        self._history_open = not self._history_open
        if self._history_open:
            self._history_panel.pack(fill="y", side="left", before=self._scroll)
        else:
            self._history_panel.pack_forget()
        self._refresh_session_bar()

    # ── in-memory session management ──────────────────────────────────────────

    def _save_current_session(self) -> None:
        """Save current conversation into the session store and update the panel."""
        if not self._history:
            return
        first_user = next(
            (m["content"] for m in self._history if m.get("role") == "user"), None
        )
        if not first_user:
            return
        title = (first_user[:36] + "…") if len(first_user) > 36 else first_user
        # Update or insert
        if self._session_id in self._sessions:
            # Existing session → update (preserve creation time)
            self._sessions[self._session_id] = list(self._history)
            self._history_panel.update_session(self._session_id, title, _hhmm())
        else:
            # New session → add
            self._sessions[self._session_id] = list(self._history)
            self._history_panel.add_session(
                self._session_id, title, _hhmm(), active=False
            )

    def _new_session(self) -> None:
        """Save current, clear display, start a fresh session."""
        self._save_current_session()
        self._session_id = _new_sid()
        self._clear_ui()
        self._history = []
        self._refresh_session_bar()

    def _load_session(self, sid: str) -> None:
        """Load a stored session into the chat display."""
        # Save the current session first (it will update or insert)
        self._save_current_session()
        messages = self._sessions.get(sid, [])
        self._session_id = sid
        self._history_panel.set_active(sid)
        self._clear_ui()                # Remove old widgets, keep history intact for now
        self._history = list(messages)  # Replace history data
        for item in messages:
            role    = str(item.get("role", ""))
            content = str(item.get("content", ""))
            if role == "user":
                self._user_row(content)
            elif role == "assistant":
                b = self._assistant_row()
                b.finalize(content)
                self._finalize_meta(b)
        self._refresh_session_bar()
        self._scroll_to_bottom()

    def _delete_session(self, sid: str) -> None:
        self._sessions.pop(sid, None)
        self._history_panel.remove_session(sid)
        if sid == self._session_id:
            self._new_session()

    # ── scroll-to-bottom button ───────────────────────────────────────────────

    def _on_canvas_scroll(self, _=None) -> None:
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
            self._scroll_btn.place(relx=0.97, rely=0.93, anchor="se")
            self._scroll_btn_visible = True

    def _scroll_to_bottom_now(self) -> None:
        self._scroll._parent_canvas.yview_moveto(1.0)
        self.after(80, self._check_scroll_pos)

    # ── session bar ───────────────────────────────────────────────────────────

    def _refresh_session_bar(self) -> None:
        count = len(self._history)   # total messages, not just user prompts
        self._session_bar.update(self._model, count, self._history_open)

    # ── row helpers ───────────────────────────────────────────────────────────

    def _hide_empty(self) -> None:
        if self._empty.winfo_ismapped():
            self._empty.pack_forget()

    def _user_row(self, text: str) -> None:
        self._hide_empty()
        outer = ctk.CTkFrame(self._scroll, fg_color="transparent")
        outer.pack(fill="x", padx=_SIDE_PAD, pady=(0, 4))

        brow = ctk.CTkFrame(outer, fg_color="transparent")
        brow.pack(fill="x")
        ctk.CTkFrame(brow, fg_color="transparent").pack(side="left", fill="x", expand=True)
        _UserBubble(brow, text).pack(side="right", anchor="e")

        # Metadata: copy · timestamp (right-aligned, fader colors)
        mrow = ctk.CTkFrame(outer, fg_color="transparent")
        mrow.pack(fill="x", pady=(3, 10))
        ctk.CTkFrame(mrow, fg_color="transparent").pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            mrow,
            text=_hhmm(),
            font=(T.FONT_FAMILY, 9),
            text_color=_CLR_META,
        ).pack(side="right", padx=(0, 4))
        _CopyBtn(mrow, lambda t=text: t).pack(side="right")

    def _assistant_row(self) -> _AssistantBubble:
        self._hide_empty()
        outer = ctk.CTkFrame(self._scroll, fg_color="transparent")
        outer.pack(fill="x", padx=_SIDE_PAD, pady=(0, 4))

        brow = ctk.CTkFrame(outer, fg_color="transparent")
        brow.pack(fill="x")
        bubble = _AssistantBubble(brow)
        bubble.pack(side="left", anchor="w")
        # Store ownership directly on the bubble
        bubble._outer = outer
        bubble._timestamp = _hhmm()
        ctk.CTkFrame(brow, fg_color="transparent").pack(side="right", fill="x", expand=True)

        return bubble

    def _finalize_meta(self, bubble: _AssistantBubble) -> None:
        """Attach copy · timestamp · ↺ Regenerate row below completed bubble."""
        # Retrieve the outer frame stored on the bubble
        outer = getattr(bubble, "_outer", None)
        if outer is None:
            return
        timestamp = getattr(bubble, "_timestamp", _hhmm())

        mrow = ctk.CTkFrame(outer, fg_color="transparent")
        mrow.pack(fill="x", pady=(3, 10))

        _CopyBtn(mrow, bubble.get_raw_text).pack(side="left")
        ctk.CTkLabel(
            mrow,
            text=timestamp,
            font=(T.FONT_FAMILY, 9),
            text_color=_CLR_META,
        ).pack(side="left", padx=(4, 0))

        if self._on_regenerate:
            ctk.CTkButton(
                mrow,
                text="↺ Regenerate",
                width=82, height=18,
                font=(T.FONT_FAMILY, 9),
                fg_color="transparent",
                hover_color=T.BG_GLASS,
                text_color=_CLR_REGEN,
                corner_radius=4,
                command=self._on_regenerate,
            ).pack(side="left", padx=(10, 0))

    # ── public API ─────────────────────────────────────────────────────────────

    def set_model(self, name: str) -> None:
        self._model = name
        self._refresh_session_bar()

    def focus_input(self) -> None:
        self._pill.focus_input()

    def update_context_bar(self, sources: list[str], tokens: int) -> None:
        if not sources:
            self._context_bar.configure(text=f"Sources: — · Tokens: {tokens}")
            return
        names = [s.split("_")[-1].split("/")[-1][:18] for s in sources]
        summary = ", ".join(names)
        if len(summary) > 50:
            summary = summary[:47] + "…"
        self._context_bar.configure(text=f"Sources: {summary} · Tokens: {tokens}")

    def load_history(self, messages: list[dict]) -> None:
        self._clear_ui()
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
        self._refresh_session_bar()
        self._scroll_to_bottom()

    def show_user_message(self, text: str) -> None:
        self._history.append({"role": "user", "content": text})
        self._user_row(text)
        self._refresh_session_bar()
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
        self._refresh_session_bar()
        self._end_stream()
        self._scroll_to_bottom()

    def show_cancelled(self) -> None:
        self._flush_pending = False
        self._chunk_buffer  = ""
        if self._streaming_bubble:
            self._streaming_bubble.finalize(self._streaming_bubble.get_raw_text() or "…")
            self._finalize_meta(self._streaming_bubble)
        self._add_strip("cancelled", "Stopped", "Generation was cancelled.")
        self._end_stream()
        self._scroll_to_bottom()

    def show_error(self, message: str) -> None:
        self._flush_pending = False
        self._chunk_buffer  = ""
        if self._streaming_bubble:
            # Properly destroy the bubble and its outer container
            outer = getattr(self._streaming_bubble, "_outer", None)
            if outer:
                outer.destroy()
            else:
                self._streaming_bubble.destroy()
            self._streaming_bubble = None
        self._add_strip("error", "Error", message)
        self._end_stream(error=True)
        self._scroll_to_bottom()

    def show_tool_output(self, tool: str, output: str, *, success: bool = True) -> None:
        kind = "tool" if success else "error"
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

    def _clear_ui(self) -> None:
        """Destroy all message widgets but keep the history data intact."""
        for child in self._scroll.winfo_children():
            child.destroy()
        self._streaming_bubble = None
        self._streaming = False
        # Recreate empty state
        self._empty = _EmptyState(self._scroll)
        self._empty.pack(fill="both", expand=True, pady=30)

    def _clear_history(self) -> None:
        """Reset the conversation history list (does not touch UI)."""
        self._history = []

    def _reset_conversation(self) -> None:
        """Clear both UI and history."""
        self._clear_ui()
        self._clear_history()

    # Backward-compatible alias (deprecated)
    def _clear_messages(self) -> None:
        """Deprecated: use _reset_conversation()."""
        self._reset_conversation()

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