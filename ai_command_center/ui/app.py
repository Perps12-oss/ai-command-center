"""Command palette main window."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.ui.components.command_box import CommandBox
from ai_command_center.ui.components.sidebar import Sidebar
from ai_command_center.ui.components.top_bar import TopBar
from ai_command_center.ui.controller import UIController
from ai_command_center.ui.theme import tokens as T
from ai_command_center.ui.ui_queue import UIQueue
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
        self._views: dict[str, PlaceholderView | ChatView | NotesView | HomeView | SystemView] = {}
        self._current_view = "home"
        self._active_request_id: str | None = None
        self._pending_user_text: str | None = None
        self._overlay_mode = "palette"
        self._bus_unsubs: list = []

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

        self._command_host = ctk.CTkFrame(right, fg_color=T.BG_PANEL, corner_radius=0, height=80)
        self._command_host.pack(fill="x")
        self._command_host.pack_propagate(False)

        self._command_box = CommandBox(self._command_host, on_submit=self._on_command)
        self._command_box.pack(fill="x", padx=T.PAD, pady=10)

        self._content = ctk.CTkFrame(right, fg_color="transparent")
        self._content.pack(fill="both", expand=True)

        self._show_view("home")

    def _ensure_view(
        self, view_id: str
    ) -> PlaceholderView | ChatView | NotesView | HomeView | SystemView | SettingsView | PluginsView:
        if view_id not in self._views:
            if view_id == "home":
                self._views[view_id] = HomeView(self._content)
            elif view_id == "chat":
                self._views[view_id] = ChatView(
                    self._content,
                    on_cancel=self._controller.publish_chat_cancel,
                )
            elif view_id == "notes":
                self._views[view_id] = NotesView(
                    self._content,
                    on_select=self._controller.publish_note_select,
                )
            elif view_id == "system":
                self._views[view_id] = SystemView(self._content)
            elif view_id == "settings":
                self._views[view_id] = SettingsView(
                    self._content,
                    on_save=self._controller.request_settings_change,
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
        view = self._views.get("notes")
        return view if isinstance(view, NotesView) else None

    def _chat_view(self) -> ChatView | None:
        view = self._views.get("chat")
        return view if isinstance(view, ChatView) else None

    def _home_view(self) -> HomeView | None:
        view = self._views.get("home")
        return view if isinstance(view, HomeView) else None

    # ── chat event wiring ──────────────────────────────────────────────────────

    def _wire_chat_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe("chat.started", self._on_chat_started)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("chat.chunk", self._on_chat_chunk)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("chat.complete", self._on_chat_complete)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("chat.cancelled", self._on_chat_cancelled)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("chat.error", self._on_chat_error)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("ollama.status", self._on_ollama_status)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("chat.history_loaded", self._on_chat_history_loaded)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("model.selected", self._on_model_selected)
        )

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
            self._top.update_status(phase, self._controller.snapshot().settings.default_model)

        self._ui_queue.enqueue(update)

    def _on_model_selected(self, event: Event) -> None:
        model = str(event.payload.get("model", ""))

        def update() -> None:
            if model:
                self._top.update_status(self._controller.snapshot().phase, model)

        self._ui_queue.enqueue(update)

    # ── tool event wiring ─────────────────────────────────────────────────────

    def _wire_tool_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe("tool.result", self._on_tool_result)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("tool.error", self._on_tool_error)
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

    # ── memory event wiring ───────────────────────────────────────────────────

    def _wire_memory_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe("memory.stored", self._on_memory_stored)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("memory.selected", self._on_memory_selected)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("memory.error", self._on_memory_error)
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

    # ── plugin event wiring ───────────────────────────────────────────────────

    def _wire_plugin_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe("plugin.catalog", self._on_plugin_catalog)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("plugin.error", self._on_plugin_error)
        )

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

    # ── note event wiring ─────────────────────────────────────────────────────

    def _wire_note_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe("note.search_results", self._on_note_search_results)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("note.selected", self._on_note_selected)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("note.created", self._on_note_created)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("note.error", self._on_note_error)
        )

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

    # ── overlay event wiring ──────────────────────────────────────────────────

    def _wire_overlay_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe("overlay.show", self._on_overlay_show)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("overlay.anchor", self._on_overlay_anchor)
        )
        self._bus_unsubs.append(
            self._bus.subscribe("overlay.hide", self._on_overlay_hide)
        )

    def _on_overlay_show(self, event: Event) -> None:
        mode = str(event.payload.get("mode", "palette"))
        x = int(event.payload.get("x", 0) or 0)
        y = int(event.payload.get("y", 0) or 0)

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
        # Notify system view when hidden/shown
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
            # Legacy support for PlaceholderView if present
            if "home" in self._views and isinstance(self._views["home"], PlaceholderView):
                self._views["home"].set_extra(
                    f'Last: "{snap.last_command}" → {snap.last_command_intent or "pending"}'
                )

    # ── show / hide / toggle ───────────────────────────────────────────────────

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
