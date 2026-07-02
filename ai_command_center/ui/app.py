"""Command palette main window — Replit UX shell over OneDrive architecture."""

from __future__ import annotations

from collections import deque

import customtkinter as ctk

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
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

    def __init__(self, bus: EventBus, state_store: AppStateStore) -> None:
        super().__init__()
        self._bus = bus
        self._controller = UIController(bus, state_store, self._queue_state_refresh)
        self._ui_queue = UIQueue(self)
        self._visible = False
        self._views: dict[str, object] = {}
        self._view_registry: dict[str, object] = {}
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
        self._register_views()
        self._build_layout()
        self._wire_all_events()
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


__all__ = ["CommandPaletteApp", "VIEW_IDS"]
