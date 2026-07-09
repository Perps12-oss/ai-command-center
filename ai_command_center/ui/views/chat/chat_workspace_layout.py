"""ChatWorkspaceLayout — 3-pane docking layout for the chat workspace.

Pane proportions (configurable, defaults to 18/62/20):
  left  (18%) — ConversationList rail
  center(62%) — message feed + composer
  right (20%) — InspectorDock (collapses below 900px width)

Gated behind Feature.FEATURE_DOCKING. When the flag is absent or False the
layout falls back to a single-pane wrapper so ChatView keeps its current
2-pane behaviour.

Reference: Open WebUI sidebar IA, Langflow docked inspector.

Architecture contract
─────────────────────
• Pure layout widget — owns no data, receives child widgets as arguments.
• No EventBus, service, or repository imports.
• Width collapse of inspector uses a <Configure> binding on the host.
"""
from __future__ import annotations

import tkinter as tk
from typing import Any

import customtkinter as ctk

from ai_command_center.core.feature.feature import Feature
from ai_command_center.ui.design_system import theme_v2 as T

_INSPECTOR_COLLAPSE_PX = 900
_PANE_LEFT_FRAC = 0.18
_PANE_CENTER_FRAC = 0.62
_PANE_RIGHT_FRAC = 0.20


class ChatWorkspaceLayout(ctk.CTkFrame):
    """3-pane PanedWindow layout for the chat workspace.

    Usage::

        layout = ChatWorkspaceLayout(parent, docking_enabled=True)
        layout.pack(fill="both", expand=True)
        layout.set_left(my_conversation_list)
        layout.set_center(my_message_feed)
        layout.set_right(my_inspector)
    """

    def __init__(
        self,
        master: Any,
        *,
        docking_enabled: bool = False,
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

    # ── public host accessors ────────────────────────────────────────────

    def left_host(self) -> ctk.CTkFrame:
        """Return the left-rail host frame."""
        return self._left_host

    def center_host(self) -> ctk.CTkFrame:
        """Return the center (message feed) host frame."""
        return self._center_host

    def right_host(self) -> ctk.CTkFrame:
        """Return the right inspector host frame."""
        return self._right_host

    def set_left(self, widget: ctk.CTkBaseClass) -> None:
        """Reparent *widget* into the left host."""
        widget.pack(in_=self._left_host, fill="both", expand=True)
        self._left_widget = widget

    def set_center(self, widget: ctk.CTkBaseClass) -> None:
        """Reparent *widget* into the center host."""
        widget.pack(in_=self._center_host, fill="both", expand=True)
        self._center_widget = widget

    def set_right(self, widget: ctk.CTkBaseClass) -> None:
        """Reparent *widget* into the right inspector host."""
        widget.pack(in_=self._right_host, fill="both", expand=True)
        self._right_widget = widget

    def toggle_inspector(self) -> bool:
        """Show or hide the inspector rail. Returns new visibility state."""
        if not self._docking_enabled:
            return False
        self._inspector_visible = not self._inspector_visible
        self._apply_inspector_visibility()
        return self._inspector_visible

    # ── private build ────────────────────────────────────────────────────

    def _build_simple(self) -> None:
        """Single-pane fallback — center fills all space."""
        self._left_host = ctk.CTkFrame(self, fg_color="transparent", width=0)
        self._center_host = ctk.CTkFrame(self, fg_color="transparent")
        self._center_host.pack(fill="both", expand=True)
        self._right_host = ctk.CTkFrame(self, fg_color="transparent", width=0)

    def _build_docked(self) -> None:
        """3-pane PanedWindow layout."""
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
            fg_color=T.BG_PANEL,
            corner_radius=0,
        )
        self._center_host = ctk.CTkFrame(
            self._paned,
            fg_color=T.BG_DEEP,
            corner_radius=0,
        )
        self._right_host = ctk.CTkFrame(
            self._paned,
            fg_color=T.BG_PANEL,
            corner_radius=0,
        )

        self._paned.add(self._left_host, minsize=140, stretch="never")
        self._paned.add(self._center_host, minsize=320, stretch="always")
        self._paned.add(self._right_host, minsize=160, stretch="never")

        self.bind("<Configure>", self._on_resize)
        self.after(100, self._set_initial_sashes)

    def _set_initial_sashes(self) -> None:
        total = self.winfo_width()
        if total < 100:
            self.after(150, self._set_initial_sashes)
            return
        left_px = int(total * _PANE_LEFT_FRAC)
        right_start = int(total * (_PANE_LEFT_FRAC + _PANE_CENTER_FRAC))
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
                    self._paned.add(self._right_host, minsize=160, stretch="never")
            except (tk.TclError, AttributeError):
                pass
        else:
            try:
                self._paned.remove(self._right_host)
            except (tk.TclError, AttributeError):
                pass


def make_chat_workspace_layout(master: Any) -> ChatWorkspaceLayout:
    """Factory that checks Feature.FEATURE_DOCKING and creates the layout."""
    try:
        from ai_command_center.core.feature.feature_registry import FeatureRegistry
        docking = FeatureRegistry.instance().is_enabled(Feature.FEATURE_DOCKING)
    except Exception:
        docking = False
    return ChatWorkspaceLayout(master, docking_enabled=docking)
