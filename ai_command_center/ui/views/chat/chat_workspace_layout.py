"""ChatWorkspaceLayout — 3-pane docking layout for the chat workspace.

Fixed pixel widths:
  left  (280px) — ConversationList rail
  center(flex)  — message feed + composer
  right (320px) — InspectorPanel
"""
from __future__ import annotations

import tkinter as tk
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

_INSPECTOR_COLLAPSE_PX = 1100


class ChatWorkspaceLayout(ctk.CTkFrame):
    """3-pane PanedWindow layout for the chat workspace."""

    def __init__(
        self,
        master: Any,
        *,
        docking_enabled: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._docking_enabled = docking_enabled
        self._inspector_visible = True
        self._left_widget: ctk.CTkBaseClass | None = None
        self._center_widget: ctk.CTkBaseClass | None = None
        self._right_widget: ctk.CTkBaseClass | None = None

        if docking_enabled:
            self._build_docked()
        else:
            self._build_simple()

    def left_host(self) -> ctk.CTkFrame:
        return self._left_host

    def center_host(self) -> ctk.CTkFrame:
        return self._center_host

    def right_host(self) -> ctk.CTkFrame:
        return self._right_host

    def set_left(self, widget: ctk.CTkBaseClass) -> None:
        widget.pack(in_=self._left_host, fill="both", expand=True)
        self._left_widget = widget

    def set_center(self, widget: ctk.CTkBaseClass) -> None:
        widget.pack(in_=self._center_host, fill="both", expand=True)
        self._center_widget = widget

    def set_right(self, widget: ctk.CTkBaseClass) -> None:
        widget.pack(in_=self._right_host, fill="both", expand=True)
        self._right_widget = widget

    def toggle_inspector(self) -> bool:
        if not self._docking_enabled:
            return False
        self._inspector_visible = not self._inspector_visible
        self._apply_inspector_visibility()
        return self._inspector_visible

    def _build_simple(self) -> None:
        self._left_host = ctk.CTkFrame(self, fg_color="transparent", width=0)
        self._center_host = ctk.CTkFrame(self, fg_color="transparent")
        self._center_host.pack(fill="both", expand=True)
        self._right_host = ctk.CTkFrame(self, fg_color="transparent", width=0)

    def _build_docked(self) -> None:
        self._paned = tk.PanedWindow(
            self,
            orient=tk.HORIZONTAL,
            sashwidth=4,
            sashrelief=tk.FLAT,
            background=T.BG_GLASS_BORDER,
            handlesize=0,
            showhandle=False,
        )
        self._paned.pack(fill="both", expand=True)

        self._left_host = ctk.CTkFrame(
            self._paned,
            fg_color=T.SURFACE_PRIMARY,
            corner_radius=0,
            width=T.CHAT_HISTORY_WIDTH,
        )
        self._center_host = ctk.CTkFrame(
            self._paned,
            fg_color=T.APP_BG,
            corner_radius=0,
        )
        self._right_host = ctk.CTkFrame(
            self._paned,
            fg_color=T.SURFACE_PRIMARY,
            corner_radius=0,
            width=T.INSPECTOR_WIDTH,
        )

        self._paned.add(self._left_host, minsize=T.CHAT_HISTORY_WIDTH, stretch="never")
        self._paned.add(self._center_host, minsize=400, stretch="always")
        self._paned.add(self._right_host, minsize=T.INSPECTOR_WIDTH, stretch="never")

        self.bind("<Configure>", self._on_resize)
        self.after(100, self._set_initial_sashes)

    def _set_initial_sashes(self) -> None:
        total = self.winfo_width()
        if total < 100:
            self.after(150, self._set_initial_sashes)
            return
        left_px = T.CHAT_HISTORY_WIDTH
        right_start = max(left_px + 400, total - T.INSPECTOR_WIDTH)
        try:
            self._paned.sash_place(0, left_px, 0)
            self._paned.sash_place(1, right_start, 0)
        except tk.TclError:
            pass

    def _on_resize(self, event: tk.Event) -> None:
        if not self._docking_enabled:
            return
        width = event.width
        should_show = width >= _INSPECTOR_COLLAPSE_PX
        if should_show != self._inspector_visible:
            self._inspector_visible = should_show
            self._apply_inspector_visibility()

    def _apply_inspector_visibility(self) -> None:
        if not self._docking_enabled:
            return
        if self._inspector_visible:
            try:
                if self._right_host not in self._paned.panes():
                    self._paned.add(
                        self._right_host,
                        minsize=T.INSPECTOR_WIDTH,
                        stretch="never",
                    )
            except (tk.TclError, AttributeError):
                pass
        else:
            try:
                self._paned.remove(self._right_host)
            except (tk.TclError, AttributeError):
                pass


def make_chat_workspace_layout(master: Any) -> ChatWorkspaceLayout:
    """Factory — chat workspace always uses docked layout."""
    return ChatWorkspaceLayout(master, docking_enabled=True)
