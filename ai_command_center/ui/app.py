"""Command palette main window."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.clipboard_intent import (
    empty_clipboard_message,
    wants_clipboard,
)
from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import (
    CHAT_CANCELLED,
    CHAT_CHUNK,
    CHAT_COMPLETE,
    CHAT_ERROR,
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
    TELEMETRY_EVENT,
    TOOL_ERROR,
    TOOL_RESULT,
)
from ai_command_center.ui.capability_help import show_capability_help
from ai_command_center.ui.components.command_box import CommandBox
from ai_command_center.ui.components.sidebar import Sidebar
from ai_command_center.ui.components.top_bar import TopBar
from ai_command_center.ui.controller import UIController
from ai_command_center.ui.theme import tokens as T
from ai_command_center.ui.ui_queue import UIQueue
from ai_command_center.ui.layer.background_controller import BackgroundController
from ai_command_center.ui.layer.content_backdrop import ShellBackdrop
from ai_command_center.ui.layer.layer_stack import PageLayerStack
from ai_command_center.ui.motion.scheduler import MotionScheduler, MotionSignal
from ai_command_center.ui.views.chat_view import ChatView
from ai_command_center.ui.views.home_view import HomeView
from ai_command_center.ui.views.notes_view import NotesView
from ai_command_center.ui.views.placeholder import PlaceholderView
from ai_command_center.ui.views.plugins_view import PluginsView
from ai_command_center.ui.views.settings_view import SettingsView
from ai_command_center.ui.views.system_view import SystemView

VIEW_IDS: tuple[str, ...] = (
    "home",
    "chat",
    "notes",
    "system",
    "plugins",
    "settings",
)


class CommandPaletteApp(ctk.CTk):
    """1100×700 command palette — fade-in, deferred render, glass shell."""

    def __init__(self, bus: EventBus, state_store: AppStateStore) -> None:
        super().__init__()
        self._bus = bus
        self._controller = UIController(bus, state_store, self._queue_state_refresh)
        self._ui_queue = UIQueue(self)
        self._visible = False
        self._views: dict[str, PlaceholderView | ChatView | NotesView] = {}
        self._current_view = "home"
        self._active_request_id: str | None = None
        self._pending_user_text: str | None = None
        self._overlay_mode = "palette"
        self._bus_unsubs: list = []
        self._motion = MotionScheduler(bus)
        self._motion.subscribe(self._on_motion_signal)
        self._motion.start()
        self._background_ctrl = BackgroundController(bus)
        self._background_ctrl.start()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("AI Command Center")
        self.configure(fg_color=T.CANVAS_FALLBACK)
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
        self.update_idletasks()
        self.attributes("-alpha", 0.0)
        self._apply_state()
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

        self._command_host = ctk.CTkFrame(right, fg_color="transparent")
        self._command_host.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        self._command_box = CommandBox(
            self._command_host,
            on_submit=self._on_command,
            on_help=self._show_capability_help,
        )
        self._command_box.pack(fill="x")

        self._shell_backdrop = ShellBackdrop(right, "home")
        self._shell_backdrop.show()
        self._content = self._shell_backdrop

        self._show_view("home")

    def _ensure_view(
        self,
        view_id: str,
    ) -> (
        PlaceholderView
        | ChatView
        | NotesView
        | SettingsView
        | PluginsView
        | HomeView
        | SystemView
    ):
        if view_id not in self._views:
            shell = self._shell_backdrop
            page_host = shell.page_host
            if view_id == "home":
                home = HomeView(shell, shell=self._shell_backdrop, bus=self._bus)
                home.mount_bus(self._bus)
                self._views[view_id] = home
            elif view_id == "system":
                self._views[view_id] = SystemView(page_host)
            elif view_id == "chat":
                self._views[view_id] = ChatView(
                    page_host,
                    on_cancel=self._controller.publish_chat_cancel,
                )
            elif view_id == "notes":
                self._views[view_id] = NotesView(
                    page_host,
                    on_select=self._controller.publish_note_select,
                )
            elif view_id == "settings":
                self._views[view_id] = SettingsView(
                    page_host,
                    on_save=self._controller.request_settings_change,
                )
            elif view_id == "plugins":
                self._views[view_id] = PluginsView(
                    page_host,
                    on_toggle=self._controller.publish_plugin_toggle,
                )
            else:
                self._views[view_id] = PlaceholderView(page_host, view_id)
        return self._views[view_id]

    def _home_view(self) -> HomeView | None:
        view = self._views.get("home")
        return view if isinstance(view, HomeView) else None

    def _system_view(self) -> SystemView | None:
        view = self._views.get("system")
        return view if isinstance(view, SystemView) else None

    def _notes_view(self) -> NotesView | None:
        view = self._views.get("notes")
        return view if isinstance(view, NotesView) else None

    def _chat_view(self) -> ChatView | None:
        view = self._views.get("chat")
        return view if isinstance(view, ChatView) else None

    def _show_capability_help(self) -> None:
        show_capability_help(self)

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
            self._bus.subscribe(CHAT_COMPLETE, self._on_chat_complete)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(CHAT_CANCELLED, self._on_chat_cancelled)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(CHAT_ERROR, self._on_chat_error)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(OLLAMA_STATUS, self._on_ollama_status)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(CHAT_HISTORY_LOADED, self._on_chat_history_loaded)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(MODEL_SELECTED, self._on_model_selected)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(COMMAND_ROUTED, self._on_chat_context_routed)
        )

    def _on_chat_context_routed(self, event: Event) -> None:
        if event.source != "chat_handler":
            return
        if event.payload.get("status") != "processing":
            return
        sources = event.payload.get("context_sources") or []
        tokens = int(event.payload.get("token_estimate", 0))

        def update() -> None:
            chat = self._chat_view()
            if chat:
                chat.update_context_bar(list(sources), tokens)

        self._ui_queue.enqueue(update)

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

        def update() -> None:
            chat = self._chat_view()
            if chat:
                chat.finish_assistant(text)
            self._active_request_id = None
            self._top.update_status("ready", self._controller.snapshot().settings.default_model)

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
            self._navigate("chat")
            chat = self._chat_view()
            if chat:
                chat.show_error(message)
            self._active_request_id = None
            self._top.update_status("error", self._controller.snapshot().settings.default_model)

        self._ui_queue.enqueue(update)

    def _on_ollama_status(self, event: Event) -> None:
        online = bool(event.payload.get("online"))

        def update() -> None:
            phase = "ready" if online else "error"
            snap = self._controller.snapshot()
            self._top.update_status(phase, snap.settings.default_model)
            self._top.set_ollama_online(online)
            self._apply_footer_all(online=online)

        self._ui_queue.enqueue(update)

    def _on_model_selected(self, event: Event) -> None:
        model = str(event.payload.get("model", ""))

        def update() -> None:
            if model:
                self._top.update_status(self._controller.snapshot().phase, model)

        self._ui_queue.enqueue(update)

    def _wire_tool_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe(TOOL_RESULT, self._on_tool_result)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(TOOL_ERROR, self._on_tool_error)
        )

    def _on_tool_result(self, event: Event) -> None:
        tool = str(event.payload.get("tool", "tool"))
        output = str(event.payload.get("output", ""))

        def update() -> None:
            self._navigate("chat")
            chat = self._chat_view()
            if chat:
                chat.show_tool_output(tool, output, success=True)

        self._ui_queue.enqueue(update)

    def _on_tool_error(self, event: Event) -> None:
        tool = str(event.payload.get("tool", "tool"))
        message = str(event.payload.get("message", event.payload.get("error", "Tool failed")))

        def update() -> None:
            self._navigate("chat")
            chat = self._chat_view()
            if chat:
                chat.show_tool_output(tool, message, success=False)

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

        def update() -> None:
            self._navigate("chat")
            chat = self._chat_view()
            if chat:
                chat.show_system_message(f"Remembered: {label}")

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
            view = self._ensure_view("plugins")
            if isinstance(view, PluginsView):
                view.show_catalog(list(plugins))
            home = self._home_view()
            if home:
                home.apply_plugin_catalog({"plugins": list(plugins)})

        self._ui_queue.enqueue(update)

    def _on_plugin_error(self, event: Event) -> None:
        message = str(event.payload.get("message", "Plugin error"))

        def update() -> None:
            view = self._views.get("plugins")
            if isinstance(view, PluginsView):
                view.show_error(message)

        self._ui_queue.enqueue(update)

    def _wire_note_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe(NOTE_SEARCH_RESULTS, self._on_note_search_results)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(NOTE_SELECTED, self._on_note_selected)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(NOTE_CREATED, self._on_note_created)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(NOTE_ERROR, self._on_note_error)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(NOTE_INDEX_COMPLETE, self._on_note_index_complete)
        )

    def _wire_live_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe(SYSTEM_SNAPSHOT, self._on_system_snapshot)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(COMMAND_HISTORY, self._on_command_history)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(SYSTEM_EVENTS, self._on_system_event)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(TELEMETRY_EVENT, self._on_telemetry_event)
        )

    def _on_system_snapshot(self, event: Event) -> None:
        payload = dict(event.payload)

        def update() -> None:
            home = self._home_view()
            if home:
                home.apply_system_snapshot(payload)
            system = self._system_view()
            if system:
                system.apply_system_snapshot(payload)

        self._ui_queue.enqueue(update)

    def _on_command_history(self, event: Event) -> None:
        payload = dict(event.payload)

        def update() -> None:
            home = self._home_view()
            if home:
                home.apply_command_history(payload)

        self._ui_queue.enqueue(update)

    def _on_system_event(self, event: Event) -> None:
        payload = dict(event.payload)

        def update() -> None:
            home = self._home_view()
            if home:
                home.apply_telemetry_event(payload)
            system = self._system_view()
            if system:
                system.apply_system_event(payload)

        self._ui_queue.enqueue(update)

    def _on_telemetry_event(self, event: Event) -> None:
        payload = dict(event.payload)
        payload.setdefault("event", event.topic)

        def update() -> None:
            home = self._home_view()
            if home:
                home.apply_telemetry_event(payload)

        self._ui_queue.enqueue(update)

    def _on_note_index_complete(self, event: Event) -> None:
        payload = dict(event.payload)

        def update() -> None:
            home = self._home_view()
            if home:
                home.apply_note_index(payload)

        self._ui_queue.enqueue(update)

    def _on_motion_signal(self, signal: MotionSignal) -> None:
        def update() -> None:
            home = self._home_view()
            if home:
                home.apply_motion(
                    signal.primitive_id, signal.intensity, signal.payload
                )
            system = self._system_view()
            if system:
                system.apply_motion(signal.primitive_id, signal.intensity)

        self._ui_queue.enqueue(update)

    def _apply_footer_all(self, *, online: bool) -> None:
        snap = self._controller.snapshot()
        ollama_url = snap.settings.ollama_url
        vault = snap.settings.obsidian_vault_path or "—"
        for getter in (self._home_view, self._system_view):
            view = getter()
            if view and hasattr(view, "apply_footer"):
                view.apply_footer(
                    ollama_url=ollama_url,
                    vault_path=vault,
                    online=online,
                )

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
            self._attach_page_background(self._current_view)

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

    def _on_note_search_results(self, event: Event) -> None:
        query = str(event.payload.get("query", ""))
        results = event.payload.get("results") or []

        def update() -> None:
            self._navigate("notes")
            notes = self._notes_view()
            if notes:
                notes.show_results(query, list(results))

        self._ui_queue.enqueue(update)

    def _on_note_selected(self, event: Event) -> None:
        path = str(event.payload.get("path", ""))
        title = str(event.payload.get("title", path))

        def update() -> None:
            notes = self._notes_view()
            if notes:
                notes.show_selected(path, title)

        self._ui_queue.enqueue(update)

    def _on_note_created(self, event: Event) -> None:
        path = str(event.payload.get("path", ""))
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

    def _show_view(self, view_id: str) -> None:
        if view_id not in VIEW_IDS:
            view_id = "home"
        self._current_view = view_id
        for vid, view in self._views.items():
            if vid != view_id:
                view.pack_forget()
        view = self._ensure_view(view_id)
        if self._overlay_mode == "compact":
            self._shell_backdrop.hide()
        else:
            self._shell_backdrop.show()
        if view_id == "home":
            self._shell_backdrop.unmount_page_view()
            self._shell_backdrop.clear_zone_motion()
            self._shell_backdrop.set_home_zones_visible(True)
            view.pack_forget()
        else:
            self._shell_backdrop.set_home_zones_visible(False)
            self._shell_backdrop.clear_zone_motion()
            self._shell_backdrop.mount_page_view(view)
        self._sidebar.set_active(view_id)
        self._attach_page_background(view_id)

    def _attach_page_background(self, view_id: str) -> None:
        if self._overlay_mode != "compact":
            self._shell_backdrop.refresh()
        self._background_ctrl.attach(None)

    def _navigate(self, view_id: str) -> None:
        self._show_view(view_id)
        self._controller.publish_navigate(view_id)

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
            or lower in ("settings", "chat", "notes", "plugins", "home", "system")
        ):
            self._pending_user_text = text
        self._controller.publish_command(text, clipboard=clipboard)

    def _read_clipboard(self) -> str | None:
        try:
            data = self.clipboard_get()
            return str(data).strip() or None
        except Exception:
            return None

    def _queue_state_refresh(self) -> None:
        self._ui_queue.enqueue(self._apply_state)

    def _apply_state(self) -> None:
        snap = self._controller.snapshot()
        self._top.update_status(snap.phase, snap.settings.default_model)
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
        settings_view = self._views.get("settings")
        if isinstance(settings_view, SettingsView):
            settings_view.load_from_snapshot(snap.settings)
        self._apply_footer_all(online=True)

    def _fade_in(self, step: int = 0) -> None:
        alpha = min(1.0, (step + 1) / T.FADE_STEPS)
        self.attributes("-alpha", alpha)
        if step + 1 < T.FADE_STEPS:
            delay = max(1, T.FADE_IN_MS // T.FADE_STEPS)
            self.after(delay, lambda: self._fade_in(step + 1))

    def _fade_out(self, on_done) -> None:
        def step(n: int) -> None:
            alpha = max(0.0, 1.0 - (n + 1) / T.FADE_STEPS)
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
        self.after(T.FADE_IN_MS + 40, lambda: self._attach_page_background(self._current_view))
        self.after(T.FADE_IN_MS + 80, lambda: self._shell_backdrop.refresh())

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
