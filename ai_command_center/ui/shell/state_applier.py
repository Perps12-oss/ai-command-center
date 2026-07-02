"""AppState → widget projection for the command palette shell."""

from __future__ import annotations

from ai_command_center.ui.design_system import theme_manager


class StateApplierMixin:
    """Applies AppState snapshots to shell widgets and catalog views."""

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

        self._apply_catalog_views(snap)

    def _apply_catalog_views(self, snap) -> None:
        """Render Memory, Notes, Plugins, and System views from AppState."""
        memory = self._memory_view()
        if memory:
            memory.load_from_appstate(snap)
            memory.update_injection_indicator(snap.memory_selected)

        notes = self._notes_view()
        if notes:
            notes.load_from_appstate(snap)

        plugins = self._plugins_view()
        if plugins:
            plugins.load_from_appstate(snap)

        system = self._system_view()
        if system:
            system.apply_system_snapshot(snap.system_snapshot)
            if snap.errors:
                system.load_errors(snap.errors)

        workspace = self._workspace_view()
        if workspace:
            workspace.load_from_appstate(snap)

        home = self._home_view()
        if home and snap.chat_history_count:
            home.update_stats(
                messages=snap.chat_history_count,
                memories=self._memory_count,
                notes=self._note_count,
            )
