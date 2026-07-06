"""Workspace OS Inspector — minimal UI for the walking skeleton workflow."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import (
    EVENT_TIMELINE_EVENT,
    EventBus,
)
from ai_command_center.core.events.topics import ENTITY_CREATED
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.ui_queue import UIQueue
from ai_command_center.ui.workspace_os_controller import WorkspaceOsUIController


class WorkspaceOsInspector(ctk.CTkToplevel):
    """
    Minimal Workspace OS inspector window.

    Displays live stats, recent activity, and provides entity creation.
    Reads all state from AppStateStore; publishes intents via EventBus.
    Opened via Ctrl+Shift+W.
    """

    WIDTH = 700
    HEIGHT = 700

    def __init__(
        self,
        master: ctk.CTk,
        bus: EventBus,
        state_store: AppStateStore,
        *,
        ui_queue: UIQueue,
    ) -> None:
        super().__init__(master)
        self._bus = bus
        self._state_store = state_store
        self._ui_queue = ui_queue
        self._controller = WorkspaceOsUIController(bus)
        self._unsubs: list = []

        self.title("Workspace OS Inspector")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.configure(fg_color=("#f5f5f5", "#1a1a1a"))
        self.resizable(True, True)

        self._build_layout()
        self._wire_events()
        self._refresh()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.transient(master)
        self.focus_set()
        self.grab_set()

    def _build_layout(self) -> None:
        """Build the inspector layout."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="Workspace OS",
            font=T.FONT_TITLE,
            text_color=T.TEXT_HEADING,
        )
        header.pack(pady=(16, 8))

        status = ctk.CTkLabel(
            self,
            text="Experimental",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        )
        status.pack()

        # Stats row
        stats_frame = ctk.CTkFrame(self)
        stats_frame.pack(fill="x", padx=16, pady=8)

        self._entities_label = ctk.CTkLabel(stats_frame, text="Entities: -")
        self._entities_label.grid(row=0, column=0, padx=16, pady=8)
        self._relationships_label = ctk.CTkLabel(stats_frame, text="Relationships: -")
        self._relationships_label.grid(row=0, column=1, padx=16, pady=8)
        self._actions_label = ctk.CTkLabel(stats_frame, text="Actions: -")
        self._actions_label.grid(row=0, column=2, padx=16, pady=8)
        self._events_label = ctk.CTkLabel(stats_frame, text="Events: -")
        self._events_label.grid(row=0, column=3, padx=16, pady=8)

        # Creation buttons
        create_frame = ctk.CTkFrame(self)
        create_frame.pack(fill="x", padx=16, pady=8)

        ctk.CTkButton(
            create_frame,
            text="+ Workspace",
            command=self._show_create_workspace,
        ).grid(row=0, column=0, padx=8, pady=8)
        ctk.CTkButton(
            create_frame,
            text="+ Card",
            command=self._show_create_card,
        ).grid(row=0, column=1, padx=8, pady=8)
        ctk.CTkButton(
            create_frame,
            text="+ Resource",
            command=self._show_create_resource,
        ).grid(row=0, column=2, padx=8, pady=8)

        # Search
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=16, pady=8)
        self._search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search entities...")
        self._search_entry.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        ctk.CTkButton(
            search_frame,
            text="Search",
            command=self._on_search,
        ).pack(side="right", padx=8, pady=8)
        self._search_entry.bind("<Return>", lambda _event: self._on_search())

        # Entities list
        self._entities_list = ctk.CTkTextbox(self, wrap="word")
        self._entities_list.pack(fill="both", expand=True, padx=16, pady=8)
        self._entities_list.configure(state="disabled")

        # Recent activity
        activity_label = ctk.CTkLabel(self, text="Recent Activity", font=T.FONT_HEADER)
        activity_label.pack(anchor="w", padx=16, pady=(8, 0))
        self._activity_list = ctk.CTkTextbox(self, height=120, wrap="word")
        self._activity_list.pack(fill="x", padx=16, pady=8)
        self._activity_list.configure(state="disabled")

    def _wire_events(self) -> None:
        """Subscribe to EventBus events that affect the inspector."""
        self._unsubs.append(
            self._bus.subscribe(ENTITY_CREATED, lambda _event: self._schedule_refresh())
        )
        self._unsubs.append(
            self._bus.subscribe(EVENT_TIMELINE_EVENT, lambda _event: self._schedule_refresh())
        )

    def _schedule_refresh(self) -> None:
        """Marshal UI refresh onto the Tk main thread via UIQueue."""
        self._ui_queue.enqueue(self._refresh)

    def _on_close(self) -> None:
        """Close the inspector and clean up subscriptions."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        self.destroy()

    def _refresh(self) -> None:
        """Refresh all inspector state from AppState."""
        snapshot = self._state_store.snapshot.workspace_os

        self._entities_label.configure(text=f"Entities: {snapshot.entity_count}")
        self._relationships_label.configure(
            text=f"Relationships: {snapshot.relationship_count}"
        )
        self._actions_label.configure(text=f"Actions: {snapshot.action_count}")
        self._events_label.configure(text=f"Events: {snapshot.event_count}")

        self._render_activity(snapshot.recent_events)
        self._render_entities(snapshot.entities)

    def _render_entities(self, entities: list) -> None:
        """Render the entities list with launch buttons."""
        self._entities_list.configure(state="normal")
        self._entities_list.delete("0.0", "end")

        for entity in entities:
            meta = dict(entity.metadata)
            resource_type = meta.get("resource_type")
            value = meta.get("url") or meta.get("path") or meta.get("command") or ""
            line = f"[{entity.entity_type}] {entity.title}"
            if resource_type:
                line += f" ({resource_type})"
            self._entities_list.insert("end", line + "\n")

            if resource_type and value:
                self._entities_list.insert("end", f"  → {value}\n")
                self._entities_list.insert("end", "  ")
                launch_btn = ctk.CTkButton(
                    self._entities_list,
                    text="Launch",
                    width=60,
                    height=20,
                    font=T.FONT_SMALL,
                    command=lambda eid=entity.entity_id, rt=resource_type, val=value: self._controller.launch_resource(
                        str(eid), rt, val
                    ),
                )
                self._entities_list.window_create("end", window=launch_btn)
                self._entities_list.insert("end", "  ")
                chat_btn = ctk.CTkButton(
                    self._entities_list,
                    text="Chat",
                    width=60,
                    height=20,
                    font=T.FONT_SMALL,
                    command=lambda e=entity: self._open_entity_chat(e),
                )
                self._entities_list.window_create("end", window=chat_btn)
                self._entities_list.insert("end", "\n\n")
            else:
                self._entities_list.insert("end", "  ")
                chat_btn = ctk.CTkButton(
                    self._entities_list,
                    text="Chat",
                    width=60,
                    height=20,
                    font=T.FONT_SMALL,
                    command=lambda e=entity: self._open_entity_chat(e),
                )
                self._entities_list.window_create("end", window=chat_btn)
                self._entities_list.insert("end", "\n\n")

        self._entities_list.configure(state="disabled")

    def _render_activity(self, events: tuple[str, ...]) -> None:
        """Render recent timeline activity from AppState."""
        self._activity_list.configure(state="normal")
        self._activity_list.delete("0.0", "end")

        for event_text in events:
            self._activity_list.insert("end", f"• {event_text}\n")

        self._activity_list.configure(state="disabled")

    def _on_search(self) -> None:
        query = self._search_entry.get().strip()
        if not query:
            return
        self._controller.search(query)

    def _show_create_workspace(self) -> None:
        """Open a simple dialog to create a workspace."""
        dialog = ctk.CTkInputDialog(text="Workspace name:", title="Create Workspace")
        title = dialog.get_input()
        if title:
            self._controller.create_workspace(title)

    def _show_create_card(self) -> None:
        """Open a simple dialog to create a card in the first workspace."""
        dialog = ctk.CTkInputDialog(text="Card name:", title="Create Card")
        title = dialog.get_input()
        if title:
            workspace = self._first_entity("workspace")
            if workspace:
                self._controller.create_card(str(workspace.entity_id), title)

    def _show_create_resource(self) -> None:
        """Open a simple dialog to create a URL resource in the first card."""
        dialog = _CreateResourceDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            card = self._first_entity("card")
            if card:
                self._controller.create_resource(
                    str(card.entity_id),
                    dialog.result["title"],
                    "url",
                    dialog.result["url"],
                )

    def _first_entity(self, entity_type: str):
        for e in self._state_store.snapshot.workspace_os.entities:
            if e.entity_type == entity_type:
                return e
        return None

    def _open_entity_chat(self, entity) -> None:
        meta = dict(entity.metadata)
        description = str(meta.get("description", ""))
        url = str(meta.get("url", ""))
        path = str(meta.get("path", "") or meta.get("command", ""))
        self._controller.open_chat(
            str(entity.entity_id),
            str(entity.entity_type),
            str(entity.title or entity.entity_id),
            description=description,
            url=url,
            path=path,
        )


class _CreateResourceDialog(ctk.CTkToplevel):
    """Tiny dialog to create a URL resource."""

    def __init__(self, master: ctk.CTkToplevel) -> None:
        super().__init__(master)
        self.title("Create Resource")
        self.geometry("400x200")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.result: dict[str, str] | None = None

        ctk.CTkLabel(self, text="Title:").pack(anchor="w", padx=16, pady=(16, 0))
        self._title = ctk.CTkEntry(self)
        self._title.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(self, text="URL:").pack(anchor="w", padx=16, pady=(8, 0))
        self._url = ctk.CTkEntry(self)
        self._url.pack(fill="x", padx=16, pady=4)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=16)
        ctk.CTkButton(buttons, text="Create", command=self._create).pack(side="right", padx=4)
        ctk.CTkButton(buttons, text="Cancel", command=self._cancel).pack(side="right", padx=4)

        self._title.focus_set()
        self._title.bind("<Return>", lambda _event: self._url.focus_set())
        self._url.bind("<Return>", lambda _event: self._create())

    def _create(self) -> None:
        title = self._title.get().strip()
        url = self._url.get().strip()
        if title and url:
            self.result = {"title": title, "url": url}
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()
