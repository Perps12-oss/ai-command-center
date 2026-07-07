"""MessageBlock v2 — LibreChat-style message bubbles with collapsible footer.

Components
──────────
  UserMessageBlock     — right-aligned user bubble with copy + timestamp
  AssistantMessageBlock— left-aligned assistant bubble with streaming support,
                         collapsible footer (model · duration · tokens)

Reference: LibreChat message bubble style.

Architecture contract
─────────────────────
• Pure display widgets — no EventBus, no service imports.
• AssistantMessageBlock.append_chunk() / finalize() called from UIQueue.
• Footer data supplied via finalize(text, model, duration_ms, tokens).
"""
from __future__ import annotations

import time
from typing import Any, Callable

import customtkinter as ctk

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.markdown_view import parse_markdown

_BUBBLE_WRAP = 520
_BUBBLE_TBX_W = 540
_CURSOR_CHAR = "▌"
_PLACEHOLDER = "●  ●  ●"
_META_FONT = (T.FONT_FAMILY, 9)
_FOOTER_FONT = (T.FONT_FAMILY, 9)


def _hhmm() -> str:
    return time.strftime("%H:%M")


class _CopyBtn(ctk.CTkButton):
    """Small clipboard copy button."""

    def __init__(self, master: Any, get_text: Callable[[], str]) -> None:
        super().__init__(
            master,
            text="⎘",
            width=22, height=18,
            font=(T.FONT_FAMILY, 10),
            fg_color="transparent",
            hover_color=T.BG_GLASS,
            text_color=T.TEXT_MUTED,
            corner_radius=4,
            command=self._copy,
        )
        self._get_text = get_text

    def _copy(self) -> None:
        try:
            text = self._get_text()
            self.clipboard_clear()
            self.clipboard_append(text)
            self.configure(text="✓", text_color=T.STATUS_READY)
            self.after(1500, lambda: self.configure(text="⎘", text_color=T.TEXT_MUTED))
        except Exception:
            pass


