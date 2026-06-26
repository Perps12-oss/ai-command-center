"""Command palette main window — wires all UI features together."""
from __future__ import annotations

import customtkinter as ctk

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.ui.components.command_box import CommandBox
from ai_command_center.ui.components.command_palette import CommandPalette
from ai_command_center.ui.components.shortcut_overlay import ShortcutOverlay
from ai_command_center.ui.components.sidebar import Sidebar
from ai_command_center.ui.components.toast import ToastManager
from ai_command_center.ui.components.top_bar import TopBar
from ai_command_center.ui.controller import UIController
from ai_command_center.ui.theme import theme_manager
from ai_command_center.ui.theme import tokens as T
from ai_command_center.ui.ui_queue import UIQueue
from ai_command_center.ui.views.chat_view import ChatView
from ai_command_center.ui.views.home_view import HomeView
from ai_command_center.ui.views.memory_view import MemoryView
from ai_command_center.ui.views.notes_view import NotesView
from ai_command_center.ui.views.placeholder import PlaceholderView
from ai_command_center.ui.views.plugins_view import PluginsView
from ai_command_center.ui.views.settings_view import SettingsView
from ai_command_center.ui.views.system_view import SystemView

VIEW_IDS: tuple[str, ...] = (
    "home", "chat", "notes", "memory", "system", "plugins", "settings",
)


