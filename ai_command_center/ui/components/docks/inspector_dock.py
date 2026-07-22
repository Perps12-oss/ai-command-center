"""InspectorDock — layout shell that hosts InspectorHost in any workspace rail."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.inspector.base_inspector import BaseInspector
from ai_command_center.ui.components.inspector.inspector_host import InspectorHost
from ai_command_center.ui.design_system import theme_v2 as T


class InspectorDock(ctk.CTkFrame):
    """Workspace rail shell wrapping :class:`InspectorHost`.

    Used by chat, workflow graph, automation, and provider workspaces so every
    surface shares the same inspector chrome without embedding raw hosts.
    """

    def __init__(
        self,
        master: Any,
        *,
        on_navigate: Callable[[InspectableRef], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, **kwargs)
        self._host = InspectorHost(self, on_navigate=on_navigate)
        self._host.pack(fill="both", expand=True)

    @property
    def host(self) -> InspectorHost:
        return self._host

    def register(self, kind: str, inspector: BaseInspector) -> None:
        self._host.register(kind, inspector)

    def set_default(self, widget: ctk.CTkBaseClass) -> None:
        self._host.set_default(widget)

    def show(self, ref: InspectableRef) -> None:
        self._host.show(ref)

    def clear(self) -> None:
        self._host.clear()

    def set_collapsed(self, collapsed: bool) -> None:
        self._host.set_collapsed(collapsed)

    def toggle_collapsed(self) -> bool:
        return self._host.toggle_collapsed()


__all__ = ["InspectorDock"]
