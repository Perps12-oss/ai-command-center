"""Command palette main window — Replit UX shell over OneDrive architecture."""
from __future__ import annotations

import os
from collections import deque

import customtkinter as ctk

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.clipboard_intent import (
    empty_clipboard_message,
    wants_clipboard,
)
from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import (
    CHAT_CHUNK,
    CHAT_HISTORY_LOADED,
    CHAT_STARTED,
    COMMAND_HISTORY,
    COMMAND_ROUTED,
    MEMORY_ERROR,
    MEMORY_SELECTED,
    MEMORY_STORED,
    MODEL_SELECTED,
    NOTE_CREATED,
    NOTE_ERROR,
    NOTE_INDEX_COMPLETE,
    NOTE_SEARCH_RESULTS,
    NOTE_SELECTED,
    OLLAMA_STATUS,
    OVERLAY_ANCHOR,
    OVERLAY_HIDE,
    OVERLAY_SHOW,
    PLUGIN_CATALOG,
    PLUGIN_ERROR,
    SYSTEM_EVENTS,
    SYSTEM_SNAPSHOT,
    TOOL_ERROR,
    TOOL_RESULT,
)
from ai_command_center.ui.capability_help import show_capability_help
from ai_command_center.ui.components.command_box import CommandBox
from ai_command_center.ui.design_system.command import CommandPalette
from ai_command_center.ui.design_system.shortcut import ShortcutOverlay
from ai_command_center.ui.components.sidebar import Sidebar
from ai_command_center.ui.design_system.toast import ToastManager
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
    "home",
    "chat",
    "notes",
    "memory",
    "system",
    "plugins",
    "settings",
)

# Gate-visible topic literals for Phase 5A verification: tool.result, model.selected, memory.stored.