class UserMessageBlock(ctk.CTkFrame):
    """Right-aligned user message bubble.

    ┌──────────────────────────────────────────┐
    │                                [message] │
    │                    ⎘  12:34              │
    └──────────────────────────────────────────┘
    """

    def __init__(
        self,
        master: Any,
        text: str,
        *,
        timestamp: str = "",
        inspect_ref: InspectableRef | None = None,
        on_inspect_select: Callable[[InspectableRef], None] | None = None,
        on_inspect_navigate: Callable[[InspectableRef], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._text = text
        self._inspect_ref = inspect_ref
        self._on_inspect_select = on_inspect_select
        self._on_inspect_navigate = on_inspect_navigate
        ts = timestamp or _hhmm()

        # Bubble row (right-aligned)
        brow = ctk.CTkFrame(self, fg_color="transparent")
        brow.pack(fill="x")
        ctk.CTkFrame(brow, fg_color="transparent").pack(
            side="left", fill="x", expand=True
        )

        bubble = ctk.CTkFrame(
            brow,
            fg_color=T.MSG_USER_BG,
            corner_radius=T.BUBBLE_RADIUS,
            border_width=1,
            border_color=T.MSG_USER_BORDER,
        )
        bubble.pack(side="right", anchor="e", pady=2)

        txt_lbl = ctk.CTkLabel(
            bubble,
            text=text,
            font=T.FONT_BODY,
            text_color=T.MSG_USER_TEXT,
            wraplength=_BUBBLE_WRAP,
            justify="left",
            anchor="w",
        )
        txt_lbl.pack(padx=14, pady=10)

        # Meta row
        mrow = ctk.CTkFrame(self, fg_color="transparent")
        mrow.pack(fill="x", pady=(2, 8))
        ctk.CTkFrame(mrow, fg_color="transparent").pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkLabel(
            mrow,
            text=ts,
            font=_META_FONT,
            text_color=T.TEXT_MUTED,
        ).pack(side="right", padx=(0, 4))
        _CopyBtn(mrow, lambda: self._text).pack(side="right")
        self._bind_inspect_handlers(self, bubble, txt_lbl, mrow)

    def get_text(self) -> str:
        return self._text

    def _bind_inspect_handlers(self, *widgets: Any) -> None:
        if self._inspect_ref is None:
            return
        for widget in widgets:
            try:
                widget.bind("<Button-1>", self._handle_inspect_select, add="+")
                widget.bind("<Double-Button-1>", self._handle_inspect_navigate, add="+")
            except Exception:
                pass

    def _handle_inspect_select(self, _event: Any) -> None:
        if self._inspect_ref is not None and self._on_inspect_select is not None:
            self._on_inspect_select(self._inspect_ref)

    def _handle_inspect_navigate(self, _event: Any) -> None:
        if self._inspect_ref is not None and self._on_inspect_navigate is not None:
            self._on_inspect_navigate(self._inspect_ref)


class AssistantMessageBlock(ctk.CTkFrame):
    """Left-aligned assistant message bubble with streaming and collapsible footer.

    ┌──────────────────────────────────────────┐
    │ [message content …]                      │
    │ ⎘  12:34  ↺ Regenerate  👍  👎           │
    │ ▾ llama3.2 · 1.2s · 312 tokens          │  ← collapsible footer
    └──────────────────────────────────────────┘
    """

    def __init__(
        self,
        master: Any,
        *,
        on_regenerate: Callable[[], None] | None = None,
        on_rate: Callable[[str], None] | None = None,
        inspect_ref: InspectableRef | None = None,
        on_inspect_select: Callable[[InspectableRef], None] | None = None,
        on_inspect_navigate: Callable[[InspectableRef], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_regenerate = on_regenerate
        self._on_rate = on_rate
        self._inspect_ref = inspect_ref
        self._on_inspect_select = on_inspect_select
        self._on_inspect_navigate = on_inspect_navigate
        self._raw_text: str = ""
        self._timestamp: str = _hhmm()
        self._streaming: bool = False
        self._footer_visible: bool = False

        self._build()

    def _build(self) -> None:
        # Bubble
        brow = ctk.CTkFrame(self, fg_color="transparent")
        brow.pack(fill="x")

        self._bubble = ctk.CTkFrame(
            brow,
            fg_color=T.MSG_ASSISTANT_BG,
            corner_radius=T.BUBBLE_RADIUS,
            border_width=1,
            border_color=T.MSG_ASSISTANT_BORDER,
        )
        self._bubble.pack(side="left", anchor="w", pady=2)
        ctk.CTkFrame(brow, fg_color="transparent").pack(
            side="right", fill="x", expand=True
        )

        self._textbox = ctk.CTkTextbox(
            self._bubble,
            width=_BUBBLE_TBX_W,
            wrap="word",
            font=T.FONT_BODY,
            fg_color=T.MSG_ASSISTANT_BG,
            text_color=T.MSG_ASSISTANT_TEXT,
            border_width=0,
            activate_scrollbars=False,
            height=40,
        )
        self._textbox.pack(padx=12, pady=10, fill="x")
        self._textbox.configure(state="normal")
        self._textbox.insert("end", _PLACEHOLDER)
        self._textbox.configure(state="disabled")
        self._bind_inspect_handlers(self, self._bubble, self._textbox)

    def append_raw(self, text: str) -> None:
        """Append raw streaming text to the textbox."""
        if not text:
            return
        if not self._streaming:
            self._streaming = True
            self._raw_text = ""
            self._textbox.configure(state="normal")
            self._textbox.delete("1.0", "end")

        self._raw_text += text
        self._refresh_inspect_ref()
        self._textbox.configure(state="normal")
        self._textbox.insert("end", text)
        self._textbox.configure(state="disabled")
        self._resize_textbox()

    def finalize(
        self,
        text: str,
        *,
        model: str = "",
        duration_ms: int = 0,
        tokens: int = 0,
    ) -> None:
        """Finalize the message with full text and optional metadata."""
        self._streaming = False
        self._raw_text = text
        self._refresh_inspect_ref()
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        try:
            segments = parse_markdown(text)
            _apply_markdown_segments(self._textbox, segments)
        except Exception:
            self._textbox.insert("end", text)
        self._textbox.configure(state="disabled")
        self._resize_textbox()
        self._build_meta_row(model=model, duration_ms=duration_ms, tokens=tokens)

    def get_raw_text(self) -> str:
        return self._raw_text

    def _refresh_inspect_ref(self) -> None:
        if self._inspect_ref is None:
            return
        payload = dict(self._inspect_ref.payload)
        payload["content"] = self._raw_text
        self._inspect_ref = InspectableRef.from_payload(
            {
                "kind": self._inspect_ref.kind,
                "ref_id": self._inspect_ref.ref_id,
                "label": self._inspect_ref.label,
                "payload": payload,
            }
        )

    def _bind_inspect_handlers(self, *widgets: Any) -> None:
        if self._inspect_ref is None:
            return
        for widget in widgets:
            try:
                widget.bind("<Button-1>", self._handle_inspect_select, add="+")
                widget.bind("<Double-Button-1>", self._handle_inspect_navigate, add="+")
            except Exception:
                pass

    def _handle_inspect_select(self, _event: Any) -> None:
        if self._inspect_ref is not None and self._on_inspect_select is not None:
            self._on_inspect_select(self._inspect_ref)

    def _handle_inspect_navigate(self, _event: Any) -> None:
        if self._inspect_ref is not None and self._on_inspect_navigate is not None:
            self._on_inspect_navigate(self._inspect_ref)

    def _resize_textbox(self) -> None:
        """Expand textbox height to fit content (no scrollbar needed)."""
        try:
            lines = int(self._textbox.index("end-1c").split(".")[0])
            h = max(40, min(lines * 20 + 10, 600))
            self._textbox.configure(height=h)
        except Exception:
            pass

    def _build_meta_row(
        self, *, model: str, duration_ms: int, tokens: int
    ) -> None:
        mrow = ctk.CTkFrame(self, fg_color="transparent")
        mrow.pack(fill="x", pady=(2, 4))

        _CopyBtn(mrow, self.get_raw_text).pack(side="left")
        ctk.CTkLabel(
            mrow,
            text=self._timestamp,
            font=_META_FONT,
            text_color=T.TEXT_MUTED,
        ).pack(side="left", padx=(4, 0))

        if self._on_regenerate:
            ctk.CTkButton(
                mrow,
                text="↺",
                width=26, height=18,
                font=(T.FONT_FAMILY, 9),
                fg_color="transparent",
                hover_color=T.BG_GLASS,
                text_color=T.TEXT_MUTED,
                corner_radius=4,
                command=self._on_regenerate,
            ).pack(side="left", padx=(8, 0))

        for emoji, rating in (("👍", "up"), ("👎", "down")):
            ctk.CTkButton(
                mrow,
                text=emoji,
                width=24, height=18,
                font=(T.FONT_FAMILY, 10),
                fg_color="transparent",
                hover_color=T.BG_GLASS,
                text_color=T.TEXT_MUTED,
                corner_radius=4,
                command=lambda r=rating: self._on_rate(r) if self._on_rate else None,
            ).pack(side="right", padx=2)

        if model or duration_ms or tokens:
            self._build_footer(mrow, model=model, duration_ms=duration_ms, tokens=tokens)

    def _build_footer(
        self,
        meta_row: ctk.CTkFrame,
        *,
        model: str,
        duration_ms: int,
        tokens: int,
    ) -> None:
        """Add collapsible footer with model·duration·tokens."""
        footer_parts: list[str] = []
        if model:
            footer_parts.append(model)
        if duration_ms:
            footer_parts.append(f"{duration_ms / 1000:.1f}s")
        if tokens:
            footer_parts.append(f"{tokens} tokens")
        footer_text = " · ".join(footer_parts)

        self._footer_frame = ctk.CTkFrame(
            self,
            fg_color=T.BG_GLASS,
            corner_radius=T.SMALL_RADIUS,
        )
        ctk.CTkLabel(
            self._footer_frame,
            text=footer_text,
            font=_FOOTER_FONT,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(padx=8, pady=3, anchor="w")

        ctk.CTkButton(
            meta_row,
            text="▾ details",
            width=52, height=16,
            font=(T.FONT_FAMILY, 8),
            fg_color="transparent",
            hover_color=T.BG_GLASS,
            text_color=T.TEXT_MUTED,
            corner_radius=4,
            command=self._toggle_footer,
        ).pack(side="left", padx=(6, 0))

    def _toggle_footer(self) -> None:
        if not hasattr(self, "_footer_frame"):
            return
        self._footer_visible = not self._footer_visible
        if self._footer_visible:
            self._footer_frame.pack(fill="x", padx=14, pady=(0, 6))
        else:
            self._footer_frame.pack_forget()


def _apply_markdown_segments(
    textbox: ctk.CTkTextbox,
    segments: list[tuple[str, str]],
) -> None:
    """Apply parsed markdown segments to a CTkTextbox.

    Segments are (tag, text) tuples where tag is one of:
    normal, bold, italic, code, code_block, header, list.
    """
    try:
        tk_text = textbox._textbox
        tk_text.tag_config("bold", font=(T.FONT_FAMILY, 13, "bold"))
        tk_text.tag_config("italic", font=(T.FONT_FAMILY, 13, "italic"))
        tk_text.tag_config(
            "code",
            font=("Consolas", 12),
            foreground=T.CODE_TEXT,
            background=T.CODE_BG,
        )
        tk_text.tag_config(
            "code_block",
            font=("Consolas", 11),
            foreground=T.CODE_TEXT,
            background=T.CODE_BG,
            lmargin1=8, lmargin2=8,
        )
        tk_text.tag_config(
            "header",
            font=(T.FONT_FAMILY, 16, "bold"),
            foreground=T.TEXT_HEADING,
        )
    except Exception:
        pass

    for tag, text in segments:
        try:
            textbox.configure(state="normal")
            if tag in {"bold", "italic", "code", "code_block", "header", "list"}:
                textbox._textbox.insert("end", text, tag)
            else:
                textbox.insert("end", text)
        except Exception:
            try:
                textbox.configure(state="normal")
                textbox.insert("end", text)
            except Exception:
                pass
