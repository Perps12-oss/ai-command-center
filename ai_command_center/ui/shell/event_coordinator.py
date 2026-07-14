"""EventBus subscription wiring for the command palette shell."""

from __future__ import annotations

import os

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CHAT_EXPORT_ERROR,
    CHAT_EXPORT_RESULT,
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
    SERVICE_STATE_CHANGED,
    SYSTEM_EVENTS,
    SYSTEM_SNAPSHOT,
    TOOL_ERROR,
    TOOL_RESULT,
)
from ai_command_center.ui.shell.view_manager import VIEW_IDS
from ai_command_center.ui.views.plugins_view import PluginsView


class EventCoordinatorMixin:
    """Subscribes to EventBus topics and marshals updates onto the UI thread."""

    def _wire_all_events(self) -> None:
        self._wire_chat_events()
        self._wire_note_events()
        self._wire_overlay_events()
        self._wire_tool_events()
        self._wire_memory_events()
        self._wire_plugin_events()
        self._wire_navigation_events()
        self._wire_live_events()

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
            self._navigate(view, clear_chat_entity=(view == "chat"))

        self._ui_queue.enqueue(update)

    def _wire_chat_events(self) -> None:
        self._bus_unsubs.append(
            self._bus.subscribe(CHAT_EXPORT_RESULT, self._on_chat_export_result)
        )
        self._bus_unsubs.append(
            self._bus.subscribe(CHAT_EXPORT_ERROR, self._on_chat_export_error)
        )

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
        """Note search results are projected into AppState; view renders from there."""

        def update() -> None:
            self._navigate("notes")

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
            self._toast.show(
                f"Indexed {files} notes ({ms} ms)",
                kind="success",
                action=("View", lambda: self._navigate("notes")),
            )
            home = self._home_view()
            if home:
                home.update_vault(indexing=False, files=files, ms=ms)
            self._queue_state_refresh()

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
            self._toast.show(
                f"Remembered: {label}",
                kind="success",
                action=("View", lambda: self._navigate("memory")),
            )
            home = self._home_view()
            if home:
                home.update_memory(self._memory_count)

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
        summary = output[:120] + ("…" if len(output) > 120 else "")

        def update() -> None:
            chat = self._chat_view()
            if chat:
                chat.show_tool_output(tool, output, success=True)
            system = self._system_view()
            if system:
                system.push_tool_event(f"{tool}: {summary}")
            self._queue_state_refresh()

        self._ui_queue.enqueue(update)

    def _on_tool_error(self, event: Event) -> None:
        tool = str(event.payload.get("tool", ""))
        error = str(event.payload.get("error", ""))

        def update() -> None:
            chat = self._chat_view()
            if chat:
                chat.show_tool_output(tool, error, success=False)
            system = self._system_view()
            if system:
                system.push_tool_event(f"{tool}: {error[:120]}", is_error=True)
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
        """Plugin catalog is projected into AppState; view renders from there."""

        def update() -> None:
            self._navigate("plugins")

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
            self._queue_state_refresh()

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
        self._bus_unsubs.append(
            self._bus.subscribe(SERVICE_STATE_CHANGED, self._on_service_state_changed)
        )

    def _on_system_snapshot(self, event: Event) -> None:
        """Refresh system meters only; AppState owns structural projection."""
        if getattr(self, "_current_view", "") != "system":
            return
        payload = event.payload or {}

        def update() -> None:
            system = self._system_view()
            if system is None:
                return
            from ai_command_center.domain.system_snapshot import SystemSnapshot

            system.apply_system_snapshot(
                SystemSnapshot(
                    cpu_percent=float(payload.get("cpu_percent", 0.0)),
                    ram_percent=float(payload.get("ram_percent", 0.0)),
                    ollama_online=bool(payload.get("ollama_online", False)),
                    extra=dict(payload.get("extra", {})),
                )
            )

        self._ui_queue.enqueue(update)

    def _on_ollama_status(self, event: Event) -> None:
        online = bool(event.payload.get("online", False))
        model = str(event.payload.get("model", ""))

        def update() -> None:
            home = self._home_view()
            if home:
                home.update_ollama(online, model)
            self._queue_state_refresh()

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
            self._queue_state_refresh()

        self._ui_queue.enqueue(update)

    def _on_service_state_changed(self, event: Event) -> None:
        service = str(event.payload.get("service", ""))
        state = str(event.payload.get("state", ""))
        if not service or not state:
            return

        def update() -> None:
            system = self._system_view()
            if system:
                system.push_service_state(service, state)

        self._ui_queue.enqueue(update)

    def _on_model_selected(self, event: Event) -> None:
        model = str(event.payload.get("model", ""))
        resolved_by = str(event.payload.get("resolved_by", ""))
        indicator = f"{model} (routed)" if resolved_by == "model_router" else model

        def update() -> None:
            self._top.update_status("ready", indicator)
            chat = self._chat_view()
            if chat:
                chat.set_model(indicator)

        self._ui_queue.enqueue(update)
