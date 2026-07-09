"""WorkspaceInspector — conversation workspace panel for the chat right rail."""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.inspector.base_inspector import BaseInspector
from ai_command_center.ui.design_system import theme_v2 as T

_SECTION_FONT = (T.FONT_FAMILY, 10, "bold")
_LABEL_FONT = (T.FONT_FAMILY, 10)
_VALUE_FONT = (T.FONT_FAMILY, 11)


class ChatInspector(BaseInspector):
    """Workspace inspector: conversation stats, workspace objects, actions."""

    def __init__(
        self,
        master: Any,
        *,
        on_export: Callable[[], None] | None = None,
        on_pin: Callable[[], None] | None = None,
        on_clear: Callable[[], None] | None = None,
        on_copy_message: Callable[[], None] | None = None,
        on_create_note: Callable[[], None] | None = None,
        on_artifact_stub: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.SURFACE_PRIMARY, corner_radius=0, **kwargs)
        self._on_export = on_export
        self._on_pin = on_pin
        self._on_clear = on_clear
        self._on_copy_message = on_copy_message
        self._on_create_note = on_create_note
        self._on_artifact_stub = on_artifact_stub
        self._selected_content = ""

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=12, pady=8)

        convo = self._section("Conversation")
        self._messages_lbl = self._stat_row(convo, "Messages", "0")
        self._model_lbl = self._stat_row(convo, "Model", "—")
        self._tokens_lbl = self._stat_row(convo, "Tokens", "—")
        self._created_lbl = self._stat_row(convo, "Created", "—")

        artifacts = self._section("Artifacts")
        self._artifacts_frame = ctk.CTkFrame(artifacts, fg_color="transparent")
        self._artifacts_frame.pack(fill="x", padx=8, pady=8)
        self._artifacts_count = ctk.CTkLabel(
            self._artifacts_frame,
            text="0",
            font=_VALUE_FONT,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._artifacts_count.pack(fill="x")

        notes = self._section("Notes")
        self._notes_lbl = ctk.CTkLabel(
            notes,
            text="0",
            font=_VALUE_FONT,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._notes_lbl.pack(fill="x", padx=10, pady=8)

        exec_sec = self._section("Executions")
        self._exec_lbl = ctk.CTkLabel(
            exec_sec,
            text="0",
            font=_VALUE_FONT,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._exec_lbl.pack(fill="x", padx=10, pady=8)

        tools_sec = self._section("Tools Used")
        self._tools_frame = ctk.CTkFrame(tools_sec, fg_color="transparent")
        self._tools_frame.pack(fill="x", padx=8, pady=8)

        actions = self._section("Actions")
        btn_frame = ctk.CTkFrame(actions, fg_color="transparent")
        btn_frame.pack(fill="x", padx=8, pady=(0, 12))

        for label, cmd, danger in (
            ("Copy Message", on_copy_message, False),
            ("Export Chat", on_export, False),
            ("Create Note", on_create_note, False),
            ("Create Artifact", on_artifact_stub, False),
            ("Pin", on_pin, False),
            ("Clear Chat", on_clear, True),
        ):
            if not cmd:
                continue
            ctk.CTkButton(
                btn_frame,
                text=label,
                height=30,
                font=T.FONT_SMALL,
                fg_color="transparent" if danger else T.SURFACE_ELEVATED,
                hover_color=T.STATUS_ERROR_BG if danger else T.SURFACE_SECONDARY,
                text_color=T.ERROR_RED if danger else T.TEXT_PRIMARY,
                corner_radius=T.BUTTON_RADIUS,
                command=cmd,
            ).pack(fill="x", pady=(0, 4))

    def _section(self, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame.pack(fill="x", pady=(6, 0))
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

    def _stat_row(self, parent: ctk.CTkFrame, key: str, value: str) -> ctk.CTkLabel:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(
            row,
            text=key,
            font=_LABEL_FONT,
            text_color=T.TEXT_MUTED,
            width=72,
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

    def update_session(
        self,
        *,
        session_id: str = "",
        message_id: str = "",
        model: str = "",
        tokens: int = 0,
        message_count: int = 0,
        tools: tuple[str, ...] = (),
        artifacts: tuple[str, ...] = (),
        notes_count: int = 0,
        executions_count: int = 0,
        created_ts: float | None = None,
        selected_content: str = "",
    ) -> None:
        del session_id, message_id
        self._selected_content = selected_content
        self._messages_lbl.configure(text=str(message_count))
        self._model_lbl.configure(text=model or "—")
        self._tokens_lbl.configure(text=f"~{tokens}" if tokens else "—")
        if created_ts:
            created = time.strftime("%I:%M %p", time.localtime(created_ts)).lstrip("0")
        else:
            created = time.strftime("%I:%M %p", time.localtime()).lstrip("0")
        self._created_lbl.configure(text=created)

        for child in self._artifacts_frame.winfo_children():
            child.destroy()
        if artifacts:
            self._artifacts_count = ctk.CTkLabel(
                self._artifacts_frame,
                text=str(len(artifacts)),
                font=_VALUE_FONT,
                text_color=T.TEXT_PRIMARY,
                anchor="w",
            )
            self._artifacts_count.pack(fill="x")
            for name in artifacts[:6]:
                ctk.CTkLabel(
                    self._artifacts_frame,
                    text=f"· {name}",
                    font=_LABEL_FONT,
                    text_color=T.TEXT_SECONDARY,
                    anchor="w",
                ).pack(fill="x", pady=1)
        else:
            ctk.CTkLabel(
                self._artifacts_frame,
                text="0",
                font=_VALUE_FONT,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x")

        self._notes_lbl.configure(text=str(notes_count))
        self._exec_lbl.configure(text=str(executions_count))

        for child in self._tools_frame.winfo_children():
            child.destroy()
        if tools:
            row = ctk.CTkFrame(self._tools_frame, fg_color="transparent")
            row.pack(fill="x")
            for tool in tools:
                ctk.CTkLabel(
                    row,
                    text=tool,
                    font=(T.FONT_FAMILY, 9),
                    fg_color=T.SURFACE_SECONDARY,
                    text_color=T.ACCENT_BLUE,
                    corner_radius=8,
                    height=22,
                ).pack(side="left", padx=(0, 4), pady=2)
        else:
            ctk.CTkLabel(
                self._tools_frame,
                text="None",
                font=_LABEL_FONT,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x")

    def update_selected_message(self, ref: InspectableRef) -> None:
        content = ""
        for key in ("content", "text", "body"):
            val = ref.get(key)
            if val:
                content = val
                break
        index_raw = ref.get("index", "0")
        try:
            message_count = int(index_raw) + 1
        except ValueError:
            message_count = 0
        self.update_session(
            selected_content=content,
            message_count=message_count,
        )

    def update_context(self, context: Any) -> None:
        model = str(getattr(context, "model", "") or "")
        tokens = int(getattr(context, "token_count", 0) or 0)
        tools: list[str] = []
        for run in getattr(context, "tool_runs", ()) or ():
            name = getattr(run, "tool_name", None) or getattr(run, "name", None)
            if name:
                tools.append(str(name))
        artifacts: list[str] = []
        for art in getattr(context, "artifacts", ()) or ():
            title = getattr(art, "title", None) or getattr(art, "name", None) or getattr(art, "artifact_id", "")
            if title:
                artifacts.append(str(title))
        self.update_session(
            model=model,
            tokens=tokens,
            tools=tuple(tools),
            artifacts=tuple(artifacts),
            executions_count=1 if getattr(context, "request_id", "") else 0,
        )

    def get_selected_content(self) -> str:
        return self._selected_content


__all__ = ["ChatInspector"]
