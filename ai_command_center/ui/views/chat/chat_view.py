"""Chat view — premium minimalist messaging UI, consumer-facing only."""
from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.chat_history_panel import ChatHistoryPanel
from ai_command_center.ui.components.inspector.execution_inspector import ExecutionInspector
from ai_command_center.ui.components.inspector.inspector_host import InspectorHost
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.chat.chat_header import ChatHeader
from ai_command_center.ui.views.chat.chat_input import InputPill, TemplatesOverlay
from ai_command_center.ui.views.chat.chat_search import ChatSearchController
from ai_command_center.ui.views.chat.chat_workspace_layout import make_chat_workspace_layout
from ai_command_center.ui.views.chat.conversation_list import ConversationList
from ai_command_center.ui.views.chat.message_block import AssistantMessageBlock, UserMessageBlock
from ai_command_center.ui.views.chat.session_store import SessionStore, hhmm, session_title
from ai_command_center.ui.views.chat.stream_renderer import (
    CLR_META,
    CLR_REGEN,
    SIDE_PAD,
    AssistantBubble,
    CopyBtn,
    EmptyState,
    SystemStrip,
    UserBubble,
)
from ai_command_center.ui.widget_utils import clear_children


class _SessionBar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_export:         Callable | None,
        on_toggle_history: Callable,
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, height=40)
        self.pack_propagate(False)

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
            text_color=CLR_META,
        )
        self._count_lbl.pack(side="left", padx=(6, 0), pady=9)

        self._entity_lbl = ctk.CTkLabel(
            self,
            text="",
            font=(T.FONT_FAMILY, 10),
            text_color=T.ACCENT_DEFAULT,
            anchor="w",
        )
        self._entity_lbl.pack(side="left", padx=(8, 0), pady=9)

        if on_export:
            ctk.CTkButton(
                self,
                text="⬇ Export",
                width=72, height=24,
                font=(T.FONT_FAMILY, 10),
                fg_color=T.BG_GLASS,
                hover_color=T.BG_GLASS_BORDER,
                text_color=CLR_META,
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

    def update_entity(self, entity_type: str, title: str) -> None:
        if entity_type and title:
            icon = {"workspace": "◈", "card": "▢", "resource": "🔗"}.get(entity_type, "•")
            self._entity_lbl.configure(text=f"{icon}  {entity_type.title()}: {title}")
        else:
            self._entity_lbl.configure(text="")


class ChatView(ctk.CTkFrame):
    """Consumer-facing streaming chat.

    Architecture contract
    ─────────────────────
    • Data arrives only via the public methods below (UIQueue → main thread).
    • No EventBus, service, or backend imports.
    • No developer logs, pipeline paths, or system telemetry.
    • The view does NOT manage session persistence beyond the current conversation.
    """

    def __init__(
        self,
        master,
        on_cancel:     Callable,
        on_export:     Callable[[list[dict]], None] | None = None,
        on_regenerate: Callable[[], None]            | None = None,
        on_send:       Callable[[str], None]         | None = None,
        on_new_session: Callable[[], None]           | None = None,
        on_inspect_select: Callable[[InspectableRef], None] | None = None,
        on_inspect_navigate: Callable[[InspectableRef], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_cancel     = on_cancel
        self._on_export     = on_export
        self._on_regenerate = on_regenerate
        self._on_send       = on_send
        self._on_new_session = on_new_session
        self._on_inspect_select = on_inspect_select
        self._on_inspect_navigate = on_inspect_navigate

        self._request_id:       str | None              = None
        self._streaming:        bool                    = False
        self._streaming_bubble: AssistantBubble | None = None
        self._chunk_buffer:     str                     = ""
        self._flush_pending:    bool                    = False
        self._model:            str                     = ""
        self._entity_type:      str                     = ""
        self._entity_title:     str                     = ""

        self._store = SessionStore()
        self._history_open:     bool                    = True
        self._docking = False
        self._chat_header: ChatHeader | None = None
        self._conversation_list: ConversationList | None = None
        self._execution_inspector: ExecutionInspector | None = None
        self._inspector_host: InspectorHost | None = None
        self._use_v2_blocks = False
        self._session_bar: _SessionBar | None = None
        self._execution_context: Any = None

        self._build()

    @property
    def _history(self) -> list[dict]:
        return self._store.history

    @_history.setter
    def _history(self, value: list[dict]) -> None:
        self._store.set_history(value)

    def _build(self) -> None:
        self._workspace = make_chat_workspace_layout(self)
        self._docking = self._workspace._docking_enabled
        self._use_v2_blocks = self._docking

        if self._docking:
            self._build_docked()
            return
        self._build_legacy()

    def _build_docked(self) -> None:
        self._workspace.pack(fill="both", expand=True)

        self._conversation_list = ConversationList(
            self._workspace.left_host(),
            on_new=self._new_session,
            on_select=self._load_session,
            on_delete=self._delete_session,
        )
        self._workspace.set_left(self._conversation_list)

        center = ctk.CTkFrame(self._workspace.center_host(), fg_color="transparent")
        center.pack(fill="both", expand=True)

        self._chat_header = ChatHeader(
            center,
            on_rename=self._rename_conversation,
            on_export=self._handle_export,
            on_pin=self._toggle_pin,
            on_archive=self._toggle_archive,
        )
        self._chat_header.pack(fill="x", side="top")

        self._scroll = ctk.CTkScrollableFrame(
            center, fg_color=T.BG_DEEP, corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True)
        self._scroll.columnconfigure(0, weight=1)

        ctx_frame = ctk.CTkFrame(center, fg_color="transparent")
        ctx_frame.pack(fill="x", side="bottom", padx=16, pady=(0, 4))
        self._context_bar = ctk.CTkLabel(
            ctx_frame,
            text="Sources: — · Tokens: —",
            font=(T.FONT_FAMILY, 10),
            text_color=CLR_META,
            anchor="w",
        )
        self._context_bar.pack(side="left", fill="x", expand=True)
        self._token_bar = ctk.CTkProgressBar(
            ctx_frame,
            width=120,
            height=4,
            corner_radius=2,
            fg_color=T.BG_GLASS,
            progress_color=T.STATUS_READY,
        )
        self._token_bar.set(0)
        self._token_bar.pack(side="right", padx=(8, 0))

        self._pill = InputPill(
            center,
            on_send=self._on_send,
            on_stop=self._handle_stop,
        )
        self._pill.pack(fill="x", side="bottom")
        self._templates_overlay = TemplatesOverlay(self, on_select=self._pill.insert_template)
        self._pill.set_templates_overlay(self._templates_overlay)

        self._empty = EmptyState(self._scroll)
        self._empty.pack(fill="both", expand=True, pady=30)

        self._execution_inspector = ExecutionInspector(self._workspace.right_host())
        self._inspector_host = InspectorHost(self._workspace.right_host())
        self._inspector_host.register("execution", self._execution_inspector)
        self._inspector_host.set_default(self._execution_inspector)
        self._workspace.set_right(self._inspector_host)

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

        canvas = self._scroll._parent_canvas
        for event in ("<MouseWheel>", "<Button-4>", "<Button-5>", "<Configure>"):
            canvas.bind(event, self._on_canvas_scroll, add="+")

        self._search = ChatSearchController(
            self,
            self._chat_header,
            self._scroll,
            get_history=lambda: self._history,
        )
        root = self.winfo_toplevel()
        self._search.bind_shortcuts(root)
        self._refresh_session_bar()

    def _build_legacy(self) -> None:
        self._session_bar = _SessionBar(
            self,
            on_export=self._handle_export,
            on_toggle_history=self._toggle_history,
        )
        self._session_bar.pack(fill="x", side="top")

        ctx_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctx_frame.pack(fill="x", side="bottom", padx=16, pady=(0, 4))

        self._context_bar = ctk.CTkLabel(
            ctx_frame,
            text="Sources: — · Tokens: —",
            font=(T.FONT_FAMILY, 10),
            text_color=CLR_META,
            anchor="w",
        )
        self._context_bar.pack(side="left", fill="x", expand=True)

        self._token_bar = ctk.CTkProgressBar(
            ctx_frame,
            width=120,
            height=4,
            corner_radius=2,
            fg_color=T.BG_GLASS,
            progress_color=T.STATUS_READY,
        )
        self._token_bar.set(0)
        self._token_bar.pack(side="right", padx=(8, 0))

        self._pill = InputPill(
            self,
            on_send=self._on_send,
            on_stop=self._handle_stop,
        )
        self._pill.pack(fill="x", side="bottom")

        self._templates_overlay = TemplatesOverlay(self, on_select=self._pill.insert_template)
        self._pill.set_templates_overlay(self._templates_overlay)

        middle = ctk.CTkFrame(self, fg_color="transparent")
        middle.pack(fill="both", expand=True)

        self._history_panel = ChatHistoryPanel(
            middle,
            on_new=self._new_session,
            on_select=self._load_session,
            on_delete=self._delete_session,
        )
        self._history_panel.pack(fill="y", side="left")

        self._divider = ctk.CTkFrame(middle, width=1, fg_color=T.BG_GLASS_BORDER)
        self._divider.pack(fill="y", side="left")

        self._scroll = ctk.CTkScrollableFrame(
            middle, fg_color=T.BG_DEEP, corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True)
        self._scroll.columnconfigure(0, weight=1)

        self._empty = EmptyState(self._scroll)
        self._empty.pack(fill="both", expand=True, pady=30)

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

        canvas = self._scroll._parent_canvas
        for event in ("<MouseWheel>", "<Button-4>", "<Button-5>", "<Configure>"):
            canvas.bind(event, self._on_canvas_scroll, add="+")

        self._search = ChatSearchController(
            self,
            self._session_bar,
            self._scroll,
            get_history=lambda: self._history,
        )
        root = self.winfo_toplevel()
        self._search.bind_shortcuts(root)

        self._refresh_session_bar()

    def _rename_conversation(self, title: str) -> None:
        meta = self._store.ensure_metadata(self._store.session_id, title=title)
        if self._conversation_list:
            self._conversation_list.update_conversation(meta)

    def _toggle_pin(self) -> None:
        meta = self._store.ensure_metadata(self._store.session_id)
        meta.pinned = not meta.pinned
        if self._conversation_list:
            self._conversation_list.update_conversation(meta)
        if self._chat_header:
            self._chat_header.set_pinned(meta.pinned)

    def _toggle_archive(self) -> None:
        meta = self._store.ensure_metadata(self._store.session_id)
        meta.archived = not meta.archived
        if self._conversation_list:
            self._conversation_list.update_conversation(meta)

    def update_inspector(self, context) -> None:
        self._execution_context = context
        if self._execution_inspector is not None:
            self._execution_inspector.update_context(context)

    def show_inspector(self, ref: InspectableRef) -> None:
        if self._inspector_host is not None:
            self._inspector_host.show(ref)

    def clear_inspector(self) -> None:
        if self._inspector_host is not None:
            self._inspector_host.clear()

    def update_chat_execution_status(
        self, status: str, provider: str, model: str
    ) -> None:
        if self._chat_header is not None:
            self._chat_header.update_status(status)
            self._chat_header.update_provider(provider, model)

    def _sync_conversation_item(self, sid: str, title: str, *, is_new: bool) -> None:
        if self._conversation_list is None:
            return
        badge = self._model.split("/")[0] if self._model else ""
        meta = self._store.ensure_metadata(sid, title=title, provider_badge=badge)
        if is_new:
            self._conversation_list.add_conversation(meta)
        else:
            self._conversation_list.update_conversation(meta)
        self._conversation_list.set_active(sid)

    def _toggle_history(self) -> None:
        if self._history_panel is None:
            return
        self._history_open = not self._history_open
        if self._history_open:
            self._scroll.pack_forget()
            self._divider.pack_forget()
            self._history_panel.pack(fill="y", side="left")
            self._divider.pack(fill="y", side="left")
            self._scroll.pack(fill="both", expand=True)
        else:
            self._history_panel.pack_forget()
        self._refresh_session_bar()

    def _save_current_session(self) -> None:
        self._store.save_current_session(
            on_update=lambda s, t, ts: self._on_session_saved(s, t, ts, existed=True),
            on_add=lambda s, t, ts: self._on_session_saved(s, t, ts, existed=False),
        )

    def _on_session_saved(self, sid: str, title: str, _ts: str, *, existed: bool) -> None:
        if self._conversation_list is not None:
            self._sync_conversation_item(sid, title, is_new=not existed)
            return
        if self._history_panel is None:
            return
        if existed:
            self._history_panel.update_session(sid, title, _ts)
        else:
            self._history_panel.add_session(sid, title, _ts, active=False)

    def _new_session(self) -> None:
        if self._on_new_session:
            self._on_new_session()
            return
        self._save_current_session()
        self._store.start_new_session()
        self._clear_ui()
        self._refresh_session_bar()

    def reset_local_session(self) -> None:
        """Reset in-memory session UI after bus-driven new-session events."""
        self._save_current_session()
        self._store.start_new_session()
        self._clear_ui()
        self._refresh_session_bar()

    def _load_session(self, sid: str) -> None:
        self._save_current_session()
        messages = self._store.load_session(sid)
        if self._conversation_list is not None:
            self._conversation_list.set_active(sid)
        elif self._history_panel is not None:
            self._history_panel.set_active(sid)
        self._clear_ui()
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
        was_active = self._store.delete_session(sid)
        if self._conversation_list is not None:
            self._conversation_list.remove_conversation(sid)
        elif self._history_panel is not None:
            self._history_panel.remove_session(sid)
        if was_active:
            self._new_session()

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

    def _refresh_session_bar(self) -> None:
        count = len(self._history)
        title = session_title(self._history) or "New Chat"
        if self._chat_header is not None:
            self._chat_header.update_title(title)
            self._chat_header.update_model(self._model)
            meta = self._store.get_metadata(self._store.session_id)
            if meta:
                self._chat_header.set_pinned(meta.pinned)
        elif self._session_bar is not None:
            self._session_bar.update(self._model, count, self._history_open)
            self._session_bar.update_entity(self._entity_type, self._entity_title)

    def _hide_empty(self) -> None:
        if self._empty.winfo_ismapped():
            self._empty.pack_forget()

    def _make_message_ref(
        self,
        role: str,
        content: str,
        *,
        request_id: str = "",
        message_index: int | None = None,
    ) -> InspectableRef:
        preview = content.strip().splitlines()[0][:60] if content.strip() else f"{role.title()} message"
        payload: dict[str, str] = {
            "role": role,
            "content": content,
        }
        if request_id:
            payload["request_id"] = request_id
        if message_index is not None:
            payload["index"] = str(message_index)
        return InspectableRef.from_payload(
            {
                "kind": "message",
                "ref_id": request_id or f"{self._store.session_id}:{role}:{message_index if message_index is not None else len(self._history)}",
                "label": preview,
                "payload": payload,
            }
        )

    def _user_row(self, text: str, *, message_index: int | None = None) -> None:
        self._hide_empty()
        if self._use_v2_blocks:
            ref = self._make_message_ref("user", text, message_index=message_index)
            UserMessageBlock(
                self._scroll,
                text,
                inspect_ref=ref,
                on_inspect_select=self._on_inspect_select,
                on_inspect_navigate=self._on_inspect_navigate,
            ).pack(
                fill="x", padx=SIDE_PAD, pady=(0, 8)
            )
            return
        outer = ctk.CTkFrame(self._scroll, fg_color="transparent")
        outer.pack(fill="x", padx=SIDE_PAD, pady=(0, 4))

        brow = ctk.CTkFrame(outer, fg_color="transparent")
        brow.pack(fill="x")
        ctk.CTkFrame(brow, fg_color="transparent").pack(side="left", fill="x", expand=True)
        UserBubble(brow, text).pack(side="right", anchor="e")

        mrow = ctk.CTkFrame(outer, fg_color="transparent")
        mrow.pack(fill="x", pady=(3, 10))
        ctk.CTkFrame(mrow, fg_color="transparent").pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            mrow,
            text=hhmm(),
            font=(T.FONT_FAMILY, 9),
            text_color=CLR_META,
        ).pack(side="right", padx=(0, 4))
        CopyBtn(mrow, lambda t=text: t).pack(side="right")

    def _assistant_row(self, *, message_index: int | None = None) -> AssistantBubble | AssistantMessageBlock:
        self._hide_empty()
        if self._use_v2_blocks:
            ref = self._make_message_ref(
                "assistant",
                self._chunk_buffer or "",
                request_id=self._request_id or "",
                message_index=message_index,
            )
            block = AssistantMessageBlock(
                self._scroll,
                on_regenerate=self._on_regenerate,
                on_rate=lambda rating: None,
                inspect_ref=ref,
                on_inspect_select=self._on_inspect_select,
                on_inspect_navigate=self._on_inspect_navigate,
            )
            block.pack(fill="x", padx=SIDE_PAD, pady=(0, 4))
            return block
        outer = ctk.CTkFrame(self._scroll, fg_color="transparent")
        outer.pack(fill="x", padx=SIDE_PAD, pady=(0, 4))

        brow = ctk.CTkFrame(outer, fg_color="transparent")
        brow.pack(fill="x")
        bubble = AssistantBubble(brow)
        bubble.pack(side="left", anchor="w")
        bubble._outer = outer
        bubble._timestamp = hhmm()
        ctk.CTkFrame(brow, fg_color="transparent").pack(side="right", fill="x", expand=True)

        return bubble

    def _finalize_meta(self, bubble: AssistantBubble | AssistantMessageBlock) -> None:
        if isinstance(bubble, AssistantMessageBlock):
            execution_id = self._request_id or ""
            artifact_count = 0
            decision_count = 0
            if self._execution_context is not None:
                artifact_count = len(
                    getattr(self._execution_context, "artifacts", ()) or ()
                )
            bubble.finalize(
                bubble.get_raw_text(),
                model=self._model,
                tokens=int(len(bubble.get_raw_text()) / 4),
                execution_id=execution_id,
                artifact_count=artifact_count,
                decision_count=decision_count,
            )
            return
        outer = getattr(bubble, "_outer", None)
        if outer is None:
            return
        timestamp = getattr(bubble, "_timestamp", hhmm())

        mrow = ctk.CTkFrame(outer, fg_color="transparent")
        mrow.pack(fill="x", pady=(3, 10))

        CopyBtn(mrow, bubble.get_raw_text).pack(side="left")
        ctk.CTkLabel(
            mrow,
            text=timestamp,
            font=(T.FONT_FAMILY, 9),
            text_color=CLR_META,
        ).pack(side="left", padx=(4, 0))

        if self._on_regenerate:
            ctk.CTkButton(
                mrow,
                text="↺ Regenerate",
                width=82, height=18,
                font=(T.FONT_FAMILY, 9),
                fg_color="transparent",
                hover_color=T.BG_GLASS,
                text_color=CLR_REGEN,
                corner_radius=4,
                command=self._on_regenerate,
            ).pack(side="left", padx=(10, 0))

        for emoji, rating in (("👍", "up"), ("👎", "down")):
            btn = ctk.CTkButton(
                mrow,
                text=emoji,
                width=24, height=18,
                font=(T.FONT_FAMILY, 10),
                fg_color="transparent",
                hover_color=T.BG_GLASS,
                text_color=CLR_META,
                corner_radius=4,
                command=lambda r=rating, b=bubble: self._rate_message(b, r),
            )
            btn.pack(side="right", padx=(2, 0))

    def _rate_message(self, bubble: AssistantBubble, rating: str) -> None:
        color = T.STATUS_READY if rating == "up" else T.STATUS_ERROR
        try:
            bubble.configure(border_width=1, border_color=color)
        except Exception:
            pass
        if self._on_send:
            snippet = bubble.get_raw_text()[:60].replace("\n", " ")
            self._on_send(f".rating:{rating} \"{snippet}\"")

    def set_model(self, name: str) -> None:
        self._model = name
        self._refresh_session_bar()

    def update_entity_context(self, entity_id: str, entity_type: str, title: str) -> None:
        if entity_id:
            self._entity_type = entity_type
            self._entity_title = title
        else:
            self._entity_type = ""
            self._entity_title = ""
        self._refresh_session_bar()
        if self._chat_header is not None and title:
            current = session_title(self._history) or title
            self._chat_header.update_title(current)

    def focus_input(self) -> None:
        self._pill.focus_input()

    _TOKEN_BUDGET = 4096

    def update_context_bar(self, sources: list[str], tokens: int) -> None:
        if not sources:
            self._context_bar.configure(text=f"Sources: — · Tokens: {tokens}")
        else:
            names = [s.split("_")[-1].split("/")[-1][:18] for s in sources]
            summary = ", ".join(names)
            if len(summary) > 50:
                summary = summary[:47] + "…"
            self._context_bar.configure(text=f"Sources: {summary} · Tokens: {tokens}")
        frac = min(1.0, tokens / self._TOKEN_BUDGET) if tokens > 0 else 0.0
        if frac >= 0.85:
            color = T.STATUS_ERROR
        elif frac >= 0.6:
            color = T.STATUS_BUSY
        else:
            color = T.STATUS_READY
        self._token_bar.configure(progress_color=color)
        self._token_bar.set(frac)

    def load_history(self, messages: list[dict]) -> None:
        self._clear_ui()
        self._history = list(messages)
        for index, item in enumerate(messages):
            role    = str(item.get("role", ""))
            content = str(item.get("content", ""))
            if role == "user":
                self._user_row(content, message_index=index)
            elif role == "assistant":
                b = self._assistant_row(message_index=index)
                b.finalize(content)
                self._finalize_meta(b)
        self._refresh_session_bar()
        self._scroll_to_bottom()

    def show_user_message(self, text: str) -> None:
        self._store.append_message("user", text)
        self._user_row(text, message_index=len(self._history) - 1)
        self._refresh_session_bar()
        self._scroll_to_bottom()

    def begin_assistant(self, request_id: str) -> None:
        self._request_id   = request_id
        self._streaming    = True
        self._chunk_buffer = ""
        self._streaming_bubble = self._assistant_row(message_index=len(self._history))
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
        self._store.append_message("assistant", text)
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

    def _flush_chunks(self) -> None:
        self._flush_pending = False
        if self._chunk_buffer and self._streaming_bubble:
            self._streaming_bubble.append_raw(self._chunk_buffer)
            self._chunk_buffer = ""
            self._scroll_to_bottom()

    def _add_strip(self, kind: str, label: str, body: str) -> None:
        SystemStrip(self._scroll, kind, label, body).pack(
            fill="x", padx=SIDE_PAD + 4, pady=(0, 4)
        )

    def _clear_ui(self) -> None:
        clear_children(self._scroll)
        self._streaming_bubble = None
        self._streaming = False
        self._empty = EmptyState(self._scroll)
        self._empty.pack(fill="both", expand=True, pady=30)

    def _clear_history(self) -> None:
        self._store.clear_history()

    def _reset_conversation(self) -> None:
        self._clear_ui()
        self._clear_history()

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