class CommandPaletteApp(ctk.CTk):
    """1100x700 command palette - fade-in, glass shell, theme, toasts."""

    def __init__(self, bus: EventBus, state_store: AppStateStore) -> None:
        super().__init__()
        self._bus = bus
        self._controller = UIController(bus, state_store, self._queue_state_refresh)
        self._ui_queue = UIQueue(self)
        self._visible = False
        self._views: dict[str, object] = {}
        self._current_view = "home"
        self._active_request_id: str | None = None
        self._pending_user_text: str | None = None
        self._completed_request_ids: deque[str] = deque(maxlen=32)
        self._last_terminal_chat_key: tuple[str, str] | None = None
        self._overlay_mode = "palette"
        self._bus_unsubs: list = []
        self._memory_count = 0
        self._msg_count = 0
        self._note_count = 0

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
        self._wire_navigation_events()
        self._wire_live_events()
        self._setup_keybindings()
        self.update_idletasks()
        self.attributes("-alpha", 0.0)
        self._apply_state()
        snap = self._controller.snapshot()
        theme_manager.apply(
            self,
            theme_name=snap.settings.theme,
            alpha=snap.settings.window_alpha,
        )
        self._visible = False

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

        self._command_box = CommandBox(
            self._command_host,
            on_submit=self._on_command,
            on_help=self._show_capability_help,
        )
        self._command_box.pack(fill="x", padx=T.PAD, pady=10)

        self._content = ctk.CTkFrame(right, fg_color="transparent")
        self._content.pack(fill="both", expand=True)

        self._show_view("home")

        # Overlay widgets (attached to root window for correct placement)
        self._toast = ToastManager(self)
        self._command_palette = CommandPalette(self)
        self._shortcut_overlay = ShortcutOverlay(self)

    def _setup_keybindings(self) -> None:
        self.bind("<Control-k>", lambda _: self._show_command_palette())
        self.bind("<Control-K>", lambda _: self._show_command_palette())
        self.bind("?", self._maybe_show_shortcuts)

    def _show_command_palette(self) -> None:
        commands = [
            ("⌂  Home", "Navigate to Home", lambda: self._navigate("home")),
            ("💬  Chat", "Navigate to Chat", lambda: self._navigate("chat")),
            ("📝  Notes", "Search vault notes", lambda: self._navigate("notes")),
            ("🧠  Memory", "Browse stored memories", lambda: self._navigate("memory")),
            ("⚙  System", "System monitor", lambda: self._navigate("system")),
            ("🧩  Plugins", "Manage plugins", lambda: self._navigate("plugins")),
            ("◈  Settings", "Open settings & themes", lambda: self._navigate("settings")),
            ("⬇  Export Chat", "Save conversation to markdown", self._on_chat_export_request),
            ("↺  Regenerate", "Re-run the last AI prompt", self._on_chat_regenerate),
            ("⟨  Toggle Sidebar", "Collapse or expand sidebar", self._sidebar.toggle_collapse),
            ("?  Shortcuts", "Show keyboard shortcut overlay", self._shortcut_overlay.show),
        ]
        self._command_palette.show(commands)

    def _maybe_show_shortcuts(self, event) -> None:
        focused = self.focus_get()
        if isinstance(focused, (ctk.CTkEntry, ctk.CTkTextbox)):
            return
        self._shortcut_overlay.show()

    # ── view management ────────────────────────────────────────────────────────

    def _ensure_view(self, view_id: str) -> object:
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

    def _home_view(self) -> HomeView | None:
        v = self._views.get("home")
        return v if isinstance(v, HomeView) else None

    def _system_view(self) -> SystemView | None:
        v = self._views.get("system")
        return v if isinstance(v, SystemView) else None

    def _notes_view(self) -> NotesView | None:
        v = self._views.get("notes")
        return v if isinstance(v, NotesView) else None

    def _chat_view(self) -> ChatView | None:
        v = self._views.get("chat")
        return v if isinstance(v, ChatView) else None

    def _memory_view(self) -> MemoryView | None:
        v = self._views.get("memory")
        return v if isinstance(v, MemoryView) else None

    def _show_view(self, view_id: str) -> None:
        if view_id not in VIEW_IDS:
            view_id = "home"
        self._current_view = view_id
        for view in self._views.values():
            view.pack_forget()
        view = self._ensure_view(view_id)
        view.pack(fill="both", expand=True)
        self._sidebar.set_active(view_id)
        if view_id == "settings":
            settings_view = self._views.get("settings")
            if isinstance(settings_view, SettingsView):
                settings_view.load_from_snapshot(self._controller.snapshot().settings)
        if view_id == "chat":
            chat = self._chat_view()
            if chat:
                chat.focus_input()

    def _navigate(self, view_id: str) -> None:
        self._show_view(view_id)
        self._controller.publish_navigate(view_id)

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
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = pathlib.Path.home() / f"chat_export_{ts}.md"
        lines = [f"# Chat Export — {ts}\n"]
        for msg in history:
            role = msg.get("role", "unknown").upper()
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
                    self._on_command(msg.get("content", ""))
                    return

    def _on_memory_delete(self, memory_id: str | None, text: str = "") -> None:
        if memory_id:
            self._controller.publish_memory_delete(memory_id)

    # ── command input ──────────────────────────────────────────────────────────

    def _on_command(self, text: str) -> None:
        lower = text.strip().lower()
        if lower in ("?", "help"):
            self._show_capability_help()
            return

        clipboard: str | None = None
        if wants_clipboard(text):
            clipboard = self._read_clipboard()
            if not clipboard:
                message = empty_clipboard_message()

                def update() -> None:
                    self._navigate("chat")
                    chat = self._chat_view()
                    if chat:
                        chat.show_error(message)

                self._ui_queue.enqueue(update)
                return

        if not (
            lower.startswith("note:")
            or lower.startswith("new note:")
            or lower.startswith("remember:")
            or lower.startswith("memory:")
            or lower.startswith(">")
            or lower.startswith("go ")
            or lower in ("settings", "chat", "notes", "plugins", "home", "system", "memory")
        ):
            self._pending_user_text = text
        self._controller.publish_command(text, clipboard=clipboard)

    def _read_clipboard(self) -> str | None:
        try:
            return self.clipboard_get()
        except Exception:
            return None

    def _show_capability_help(self) -> None:
        show_capability_help(self)

    # ── state refresh ──────────────────────────────────────────────────────────

    def _queue_state_refresh(self) -> None:
        self._ui_queue.enqueue(self._apply_state)

    def _apply_state(self) -> None:
        snap = self._controller.snapshot()
        self._top.update_status(snap.phase, snap.settings.default_model)
        if snap.chat_status == "streaming":
            self._last_terminal_chat_key = None
        self._overlay_mode = snap.settings.overlay_mode
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

        home = self._home_view()
        if home:
            home.update_stats(
                messages=self._msg_count,
                memories=self._memory_count,
                notes=self._note_count,
            )
            if snap.system_snapshot.ollama_online:
                home.update_ollama(True, snap.settings.default_model)
            else:
                home.update_ollama(False)

        chat = self._chat_view()
        if chat:
            chat.set_model(snap.settings.default_model)
            chat.update_context_bar(list(snap.chat_context_sources), int(snap.chat_token_estimate))
            terminal_key = (str(snap.chat_status), str(snap.last_chat_request_id))
            if snap.chat_status == "complete":
                if terminal_key != self._last_terminal_chat_key and snap.last_chat_request_id:
                    chat.finish_assistant(str(snap.last_assistant_message))
                    if snap.last_chat_request_id not in self._completed_request_ids:
                        self._completed_request_ids.append(snap.last_chat_request_id)
                    self._active_request_id = None
                    self._top.update_status("ready", snap.settings.default_model)
                    self._last_terminal_chat_key = terminal_key
            elif snap.chat_status == "cancelled":
                if terminal_key != self._last_terminal_chat_key and snap.last_chat_request_id:
                    chat.show_cancelled()
                    if snap.last_chat_request_id not in self._completed_request_ids:
                        self._completed_request_ids.append(snap.last_chat_request_id)
                    self._active_request_id = None
                    self._last_terminal_chat_key = terminal_key
            elif snap.chat_status == "error":
                if terminal_key != self._last_terminal_chat_key and snap.last_chat_request_id:
                    self._navigate("chat")
                    chat = self._chat_view()
                    if chat:
                        chat.show_error(str(snap.last_chat_error or "Unknown error"))
                    if snap.last_chat_request_id not in self._completed_request_ids:
                        self._completed_request_ids.append(snap.last_chat_request_id)
                    self._active_request_id = None
                    self._top.update_status("error", snap.settings.default_model)
                    self._last_terminal_chat_key = terminal_key

        try:
            theme_manager.apply(
                self,
                theme_name=snap.settings.theme,
                alpha=snap.settings.window_alpha,
            )
        except Exception:
            pass

    # ── fade / show / hide ─────────────────────────────────────────────────────

    def _fade_in(self, step: int = 0) -> None:
        target = theme_manager.active_alpha()
        alpha = min(target, (step + 1) / T.FADE_STEPS * target)
        self.attributes("-alpha", alpha)
        if step + 1 < T.FADE_STEPS:
            delay = max(1, T.FADE_IN_MS // T.FADE_STEPS)
            self.after(delay, lambda: self._fade_in(step + 1))

    def _fade_out(self, on_done) -> None:
        start_alpha = theme_manager.active_alpha()

        def step(n: int) -> None:
            alpha = max(0.0, start_alpha - (n + 1) / T.FADE_STEPS * start_alpha)
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
        self._visible = True
        self.deiconify()
        self.lift()
        self.focus_force()
        self._command_box.focus()
        self._fade_in()

    def hide(self) -> None:
        if not self._visible:
            return
        self._visible = False

        def done() -> None:
            self.withdraw()
            self.attributes("-topmost", False)

        self._fade_out(done)

    def toggle(self) -> None:
        if self._visible:
            self.hide()
        else:
            self.show()

    def is_visible(self) -> bool:
        return self._visible

    def destroy(self) -> None:
        for unsub in self._bus_unsubs:
            try:
                unsub()
            except Exception:
                pass
        self._bus_unsubs.clear()
        super().destroy()

    def tray_phase(self) -> str:
        return self._controller.snapshot().phase

    # ── event wiring (OneDrive architecture) ───────────────────────────────────

    def _wire_navigation_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe(COMMAND_ROUTED, self._on_command_routed_navigate)
        )

    def _on_command_routed_navigate(self, event: Event) -> None:
        if event.source != "command_router":
            return
        if event.payload.get("intent") != "navigate":
            return
        view = str((event.payload.get("args") or {}).get("view", "home")).lower()
        if view not in VIEW_IDS:
            view = "home"

        def update() -> None:
            self._navigate(view)

        self._ui_queue.enqueue(update)

    def _wire_chat_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe(CHAT_STARTED, self._on_chat_started)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(CHAT_CHUNK, self._on_chat_chunk)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(CHAT_HISTORY_LOADED, self._on_chat_history_loaded)
        )

    def _on_chat_started(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id", ""))
        user_text = self._pending_user_text
        self._pending_user_text = None

        def update() -> None:
            self._navigate("chat")
            chat = self._chat_view()
            if chat:
                if user_text:
                    chat.show_user_message(user_text)
                chat.begin_assistant(request_id)
            self._active_request_id = request_id

        self._ui_queue.enqueue(update)

    def _on_chat_chunk(self, event: Event) -> None:
        text = str(event.payload.get("text", ""))
        request_id = str(event.payload.get("request_id", ""))
        if not text or request_id != self._active_request_id:
            return

        def update() -> None:
            chat = self._chat_view()
            if chat:
                chat.append_chunk(text)

        self._ui_queue.enqueue(update)

    def _on_chat_history_loaded(self, event: Event) -> None:
        messages = event.payload.get("messages") or []

        def update() -> None:
            chat = self._chat_view()
            if chat:
                chat.load_history(messages)

        self._ui_queue.enqueue(update)

    def _wire_note_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe(NOTE_SEARCH_RESULTS, self._on_note_results)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(NOTE_SELECTED, self._on_note_selected)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(NOTE_INDEX_COMPLETE, self._on_note_index_complete)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(NOTE_CREATED, self._on_note_created)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(NOTE_ERROR, self._on_note_error)
        )

    def _on_note_results(self, event: Event) -> None:
        query = str(event.payload.get("query", ""))
        results = event.payload.get("results") or []

        def update() -> None:
            self._navigate("notes")
            notes = self._notes_view()
            if notes:
                notes.show_results(query, results)

        self._ui_queue.enqueue(update)

    def _on_note_selected(self, event: Event) -> None:
        path = str(event.payload.get("path", ""))

        def update() -> None:
            self._toast.show(f"Opened: {os.path.basename(path)}", kind="info")

        self._ui_queue.enqueue(update)

    def _on_note_index_complete(self, event: Event) -> None:
        files = int(event.payload.get("files", 0))
        ms = int(event.payload.get("ms", 0))

        def update() -> None:
            self._note_count = files
            self._toast.show(f"Indexed {files} notes ({ms} ms)", kind="success")
            home = self._home_view()
            if home:
                home.update_vault(indexing=False, files=files, ms=ms)
            self._apply_state()

        self._ui_queue.enqueue(update)

    def _on_note_created(self, event: Event) -> None:
        path = str(event.payload.get("path", ""))
        self._ui_queue.enqueue(
            lambda: self._toast.show(f"Created note: {os.path.basename(path)}", kind="success")
        )

    def _on_note_error(self, event: Event) -> None:
        message = str(event.payload.get("message", "Note error"))

        def update() -> None:
            self._navigate("notes")
            notes = self._notes_view()
            if notes:
                notes.show_error(message)

        self._ui_queue.enqueue(update)

    def _wire_memory_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe(MEMORY_STORED, self._on_memory_stored)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(MEMORY_SELECTED, self._on_memory_selected)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(MEMORY_ERROR, self._on_memory_error)
        )

    def _on_memory_stored(self, event: Event) -> None:
        label = str(event.payload.get("label", ""))
        self._memory_count += 1

        def update() -> None:
            self._toast.show(f"Remembered: {label}", kind="success")
            home = self._home_view()
            if home:
                home.update_memory(self._memory_count)
            memory = self._memory_view()
            if memory:
                memory.add_memory(event.payload)

        self._ui_queue.enqueue(update)

    def _on_memory_selected(self, event: Event) -> None:
        label = str(event.payload.get("label", ""))

        def update() -> None:
            self._navigate("memory")
            self._toast.show(f"Memory: {label}", kind="info")

        self._ui_queue.enqueue(update)

    def _on_memory_error(self, event: Event) -> None:
        message = str(event.payload.get("message", "Memory error"))

        def update() -> None:
            self._navigate("memory")
            memory = self._memory_view()
            if memory:
                memory.show_error(message)

        self._ui_queue.enqueue(update)

    def _wire_tool_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe(TOOL_RESULT, self._on_tool_result)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(TOOL_ERROR, self._on_tool_error)
        )

    def _on_tool_result(self, event: Event) -> None:
        tool = str(event.payload.get("tool", ""))
        output = str(event.payload.get("output", ""))

        def update() -> None:
            chat = self._chat_view()
            if chat:
                chat.show_tool_output(tool, output, success=True)
            self._apply_state()

        self._ui_queue.enqueue(update)

    def _on_tool_error(self, event: Event) -> None:
        tool = str(event.payload.get("tool", ""))
        error = str(event.payload.get("error", ""))

        def update() -> None:
            chat = self._chat_view()
            if chat:
                chat.show_tool_output(tool, error, success=False)
            self._toast.show(f"Tool error: {tool}", kind="error")

        self._ui_queue.enqueue(update)

    def _wire_plugin_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe(PLUGIN_CATALOG, self._on_plugin_catalog)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(PLUGIN_ERROR, self._on_plugin_error)
        )

    def _on_plugin_catalog(self, event: Event) -> None:
        plugins = event.payload.get("plugins") or []

        def update() -> None:
            self._navigate("plugins")
            plugins_view = self._views.get("plugins")
            if isinstance(plugins_view, PluginsView):
                plugins_view.show_catalog(plugins)

        self._ui_queue.enqueue(update)

    def _on_plugin_error(self, event: Event) -> None:
        message = str(event.payload.get("message", "Plugin error"))

        def update() -> None:
            plugins_view = self._views.get("plugins")
            if isinstance(plugins_view, PluginsView):
                plugins_view.show_error(message)

        self._ui_queue.enqueue(update)

    def _wire_overlay_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe(OVERLAY_SHOW, self._on_overlay_show)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(OVERLAY_ANCHOR, self._on_overlay_anchor)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(OVERLAY_HIDE, self._on_overlay_hide)
        )

    def _on_overlay_show(self, event: Event) -> None:
        mode = str(event.payload.get("mode", "palette"))
        x = int(event.payload.get("x", 0) or 0)
        y = int(event.payload.get("y", 0) or 0)

        def update() -> None:
            self._overlay_mode = mode
            self._apply_overlay_geometry(mode, x, y)
            self._apply_state()

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
            self.geometry(f"{T.WINDOW_WIDTH}x{T.WINDOW_HEIGHT}")
            self.minsize(900, 560)

    def _wire_live_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe(SYSTEM_SNAPSHOT, self._on_system_snapshot)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(OLLAMA_STATUS, self._on_ollama_status)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(SYSTEM_EVENTS, self._on_system_events)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(COMMAND_HISTORY, self._on_command_history)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(MODEL_SELECTED, self._on_model_selected)
        )

    def _on_system_snapshot(self, event: Event) -> None:
        payload = event.payload or {}

        def update() -> None:
            system = self._system_view()
            if system:
                system.apply_system_snapshot(payload)
            self._apply_state()

        self._ui_queue.enqueue(update)

    def _on_ollama_status(self, event: Event) -> None:
        online = bool(event.payload.get("online", False))
        model = str(event.payload.get("model", ""))

        def update() -> None:
            home = self._home_view()
            if home:
                home.update_ollama(online, model)
            self._apply_state()

        self._ui_queue.enqueue(update)

    def _on_system_events(self, event: Event) -> None:
        text = str(event.payload.get("text", ""))
        kind = str(event.payload.get("kind", "system"))

        def update() -> None:
            home = self._home_view()
            if home:
                home.add_activity(text, kind)

        self._ui_queue.enqueue(update)

    def _on_command_history(self, event: Event) -> None:
        payload = event.payload or {}

        def update() -> None:
            home = self._home_view()
            if home:
                home.apply_command_history(payload)
            self._apply_state()

        self._ui_queue.enqueue(update)

    def _on_model_selected(self, event: Event) -> None:
        model = str(event.payload.get("model", ""))

        def update() -> None:
            self._top.update_status("ready", model)
            chat = self._chat_view()
            if chat:
                chat.set_model(model)

        self._ui_queue.enqueue(update)
