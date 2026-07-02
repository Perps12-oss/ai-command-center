"""Streaming bubble rendering and message chrome widgets."""
from __future__ import annotations

import logging
from typing import Callable

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.markdown_view import parse_markdown

BUBBLE_RADIUS = T.BUBBLE_RADIUS
BUBBLE_WRAP = 520
BUBBLE_TBX_W = 540
SIDE_PAD = 16

# Fader palette — for non-intrusive action elements
CLR_META = "#404060"   # timestamps, copy icon at rest
CLR_REGEN = "#3A3A5A"   # regenerate text at rest

_logger = logging.getLogger(__name__)


class CopyBtn(ctk.CTkButton):
    def __init__(self, master, get_text: Callable[[], str]) -> None:
        super().__init__(
            master,
            text="⎘",
            width=22, height=18,
            font=T.FONT_SMALL,
            fg_color="transparent",
            hover_color="transparent",
            text_color=CLR_META,
            corner_radius=T.SMALL_RADIUS,
            command=self._copy,
        )
        self._get = get_text

    def _copy(self) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(self._get())
            self.configure(text="✓", text_color=T.STATUS_READY)
            self.after(1400, lambda: self.configure(text="⎘", text_color=CLR_META))
        except Exception as e:
            _logger.warning("Copy failed: %s", e)


class UserBubble(ctk.CTkFrame):
    def __init__(self, master, text: str) -> None:
        super().__init__(
            master,
            fg_color=T.ACCENT_DEFAULT,
            corner_radius=BUBBLE_RADIUS,
            border_width=0,
        )
        self._text = text
        ctk.CTkLabel(
            self,
            text=text,
            font=T.FONT_BODY,
            text_color="#FFFFFF",
            wraplength=BUBBLE_WRAP,
            justify="left",
            anchor="w",
        ).pack(padx=20, pady=14)


class AssistantBubble(ctk.CTkFrame):
    _BLINK_ON = 550
    _BLINK_OFF = 400

    def __init__(self, master) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            corner_radius=BUBBLE_RADIUS,
            border_width=0,
        )
        self._raw = ""
        self._live = False
        self._cur_vis = True
        self._outer = None          # will be set by ChatView
        self._timestamp = ""          # will be set by ChatView
        self._blink_job = None        # for after() cancellation

        self._textbox = ctk.CTkTextbox(
            self,
            font=T.FONT_BODY,
            fg_color="transparent",
            text_color=T.TEXT_PRIMARY,
            wrap="word",
            activate_scrollbars=False,
            width=BUBBLE_TBX_W,
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
        self._raw = full_text
        self._write("", segments=parse_markdown(full_text))

    def get_raw_text(self) -> str:
        """Expose the raw markdown content without breaking encapsulation."""
        return self._raw

    def destroy(self) -> None:
        """Cancel any pending blink callback before destroying the widget."""
        if self._blink_job:
            self.after_cancel(self._blink_job)
        super().destroy()


class SystemStrip(ctk.CTkFrame):
    _PALETTE: dict[str, tuple[str, str]] = {
        "error":     ("#3A1010", T.STATUS_ERROR),
        "tool":      ("#0F2010", T.STATUS_READY),
        "cancelled": ("#1E1E10", T.TEXT_MUTED),
        "system":    ("transparent", CLR_META),
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


class EmptyState(ctk.CTkFrame):
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
            text_color=CLR_META,
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
