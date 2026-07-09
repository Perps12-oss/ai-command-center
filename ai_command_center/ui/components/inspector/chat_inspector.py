"""ChatInspector — structured chat session inspector panel."""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.components.inspector.base_inspector import BaseInspector
from ai_command_center.ui.design_system import theme_v2 as T

_SECTION_FONT = (T.FONT_FAMILY, 10, "bold")
_LABEL_FONT = (T.FONT_FAMILY, 10)
_VALUE_FONT = (T.FONT_FAMILY, 11)


class ChatInspector(BaseInspector):
    """Default chat inspector: message info, tools, metadata, actions."""

    def __init__(
        self,
        master: Any,
        *,
        on_export: Callable[[], None] | None = None,
        on_pin: Callable[[], None] | None = None,
        on_clear: Callable[[], None] | None = None,
        on_artifact_stub: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.SURFACE_PRIMARY, corner_radius=0, **kwargs)
        self._on_export = on_export
        self._on_pin = on_pin
        self._on_clear = on_clear
        self._on_artifact_stub = on_artifact_stub
        self._session_id = ""
        self._message_id = ""
        self._model = ""
        self._tokens = 0
        self._tools: tuple[str, ...] = ()

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=12, pady=8)

        self._info_section = self._section("Message Information")
        self._model_lbl = self._kv_row(self._info_section, "Model", "—")
        self._created_lbl = self._kv_row(self._info_section, "Created", "—")
        self._tokens_lbl = self._kv_row(self._info_section, "Tokens", "—")

        self._tools_section = self._section("Tools Used")
        self._tools_frame = ctk.CTkFrame(self._tools_section, fg_color="transparent")
        self._tools_frame.pack(fill="x", padx=8, pady=(0, 8))
        self._tools_placeholder = ctk.CTkLabel(
            self._tools_frame,
            text="No tools used",
            font=_LABEL_FONT,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._tools_placeholder.pack(fill="x")

        self._meta_section = self._section("Metadata")
        self._session_row = self._copy_row(self._meta_section, "Session ID", "")
        self._message_row = self._copy_row(self._meta_section, "Message ID", "")

        self._actions_section = self._section("Actions")
        actions = ctk.CTkFrame(self._actions_section, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=(0, 12))

        if on_export:
            ctk.CTkButton(
                actions,
                text="Export Chat",
                height=32,
                font=T.FONT_SMALL,
                fg_color=T.SURFACE_ELEVATED,
                hover_color=T.SURFACE_SECONDARY,
                text_color=T.TEXT_PRIMARY,
                corner_radius=T.BUTTON_RADIUS,
                command=on_export,
            ).pack(fill="x", pady=(0, 6))

        if on_pin:
            ctk.CTkButton(
                actions,
                text="Pin Message",
                height=32,
                font=T.FONT_SMALL,
                fg_color=T.SURFACE_ELEVATED,
                hover_color=T.SURFACE_SECONDARY,
                text_color=T.TEXT_PRIMARY,
                corner_radius=T.BUTTON_RADIUS,
                command=on_pin,
            ).pack(fill="x", pady=(0, 6))

        ctk.CTkButton(
            actions,
            text="Create Artifact",
            height=32,
            font=T.FONT_SMALL,
            fg_color=T.SURFACE_ELEVATED,
            hover_color=T.SURFACE_SECONDARY,
            text_color=T.TEXT_PRIMARY,
            corner_radius=T.BUTTON_RADIUS,
            command=lambda: on_artifact_stub() if on_artifact_stub else None,
        ).pack(fill="x", pady=(0, 6))

        if on_clear:
            ctk.CTkButton(
                actions,
                text="Clear Chat",
                height=32,
                font=T.FONT_SMALL,
                fg_color="transparent",
                hover_color=T.STATUS_ERROR_BG,
                text_color=T.ERROR_RED,
                corner_radius=T.BUTTON_RADIUS,
                command=on_clear,
            ).pack(fill="x")

    def _section(self, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(
            frame,
            text=title,
            font=_SECTION_FONT,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        ).pack(fill="x", padx=4, pady=(0, 4))
        body = ctk.CTkFrame(
            frame,
            fg_color=T.SURFACE_ELEVATED,
            corner_radius=T.CARD_RADIUS,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
        )
        body.pack(fill="x")
        return body

    def _kv_row(self, parent: ctk.CTkFrame, key: str, value: str) -> ctk.CTkLabel:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(
            row,
            text=key,
            font=_LABEL_FONT,
            text_color=T.TEXT_MUTED,
            width=70,
            anchor="w",
        ).pack(side="left")
        val = ctk.CTkLabel(
            row,
            text=value,
            font=_VALUE_FONT,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        val.pack(side="left", fill="x", expand=True)
        return val

    def _copy_row(self, parent: ctk.CTkFrame, key: str, value: str) -> ctk.CTkFrame:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(
            row,
            text=key,
            font=_LABEL_FONT,
            text_color=T.TEXT_MUTED,
            width=80,
            anchor="w",
        ).pack(side="left")
        val_lbl = ctk.CTkLabel(
            row,
            text=value or "—",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        val_lbl.pack(side="left", fill="x", expand=True)

        def _copy() -> None:
            try:
                self.clipboard_clear()
                self.clipboard_append(value)
            except Exception:
                pass

        ctk.CTkButton(
            row,
            text="⎘",
            width=24,
            height=22,
            font=(T.FONT_FAMILY, 10),
            fg_color="transparent",
            hover_color=T.SURFACE_SECONDARY,
            text_color=T.TEXT_MUTED,
            corner_radius=4,
            command=_copy,
        ).pack(side="right")
        row._value_lbl = val_lbl  # type: ignore[attr-defined]
        return row

    def update_session(
        self,
        *,
        session_id: str = "",
        message_id: str = "",
        model: str = "",
        tokens: int = 0,
        tools: tuple[str, ...] = (),
        created_ts: float | None = None,
    ) -> None:
        self._session_id = session_id
        self._message_id = message_id
        self._model = model
        self._tokens = tokens
        self._tools = tools

        self._model_lbl.configure(text=model or "—")
        if created_ts:
            created = time.strftime("%b %d, %Y %I:%M %p", time.localtime(created_ts)).lstrip("0")
        else:
            created = time.strftime("%b %d, %Y %I:%M %p", time.localtime()).lstrip("0")
        self._created_lbl.configure(text=created)
        self._tokens_lbl.configure(text=f"~{tokens}" if tokens else "—")

        self._session_row._value_lbl.configure(  # type: ignore[attr-defined]
            text=(session_id[:16] + "…") if len(session_id) > 16 else (session_id or "—")
        )
        self._message_row._value_lbl.configure(  # type: ignore[attr-defined]
            text=(message_id[:16] + "…") if len(message_id) > 16 else (message_id or "—")
        )

        for child in self._tools_frame.winfo_children():
            child.destroy()
        if tools:
            badge_row = ctk.CTkFrame(self._tools_frame, fg_color="transparent")
            badge_row.pack(fill="x", padx=8, pady=8)
            for tool in tools:
                ctk.CTkLabel(
                    badge_row,
                    text=tool,
                    font=(T.FONT_FAMILY, 9),
                    fg_color=T.SURFACE_SECONDARY,
                    text_color=T.ACCENT_BLUE,
                    corner_radius=8,
                    width=60,
                    height=22,
                ).pack(side="left", padx=(0, 4))
        else:
            ctk.CTkLabel(
                self._tools_frame,
                text="No tools used",
                font=_LABEL_FONT,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=8, pady=8)

    def update_context(self, context: Any) -> None:
        """Project ExecutionContext into chat inspector fields."""
        model = str(getattr(context, "model", "") or "")
        request_id = str(getattr(context, "request_id", "") or "")
        session_id = str(getattr(context, "session_id", "") or "")
        tokens = int(getattr(context, "token_count", 0) or 0)
        tools: list[str] = []
        for run in getattr(context, "tool_runs", ()) or ():
            name = getattr(run, "tool_name", None) or getattr(run, "name", None)
            if name:
                tools.append(str(name))
        self.update_session(
            session_id=session_id,
            message_id=request_id,
            model=model,
            tokens=tokens,
            tools=tuple(tools),
        )


__all__ = ["ChatInspector"]