class CommandPaletteApp(ctk.CTk):
    """1100×700 command palette — glass shell, theme, toasts, command palette."""

    def __init__(self, bus: EventBus, state_store: AppStateStore) -> None:
        super().__init__()
        self._bus              = bus
        self._controller       = UIController(bus, state_store, self._queue_state_refresh)
        self._ui_queue         = UIQueue(self)
        self._visible          = False
        self._views: dict[str, PlaceholderView | ChatView | NotesView | HomeView | SystemView | MemoryView] = {}
        self._current_view     = "home"
        self._active_request_id: str | None = None
        self._pending_user_text: str | None = None
        self._overlay_mode     = "palette"
        self._bus_unsubs: list = []
        self._memory_count     = 0
        self._msg_count        = 0
        self._note_count       = 0

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("AI Command Center")
        self.configure(fg_color=T.BG_DEEP)
        self.geometry(f"{T.WINDOW_WIDTH}x{T.WINDOW_HEIGHT}")
        self.minsize(900, 560)

        self.withdraw()
        self._build_layout()
        self._wire_chat_events()
        self._wire_note_events()
        self._wire_overlay_events()
        self._wire_tool_events()
        self._wire_memory_events()
        self._wire_plugin_events()
        self._wire_home_events()
        self._wire_workspace_events()
        self._setup_keybindings()
        self.update_idletasks()
        theme_manager.apply(self)
        self._apply_state()
        self._visible = False

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        self._top = TopBar(
            self,
            on_settings=lambda: self._navigate("settings"),
            on_close=self.hide,
        )
        self._top.pack(fill="x", side="top")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)

        self._sidebar = Sidebar(body, on_navigate=self._navigate)
        self._sidebar.pack(fill="y", side="left")

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.pack(fill="both", expand=True, side="left")

        self._command_host = ctk.CTkFrame(right, fg_color=T.BG_PANEL, corner_radius=0, height=80)
        self._command_host.pack(fill="x")
        self._command_host.pack_propagate(False)

        self._command_box = CommandBox(self._command_host, on_submit=self._on_command)
        self._command_box.pack(fill="x", padx=T.PAD, pady=10)

        self._content = ctk.CTkFrame(right, fg_color="transparent")
        self._content.pack(fill="both", expand=True)

        self._show_view("home")

        # Overlay widgets (attached to root window for correct placement)
        self._toast            = ToastManager(self)
        self._command_palette  = CommandPalette(self)
        self._shortcut_overlay = ShortcutOverlay(self)

    # ── keyboard bindings ─────────────────────────────────────────────────────

    def _setup_keybindings(self) -> None:
        self.bind("<Control-k>", lambda _: self._show_command_palette())
        self.bind("<Control-K>", lambda _: self._show_command_palette())
        self.bind("?",           self._maybe_show_shortcuts)

    def _show_command_palette(self) -> None:
        commands = [
            ("⌂  Home",           "Navigate to Home",              lambda: self._navigate("home")),
            ("💬  Chat",           "Navigate to Chat",              lambda: self._navigate("chat")),
            ("📝  Notes",          "Search vault notes",            lambda: self._navigate("notes")),
            ("🧠  Memory",         "Browse stored memories",        lambda: self._navigate("memory")),
            ("⚙  System",          "System monitor",               lambda: self._navigate("system")),
            ("🧩  Plugins",        "Manage plugins",                lambda: self._navigate("plugins")),
            ("◈  Settings",        "Open settings & themes",        lambda: self._navigate("settings")),
            ("⬇  Export Chat",    "Save conversation to markdown",  self._on_chat_export_request),
            ("↺  Regenerate",      "Re-run the last AI prompt",     self._on_chat_regenerate),
            ("⟨  Toggle Sidebar",  "Collapse or expand sidebar",    self._sidebar.toggle_collapse),
            ("?  Shortcuts",       "Show keyboard shortcut overlay", self._shortcut_overlay.show),
        ]
        self._command_palette.show(commands)

    def _maybe_show_shortcuts(self, event) -> None:
        focused = self.focus_get()
        if isinstance(focused, (ctk.CTkEntry, ctk.CTkTextbox)):
            return
        self._shortcut_overlay.show()

    # ── view management ───────────────────────────────────────────────────────

    def _ensure_view(
        self, view_id: str
    ) -> PlaceholderView | ChatView | NotesView | HomeView | SystemView | SettingsView | PluginsView | MemoryView:
        if view_id not in self._views:
            if view_id == "home":
                self._views[view_id] = HomeView(self._content)
            elif view_id == "chat":
                self._views[view_id] = ChatView(
                    self._content,
                    on_cancel=self._controller.publish_chat_cancel,
                    on_export=self._on_chat_export,
                    on_regenerate=self._on_chat_regenerate,
                    on_send=self._on_command,
                )
            elif view_id == "notes":
                self._views[view_id] = NotesView(
                    self._content,
                    on_select=self._controller.publish_note_select,
                )
            elif view_id == "memory":
                self._views[view_id] = MemoryView(
                    self._content,
                    on_delete=self._on_memory_delete,
                )
            elif view_id == "system":
                self._views[view_id] = SystemView(self._content)
            elif view_id == "settings":
                self._views[view_id] = SettingsView(
                    self._content,
                    on_save=self._on_settings_save,
                )
            elif view_id == "plugins":
                self._views[view_id] = PluginsView(
                    self._content,
                    on_toggle=self._controller.publish_plugin_toggle,
                )
            else:
                self._views[view_id] = PlaceholderView(self._content, view_id)
        return self._views[view_id]

    def _notes_view(self) -> NotesView | None:
        v = self._views.get("notes")
        return v if isinstance(v, NotesView) else None

    def _chat_view(self) -> ChatView | None:
        v = self._views.get("chat")
        return v if isinstance(v, ChatView) else None

    def _home_view(self) -> HomeView | None:
        v = self._views.get("home")
        return v if isinstance(v, HomeView) else None

    def _memory_view(self) -> MemoryView | None:
        v = self._views.get("memory")
        return v if isinstance(v, MemoryView) else None

    # ── settings callback ─────────────────────────────────────────────────────

    def _on_settings_save(self, key: str, value: str) -> None:
        self._controller.request_settings_change(key, value)
        if key == "theme":
            theme_manager.apply(self, theme_name=value)
            self._toast.show(f'Theme "{value}" applied', kind="success")
        elif key == "window_alpha":
            try:
                theme_manager.apply(self, alpha=float(value))
            except ValueError:
                pass

    # ── chat export / regenerate callbacks ────────────────────────────────────

    def _on_chat_export(self, history: list[dict]) -> None:
        import datetime
        import pathlib
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = pathlib.Path.home() / f"chat_export_{ts}.md"
        lines = [f"# Chat Export — {ts}\n"]
        for msg in history:
            role    = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            lines.append(f"## {role}\n{content}\n")
        try:
            path.write_text("\n".join(lines), encoding="utf-8")
            self._toast.show(f"Saved to {path.name}", kind="success")
        except Exception as exc:
            self._toast.show(f"Export failed: {exc}", kind="error")

    def _on_chat_export_request(self) -> None:
        chat = self._chat_view()
        if chat and chat._history:
            self._on_chat_export(list(chat._history))
        else:
            self._toast.show("No chat history to export", kind="warning")

    def _on_chat_regenerate(self) -> None:
        chat = self._chat_view()
        if chat and chat._history:
            for msg in reversed(chat._history):
                if msg.get("role") == "user":
                    text = msg["content"]
                    self._pending_user_text = text
                    self._controller.publish_command(text, clipboard=None)
                    self._toast.show("Regenerating last response…", kind="info")
                    return
        self._toast.show("No message to regenerate", kind="warning")

    # ── memory delete callback ────────────────────────────────────────────────

    def _on_memory_delete(self, item_id, text: str) -> None:
        self._memory_count = max(0, self._memory_count - 1)
        self._toast.show("Memory removed", kind="info")
        self._update_home_stats()

    # ── stats helper ──────────────────────────────────────────────────────────

    def _update_home_stats(self) -> None:
        home = self._home_view()
        if home:
            home.update_stats(
                messages=self._msg_count,
                memories=self._memory_count,
                notes=self._note_count,
            )

    # ── chat event wiring ─────────────────────────────────────────────────────

    def _wire_chat_events(self) -> None:
        for event, handler in (
            ("chat.started",       self._on_chat_started),
            ("chat.chunk",         self._on_chat_chunk),
            ("chat.complete",      self._on_chat_complete),
            ("chat.cancelled",     self._on_chat_cancelled),
            ("chat.error",         self._on_chat_error),
            ("ollama.status",      self._on_ollama_status),
            ("chat.history_loaded", self._on_chat_history_loaded),
            ("model.selected",     self._on_model_selected),
        ):
            self._bus_unsubs.append(self._bus.subscribe(event, handler))

    def _on_chat_history_loaded(self, event: Event) -> None:
        messages = event.payload.get("messages") or []

        def update() -> None:
            view = self._ensure_view("chat")
            if isinstance(view, ChatView):
                view.load_history(list(messages))

        self._ui_queue.enqueue(update)

    def _on_chat_started(self, event: Event) -> None:
        rid = str(event.payload.get("request_id", ""))
        self._active_request_id = rid or None

        def update() -> None:
            self._navigate("chat")
            chat = self._chat_view()
            if chat and self._pending_user_text:
                chat.show_user_message(self._pending_user_text)
                self._pending_user_text = None
            if chat and rid:
                chat.begin_assistant(rid)
            self._top.update_status("busy", self._controller.snapshot().settings.default_model)

        self._ui_queue.enqueue(update)

    def _on_chat_chunk(self, event: Event) -> None:
        text = str(event.payload.get("text", ""))
        if not text:
            return

        def update() -> None:
            chat = self._chat_view()
            if chat:
                chat.append_chunk(text)

        self._ui_queue.enqueue(update)

    def _on_chat_complete(self, event: Event) -> None:
        text = str(event.payload.get("text", ""))
        self._msg_count += 1
        count = self._msg_count

        def update() -> None:
            chat = self._chat_view()
            if chat:
                chat.finish_assistant(text)
            self._active_request_id = None
            snap  = self._controller.snapshot()
            model = snap.settings.default_model
            self._top.update_status("ready", model)
            home = self._home_view()
            if home:
                home.add_activity(f"AI responded ({len(text.split())} words)", "chat")
                home.update_stats(messages=count, memories=self._memory_count, notes=self._note_count)

        self._ui_queue.enqueue(update)

    def _on_chat_cancelled(self, event: Event) -> None:
        def update() -> None:
            chat = self._chat_view()
            if chat:
                chat.show_cancelled()
            self._active_request_id = None

        self._ui_queue.enqueue(update)

    def _on_chat_error(self, event: Event) -> None:
        message = str(event.payload.get("message", "Unknown error"))

        def update() -> None:
            chat = self._chat_view()
            if chat:
                chat.show_error(message)
            self._active_request_id = None
            self._top.update_status("error", self._controller.snapshot().settings.default_model)
            self._toast.show(f"Chat error: {message[:60]}", kind="error")

        self._ui_queue.enqueue(update)

    def _on_ollama_status(self, event: Event) -> None:
        online = bool(event.payload.get("online"))

        def update() -> None:
            snap  = self._controller.snapshot()
            phase = "ready" if online else "error"
            model = snap.settings.default_model
            self._top.update_status(phase, model)
            home = self._home_view()
            if home:
                home.update_ollama(online, model)
            chat = self._chat_view()
            if chat and online and model:
                chat.set_model(model)

        self._ui_queue.enqueue(update)

    def _on_model_selected(self, event: Event) -> None:
        model = str(event.payload.get("model", ""))

        def update() -> None:
            if model:
                self._top.update_status(self._controller.snapshot().phase, model)
                chat = self._chat_view()
                if chat:
                    chat.set_model(model)

        self._ui_queue.enqueue(update)

    # ── tool event wiring ─────────────────────────────────────────────────────

    def _wire_tool_events(self) -> None:
        self._bus_unsubs.append(self._bus.subscribe("tool.result", self._on_tool_result))
        self._bus_unsubs.append(self._bus.subscribe("tool.error",  self._on_tool_error))

    def _on_tool_result(self, event: Event) -> None:
        tool   = str(event.payload.get("tool", "tool"))
        output = str(event.payload.get("output", ""))

        def update() -> None:
            self._navigate("chat")
            chat = self._chat_view()
            if chat:
                chat.show_tool_output(tool, output, success=True)
            home = self._home_view()
            if home:
                home.add_activity(f"Tool: {tool} → OK", "tool")

        self._ui_queue.enqueue(update)

    def _on_tool_error(self, event: Event) -> None:
        tool    = str(event.payload.get("tool", "tool"))
        message = str(event.payload.get("message", event.payload.get("error", "Tool failed")))

        def update() -> None:
            self._navigate("chat")
            chat = self._chat_view()
            if chat:
                chat.show_tool_output(tool, message, success=False)
            self._toast.show(f"Tool failed: {tool}", kind="error")

        self._ui_queue.enqueue(update)

    # ── memory event wiring ───────────────────────────────────────────────────

    def _wire_memory_events(self) -> None:
        for event, handler in (
            ("memory.stored",   self._on_memory_stored),
            ("memory.selected", self._on_memory_selected),
            ("memory.error",    self._on_memory_error),
        ):
            self._bus_unsubs.append(self._bus.subscribe(event, handler))

    def _on_memory_stored(self, event: Event) -> None:
        label = str(event.payload.get("label", ""))
        self._memory_count += 1
        count = self._memory_count

        def update() -> None:
            self._navigate("chat")
            chat = self._chat_view()
            if chat:
                chat.show_system_message(f"Remembered: {label}")
            home = self._home_view()
            if home:
                home.update_memory(count)
                home.add_activity(f"Remembered: {label}", "memory")
                home.update_stats(messages=self._msg_count, memories=count, notes=self._note_count)
            mem = self._memory_view()
            if mem:
                mem.prepend_memory(label)
            self._toast.show(f"Memory stored: {label}", kind="success")

        self._ui_queue.enqueue(update)

    def _on_memory_selected(self, event: Event) -> None:
        labels = event.payload.get("labels") or []

        def update() -> None:
            self._navigate("chat")
            chat = self._chat_view()
            if chat:
                names = ", ".join(str(x) for x in labels)
                chat.show_system_message(f"Memory selected for chat: {names}")

        self._ui_queue.enqueue(update)

    def _on_memory_error(self, event: Event) -> None:
        message = str(event.payload.get("message", "Memory error"))

        def update() -> None:
            self._navigate("chat")
            chat = self._chat_view()
            if chat:
                chat.show_system_message(message)
            self._toast.show(f"Memory error: {message[:60]}", kind="error")

        self._ui_queue.enqueue(update)

    # ── plugin event wiring ───────────────────────────────────────────────────

    def _wire_plugin_events(self) -> None:
        self._bus_unsubs.append(self._bus.subscribe("plugin.catalog", self._on_plugin_catalog))
        self._bus_unsubs.append(self._bus.subscribe("plugin.error",   self._on_plugin_error))

    def _on_plugin_catalog(self, event: Event) -> None:
        plugins = event.payload.get("plugins") or []

        def update() -> None:
            view = self._ensure_view("plugins")
            if isinstance(view, PluginsView):
                view.show_catalog(list(plugins))

        self._ui_queue.enqueue(update)

    def _on_plugin_error(self, event: Event) -> None:
        message = str(event.payload.get("message", "Plugin error"))

        def update() -> None:
            view = self._views.get("plugins")
            if isinstance(view, PluginsView):
                view.show_error(message)

        self._ui_queue.enqueue(update)

    # ── workspace event wiring ────────────────────────────────────────────────

    def _wire_workspace_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe("workspace.resolved", self._on_workspace_resolved)
        )

    def _on_workspace_resolved(self, event: Event) -> None:
        title = str(event.payload.get("title", "")).strip()
        suggestions = event.payload.get("suggestions") or []

        def update() -> None:
            home = self._home_view()
            if not home:
                return
            if title:
                home.add_activity(f"Workspace: {title}", "system")
            for item in suggestions[:3]:
                if isinstance(item, dict):
                    label = str(item.get("label", "")).strip()
                    if label:
                        home.add_activity(f"Suggestion: {label}", "system")

        self._ui_queue.enqueue(update)

    # ── home status event wiring ──────────────────────────────────────────────

    def _wire_home_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe("note.index_progress", self._on_home_index_progress)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("note.index_complete", self._on_home_index_complete)
        )

    def _on_home_index_progress(self, event: Event) -> None:
        indexed = int(event.payload.get("indexed", 0) or 0)

        def update() -> None:
            home = self._home_view()
            if home:
                home.update_vault(indexing=True, files=indexed)

        self._ui_queue.enqueue(update)

    def _on_home_index_complete(self, event: Event) -> None:
        files = int(event.payload.get("files", 0) or 0)
        ms    = int(event.payload.get("ms",    0) or 0)
        self._note_count = files

        def update() -> None:
            home = self._home_view()
            if home:
                home.update_vault(indexing=False, files=files, ms=ms)
                home.add_activity(f"Vault indexed: {files} notes in {ms} ms", "note")
                home.update_stats(messages=self._msg_count, memories=self._memory_count, notes=files)
            self._toast.show(f"Vault ready — {files} notes indexed", kind="success")

        self._ui_queue.enqueue(update)

    # ── note event wiring ─────────────────────────────────────────────────────

    def _wire_note_events(self) -> None:
        for event, handler in (
            ("note.search_results", self._on_note_search_results),
            ("note.selected",       self._on_note_selected),
            ("note.created",        self._on_note_created),
            ("note.error",          self._on_note_error),
        ):
            self._bus_unsubs.append(self._bus.subscribe(event, handler))

    def _on_note_search_results(self, event: Event) -> None:
        query   = str(event.payload.get("query", ""))
        results = event.payload.get("results") or []
        count   = len(results)

        def update() -> None:
            self._navigate("notes")
            notes = self._notes_view()
            if notes:
                notes.show_results(query, list(results))
            home = self._home_view()
            if home:
                home.update_vault_search(query, count)
                home.add_activity(f"Note search: {count} result{'s' if count != 1 else ''} for \"{query}\"", "note")

        self._ui_queue.enqueue(update)

    def _on_note_selected(self, event: Event) -> None:
        path  = str(event.payload.get("path",  ""))
        title = str(event.payload.get("title", path))

        def update() -> None:
            notes = self._notes_view()
            if notes:
                notes.show_selected(path, title)

        self._ui_queue.enqueue(update)

    def _on_note_created(self, event: Event) -> None:
        path  = str(event.payload.get("path",  ""))
        title = str(event.payload.get("title", ""))

        def update() -> None:
            self._navigate("notes")
            notes = self._notes_view()
            if notes:
                notes.show_created(path, title)

        self._ui_queue.enqueue(update)

    def _on_note_error(self, event: Event) -> None:
        message = str(event.payload.get("message", "Note error"))

        def update() -> None:
            self._navigate("notes")
            notes = self._notes_view()
            if notes:
                notes.show_error(message)

        self._ui_queue.enqueue(update)

    # ── overlay event wiring ──────────────────────────────────────────────────

    def _wire_overlay_events(self) -> None:
        for event, handler in (
            ("overlay.show",   self._on_overlay_show),
            ("overlay.anchor", self._on_overlay_anchor),
            ("overlay.hide",   self._on_overlay_hide),
        ):
            self._bus_unsubs.append(self._bus.subscribe(event, handler))

    def _on_overlay_show(self, event: Event) -> None:
        mode = str(event.payload.get("mode", "palette"))
        x    = int(event.payload.get("x", 0) or 0)
        y    = int(event.payload.get("y", 0) or 0)

        def update() -> None:
            self._overlay_mode = mode
            self._apply_overlay_geometry(mode, x, y)

        self._ui_queue.enqueue(update)

    def _on_overlay_anchor(self, event: Event) -> None:
        x = int(event.payload.get("x", 0) or 0)
        y = int(event.payload.get("y", 0) or 0)

        def update() -> None:
            if self._overlay_mode == "compact" and x > 0 and y > 0:
                self.geometry(f"640x420+{x}+{y}")

        self._ui_queue.enqueue(update)

    def _on_overlay_hide(self, _event: Event) -> None:
        def update() -> None:
            self.attributes("-topmost", False)

        self._ui_queue.enqueue(update)

    def _apply_overlay_geometry(self, mode: str, x: int, y: int) -> None:
        if mode == "compact":
            self.attributes("-topmost", True)
            if x > 0 and y > 0:
                self.geometry(f"640x420+{x}+{y}")
            else:
                self.geometry("640x420")
            self.minsize(480, 320)
        else:
            self.attributes("-topmost", False)
            snap = self._controller.snapshot()
            w = int(snap.settings.window_width)
            h = int(snap.settings.window_height)
            self.geometry(f"{w}x{h}")
            self.minsize(900, 560)

    # ── view routing ───────────────────────────────────────────────────────────

    def _show_view(self, view_id: str) -> None:
        if view_id not in VIEW_IDS:
            view_id = "home"

        old_view = self._views.get(self._current_view)
        if isinstance(old_view, SystemView) and view_id != self._current_view:
            old_view.on_hide()

        self._current_view = view_id
        for vid, view in self._views.items():
            if vid != view_id:
                view.pack_forget()

        new_view = self._ensure_view(view_id)
        new_view.pack(fill="both", expand=True)
        if isinstance(new_view, SystemView):
            new_view.on_show()

        self._sidebar.set_active(view_id)

    def _navigate(self, view_id: str) -> None:
        self._show_view(view_id)
        self._controller.publish_navigate(view_id)

    # ── command handling ───────────────────────────────────────────────────────

    def _on_command(self, text: str) -> None:
        lower = text.strip().lower()
        clipboard: str | None = None
        if "clipboard" in lower:
            clipboard = self._read_clipboard()
        if not (
            lower.startswith("note:")
            or lower.startswith("new note:")
            or lower.startswith("remember:")
            or lower.startswith("memory:")
            or lower.startswith(">")
            or lower.startswith("go ")
        ):
            self._pending_user_text = text
        home = self._home_view()
        if home:
            short = text[:60] + ("…" if len(text) > 60 else "")
            home.add_activity(f"Command: {short}", "chat")
        self._controller.publish_command(text, clipboard=clipboard)

    def _read_clipboard(self) -> str | None:
        try:
            data = self.clipboard_get()
            return str(data).strip() or None
        except Exception:
            return None

    # ── state refresh ──────────────────────────────────────────────────────────

    def _queue_state_refresh(self) -> None:
        self._ui_queue.enqueue(self._apply_state)

    def _apply_state(self) -> None:
        snap = self._controller.snapshot()
        self._top.update_status(snap.phase, snap.settings.default_model)
        self._overlay_mode = snap.settings.overlay_mode

        # Theme from saved settings
        saved_theme = getattr(snap.settings, "theme", None)
        if saved_theme:
            theme_manager.apply(self, theme_name=saved_theme)
        saved_alpha = getattr(snap.settings, "window_alpha", None)
        if saved_alpha:
            try:
                theme_manager.apply(self, alpha=float(saved_alpha))
            except (ValueError, TypeError):
                pass

        try:
            if self._overlay_mode == "compact":
                self._apply_overlay_geometry("compact", 0, 0)
            else:
                w = int(snap.settings.window_width)
                h = int(snap.settings.window_height)
                if w >= 900 and h >= 560:
                    self.geometry(f"{w}x{h}")
        except ValueError:
            pass

        settings_view = self._views.get("settings")
        if isinstance(settings_view, SettingsView):
            settings_view.load_from_snapshot(snap.settings)

        if snap.last_command:
            home = self._home_view()
            if home:
                home.set_last_command(
                    f'Last: "{snap.last_command}" → {snap.last_command_intent or "pending"}'
                )

    # ── show / hide / toggle ───────────────────────────────────────────────────

    def _fade_in(self, step: int = 0) -> None:
        target = theme_manager.active_alpha()
        alpha  = min(target, (step + 1) / T.FADE_STEPS * target)
        self.attributes("-alpha", alpha)
        if step + 1 < T.FADE_STEPS:
            delay = max(1, T.FADE_IN_MS // T.FADE_STEPS)
            self.after(delay, lambda: self._fade_in(step + 1))

    def _fade_out(self, on_done) -> None:
        start = theme_manager.active_alpha()

        def step(n: int) -> None:
            alpha = max(0.0, start - (n + 1) / T.FADE_STEPS * start)
            self.attributes("-alpha", alpha)
            if n + 1 < T.FADE_STEPS:
                delay = max(1, T.FADE_IN_MS // T.FADE_STEPS)
                self.after(delay, lambda: step(n + 1))
            else:
                on_done()

        step(0)

    def show(self) -> None:
        if self._visible:
            self.lift()
            self.focus_force()
            self._command_box.focus()
            return
        self._controller.publish_palette_open()
        self.deiconify()
        self._visible = True
        self.attributes("-alpha", 0.0)
        self._fade_in()
        self.after(T.FADE_IN_MS + 20, self._command_box.focus)

    def hide(self) -> None:
        if not self._visible:
            return
        self._controller.publish_palette_close()

        def done() -> None:
            self.withdraw()
            self._visible = False

        self._fade_out(done)

    def toggle(self) -> None:
        if self._visible:
            self.hide()
        else:
            self.show()

    @property
    def is_visible(self) -> bool:
        return self._visible

    def tray_phase(self) -> str:
        return self._controller.snapshot().phase
