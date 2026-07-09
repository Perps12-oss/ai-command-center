"""MessageDocument — Claude Desktop-style documentation layout (no bubbles)."""
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
from ai_command_center.ui.views.chat.message_block import _apply_markdown_segments
from ai_command_center.ui.views.chat.response_action_strip import ResponseActionStrip

_AVATAR_SIZE = 32
_META_FONT = (T.FONT_FAMILY, 9)
_BODY_WIDTH = 720
_CURSOR_CHAR = "▌"
_PLACEHOLDER = "●  ●  ●"


def _hhmm() -> str:
    return time.strftime("%I:%M %p").lstrip("0")


def _model_display(model: str) -> str:
    if not model:
        return "Assistant"
    name = model.replace(":", " ").replace("-", " ")
    return name.title()


class _CopyBtn(ctk.CTkButton):
    def __init__(self, master: Any, get_text: Callable[[], str]) -> None:
        super().__init__(
            master,
            text="⎘",
            width=26,
            height=22,
            font=(T.FONT_FAMILY, 10),
            fg_color="transparent",
            hover_color=T.SURFACE_ELEVATED,
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
            self.configure(text="✓", text_color=T.SUCCESS_GREEN)
            self.after(1500, lambda: self.configure(text="⎘", text_color=T.TEXT_MUTED))
        except Exception:
            pass


def _avatar(master: Any, letter: str, color: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        master,
        text=letter,
        width=_AVATAR_SIZE,
        height=_AVATAR_SIZE,
        font=(T.FONT_FAMILY, 12, "bold"),
        fg_color=color,
        text_color="#FFFFFF",
        corner_radius=_AVATAR_SIZE // 2,
    )


class UserDocumentBlock(ctk.CTkFrame):
    """Documentation-style user message — avatar, name, timestamp, body."""

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
        ts = timestamp or _hhmm()

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(0, 16))

        _avatar(row, "U", T.ACCENT_PURPLE).pack(side="left", anchor="n", padx=(0, 10))

        body_col = ctk.CTkFrame(row, fg_color="transparent")
        body_col.pack(side="left", fill="x", expand=True)

        header = ctk.CTkFrame(body_col, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(
            header,
            text="You",
            font=(T.FONT_FAMILY, 12, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            header,
            text=ts,
            font=_META_FONT,
            text_color=T.TEXT_MUTED,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(
            body_col,
            text=text,
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            wraplength=_BODY_WIDTH,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(6, 0), anchor="w")

        bind_inspect_gestures(
            (self, row, body_col),
            get_ref=lambda: self._inspect_ref,
            on_select=on_inspect_select,
            on_navigate=on_inspect_navigate,
        )

    def get_text(self) -> str:
        return self._text


class AssistantDocumentBlock(ctk.CTkFrame):
    """Documentation-style assistant message with streaming and action row."""

    def __init__(
        self,
        master: Any,
        *,
        model_name: str = "",
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
        self._raw_text = ""
        self._model_name = model_name
        self._timestamp = _hhmm()
        self._streaming = False
        self._action_strip: ResponseActionStrip | None = None
        self._artifact_list: ArtifactListView | None = None
        self._artifact_count = 0
        self._execution_id = ""

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(0, 16))

        _avatar(row, "AI", T.ACCENT_BLUE).pack(side="left", anchor="n", padx=(0, 10))

        self._body_col = ctk.CTkFrame(row, fg_color="transparent")
        self._body_col.pack(side="left", fill="x", expand=True)

        header = ctk.CTkFrame(self._body_col, fg_color="transparent")
        header.pack(fill="x")
        self._name_lbl = ctk.CTkLabel(
            header,
            text=_model_display(model_name),
            font=(T.FONT_FAMILY, 12, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._name_lbl.pack(side="left")
        ctk.CTkLabel(
            header,
            text=self._timestamp,
            font=_META_FONT,
            text_color=T.TEXT_MUTED,
        ).pack(side="left", padx=(8, 0))

        self._textbox = ctk.CTkTextbox(
            self._body_col,
            width=_BODY_WIDTH,
            wrap="word",
            font=T.FONT_BODY,
            fg_color="transparent",
            text_color=T.TEXT_PRIMARY,
            border_width=0,
            activate_scrollbars=False,
            height=40,
        )
        self._textbox.pack(fill="x", pady=(6, 0))
        self._textbox.configure(state="normal")
        self._textbox.insert("end", _PLACEHOLDER)
        self._textbox.configure(state="disabled")

        self._actions = ctk.CTkFrame(self._body_col, fg_color="transparent")
        self._actions.pack(fill="x", pady=(6, 0))

        bind_inspect_gestures(
            (self, row, self._body_col),
            get_ref=lambda: self._inspect_ref,
            on_select=self._on_inspect_select,
            on_navigate=self._on_inspect_navigate,
        )

    def append_raw(self, text: str) -> None:
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
        self._streaming = False
        self._raw_text = text
        if model:
            self._model_name = model
            self._name_lbl.configure(text=_model_display(model))
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
        self._build_action_row()
        self._rebuild_action_strip(
            execution_id=execution_id,
            execution_index=execution_index,
            artifact_count=artifact_count,
            decision_count=decision_count,
        )

    def set_artifacts(self, artifacts: Sequence[ArtifactCatalogItem]) -> None:
        catalog = tuple(artifacts)
        count = len(catalog)
        if count == 0 and self._artifact_list is None:
            return
        if self._artifact_list is None:
            self._artifact_list = ArtifactListView(
                self._body_col,
                on_action=self._on_artifact_action,
            )
            self._artifact_list.pack(fill="x", pady=(4, 0), before=self._actions)
        self._artifact_list.set_artifacts(catalog)
        if count != self._artifact_count:
            self._artifact_count = count
            self._rebuild_action_strip(execution_id=self._execution_id, artifact_count=count)

    def get_raw_text(self) -> str:
        return self._raw_text

    def _build_action_row(self) -> None:
        for child in self._actions.winfo_children():
            child.destroy()
        _CopyBtn(self._actions, self.get_raw_text).pack(side="left")
        if self._on_regenerate:
            ctk.CTkButton(
                self._actions,
                text="↺",
                width=26,
                height=22,
                font=(T.FONT_FAMILY, 10),
                fg_color="transparent",
                hover_color=T.SURFACE_ELEVATED,
                text_color=T.TEXT_MUTED,
                corner_radius=4,
                command=self._on_regenerate,
            ).pack(side="left", padx=(4, 0))
        for emoji, rating in (("👍", "up"), ("👎", "down")):
            ctk.CTkButton(
                self._actions,
                text=emoji,
                width=26,
                height=22,
                font=(T.FONT_FAMILY, 10),
                fg_color="transparent",
                hover_color=T.SURFACE_ELEVATED,
                text_color=T.TEXT_MUTED,
                corner_radius=4,
                command=lambda r=rating: self._on_rate(r) if self._on_rate else None,
            ).pack(side="left", padx=(4, 0))

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
            self._body_col,
            execution_id=execution_id,
            execution_index=execution_index,
            artifact_count=artifact_count,
            decision_count=decision_count,
            on_inspect_select=self._on_inspect_select,
            on_inspect_navigate=self._on_inspect_navigate,
        )
        self._action_strip.pack(fill="x", pady=(4, 0))

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
        try:
            lines = int(self._textbox.index("end-1c").split(".")[0])
            h = max(40, min(lines * 20 + 10, 600))
            self._textbox.configure(height=h)
        except Exception:
            pass
