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
from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.core.state.artifact_state import ArtifactCatalogItem
from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.artifact_list_view import ArtifactListView
from ai_command_center.ui.components.inspector.inspect_gestures import bind_inspect_gestures
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.markdown_view import parse_markdown
from ai_command_center.ui.views.chat.response_action_strip import ResponseActionStrip

_BUBBLE_WRAP = 520
_BUBBLE_TBX_W = 540
_CURSOR_CHAR = "▌"
# Intentional UX affordance shown while waiting for the first stream chunk.
_STREAMING_INDICATOR = "●  ●  ●"
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
        bind_inspect_gestures(
            (self, bubble, txt_lbl, mrow),
            get_ref=lambda: self._inspect_ref,
            on_select=self._on_inspect_select,
            on_navigate=self._on_inspect_navigate,
        )

    def get_text(self) -> str:
        return self._text


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
        on_artifact_action: Callable[[str, str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_regenerate = on_regenerate
        self._on_rate = on_rate
        self._inspect_ref = inspect_ref
        self._on_inspect_select = on_inspect_select
        self._on_inspect_navigate = on_inspect_navigate
        self._on_artifact_action = on_artifact_action or (lambda _a, _k: None)
        self._raw_text: str = ""
        self._timestamp: str = _hhmm()
        self._streaming: bool = False
        self._footer_visible: bool = False
        self._action_strip: ResponseActionStrip | None = None
        self._artifact_list: ArtifactListView | None = None
        self._artifact_count: int = 0
        self._execution_id: str = ""

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
        self._textbox.insert("end", _STREAMING_INDICATOR)
        self._textbox.configure(state="disabled")
        bind_inspect_gestures(
            (self, self._bubble),
            get_ref=lambda: self._inspect_ref,
            on_select=self._on_inspect_select,
            on_navigate=self._on_inspect_navigate,
        )

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
        execution_id: str = "",
        execution_index: int = 0,
        artifact_count: int = 0,
        decision_count: int = 0,
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
        self._execution_id = execution_id
        self._artifact_count = artifact_count
        self._build_meta_row(model=model, duration_ms=duration_ms, tokens=tokens)
        self._rebuild_action_strip(
            execution_id=execution_id,
            execution_index=execution_index,
            artifact_count=artifact_count,
            decision_count=decision_count,
        )

    def set_artifacts(self, artifacts: Sequence[ArtifactCatalogItem]) -> None:
        """Render or refresh inline artifact cards below the assistant bubble."""
        catalog = tuple(artifacts)
        count = len(catalog)
        if count == 0 and self._artifact_list is None:
            return
        if self._artifact_list is None:
            self._artifact_list = ArtifactListView(
                self,
                on_action=self._on_artifact_action,
            )
            self._artifact_list.pack(fill="x", padx=14, pady=(0, 4))
        self._artifact_list.set_artifacts(catalog)
        if count != self._artifact_count:
            self._artifact_count = count
            self._rebuild_action_strip(
                execution_id=self._execution_id,
                artifact_count=count,
            )

    def _rebuild_action_strip(
        self,
        *,
        execution_id: str = "",
        execution_index: int = 0,
        artifact_count: int = 0,
        decision_count: int = 0,
    ) -> None:
        if self._action_strip is not None:
            self._action_strip.destroy()
            self._action_strip = None
        if not (execution_id or execution_index or artifact_count or decision_count):
            return
        self._action_strip = ResponseActionStrip(
            self,
            execution_id=execution_id,
            execution_index=execution_index,
            artifact_count=artifact_count,
            decision_count=decision_count,
            on_inspect_select=self._on_inspect_select,
            on_inspect_navigate=self._on_inspect_navigate,
        )
        self._action_strip.pack(fill="x", padx=14, pady=(0, 6))

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

    Segments are (text, tag) tuples where tag is one of:
    normal, bold, italic, code, code_block, header, list.
    """
    import logging
    logger = logging.getLogger(__name__)

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
    except Exception as exc:
        logger.debug("Failed to configure textbox tags: %s", exc)

    for text, tag in segments:
        try:
            textbox.configure(state="normal")
            if tag in {"bold", "italic", "code", "code_block", "header", "list"}:
                textbox._textbox.insert("end", text, tag)
            else:
                textbox.insert("end", text)
        except Exception as exc:
            logger.exception("Markdown rendering failed", exc_info=exc)
            try:
                textbox.configure(state="normal")
                textbox.insert("end", text)
            except Exception:
                pass
