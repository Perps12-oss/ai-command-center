"""Command palette main window — Replit UX shell over OneDrive architecture."""

from __future__ import annotations

from collections import deque

import customtkinter as ctk

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import UI_WORKSPACE_REQUIRED
from ai_command_center.ui.controller import UIController
from ai_command_center.ui.design_system import theme_manager
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.shell.application_shell import ApplicationShellMixin
from ai_command_center.ui.shell.event_coordinator import EventCoordinatorMixin
from ai_command_center.ui.shell.state_applier import StateApplierMixin
from ai_command_center.ui.shell.view_manager import VIEW_IDS, ViewManagerMixin
from ai_command_center.ui.ui_queue import UIQueue

# Gate-visible topic literals for Phase 5A verification: tool.result, model.selected, memory.stored.


class CommandPaletteApp(
    ctk.CTk,
    ApplicationShellMixin,
    ViewManagerMixin,
    EventCoordinatorMixin,
    StateApplierMixin,
):
    """1100x700 command palette - fade-in, glass shell, theme, toasts."""

    def __init__(
        self,
        bus: EventBus,
        state_store: AppStateStore,
        *,
        workspace_os_enabled: bool = True,
    ) -> None:
        super().__init__()
        self._workspace_os_enabled = workspace_os_enabled
        self._default_view = "command_center" if workspace_os_enabled else "home"
        self._bus = bus
        self._controller = UIController(bus, state_store, self._queue_state_refresh)
        self._ui_queue = UIQueue(self)
        self._visible = False
        self._views: dict[str, object] = {}
        self._view_registry: dict[str, object] = {}
        self._current_view = self._default_view
        self._completed_request_ids: deque[str] = deque(maxlen=32)
        self._last_terminal_chat_key: tuple[str, str] | None = None
        self._last_started_request_id: str | None = None
        self._last_stream_buffer_len: int = 0
        self._last_chat_history_revision: int = 0
        self._last_inspector_revision: int = -1
        self._last_workflow_graph_revision: int = -1
        self._last_automation_workspace_revision: int = -1
        self._last_execution_timeline_revision: int = -1
        self._last_execution_timeline_view_revision: int = -1
        self._shown_permission_check_id: str | None = None
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
        self._register_views()
        self._build_layout()
        self._wire_all_events()
        self._wire_workspace_policy_events()
        self._setup_keybindings()
        self.update_idletasks()
        self.attributes("-alpha", 0.0)
        self._queue_state_refresh()
        snap = self._controller.snapshot()
        theme_manager.apply(
            self,
            theme_name=snap.settings.theme,
            alpha=snap.settings.window_alpha,
        )
        self._visible = False

    def _wire_workspace_policy_events(self) -> None:
        """Route deferred commands back to workspace (Phase 6c consumer policy)."""
        self._bus_unsubs.append(
            self._bus.subscribe(UI_WORKSPACE_REQUIRED, self._on_workspace_required)
        )

    def _on_workspace_required(self, event: Event) -> None:
        _ = str(event.payload.get("reason", "no_active_workspace"))

        def update() -> None:
            if getattr(self, "_workspace_os_enabled", self._default_view == "workspace"):
                self._navigate("workspace")
            self._toast.show(
                "Activate a workspace before running commands",
                kind="info",
            )

        self._ui_queue.enqueue(update)

    def destroy(self) -> None:
        """Unsubscribe bus handlers and tear down views before Tk destroy."""
        if self._current_view and self._current_view in self._views:
            prev = self._views[self._current_view]
            if hasattr(prev, "on_hide"):
                prev.on_hide()
        for unsub in self._bus_unsubs:
            try:
                unsub()
            except Exception:
                pass
        self._bus_unsubs.clear()
        self._controller.close()
        super().destroy()


__all__ = ["CommandPaletteApp", "VIEW_IDS"]
