"""Reusable inspector host shell primitive."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.inspector.agent_inspector import AgentInspector
from ai_command_center.ui.components.inspector.artifact_inspector import ArtifactInspector
from ai_command_center.ui.components.inspector.base_inspector import BaseInspector
from ai_command_center.ui.components.inspector.decision_inspector import DecisionInspector
from ai_command_center.ui.components.inspector.execution_event_inspector import ExecutionEventInspector
from ai_command_center.ui.components.inspector.goal_inspector import GoalInspector
from ai_command_center.ui.components.inspector.memory_inspector import MemoryInspector
from ai_command_center.ui.components.inspector.message_inspector import MessageInspector
from ai_command_center.ui.components.inspector.note_inspector import NoteInspector
from ai_command_center.ui.components.inspector.provider_inspector import ProviderInspector
from ai_command_center.ui.components.inspector.task_inspector import TaskInspector
from ai_command_center.ui.components.inspector.world_node_inspector import WorldNodeInspector
from ai_command_center.ui.design_system import theme_v2 as T

_EMPTY_SELECTION_HINT = "Select an object to inspect."


class InspectorHost(ctk.CTkFrame):
    """Registry-driven host for inspectable ACC objects."""

    def __init__(
        self,
        master: Any,
        *,
        on_navigate: Callable[[InspectableRef], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, **kwargs)
        self._registry: dict[str, BaseInspector] = {}
        self._default_widget: ctk.CTkBaseClass | None = None
        self._visible_widget: ctk.CTkBaseClass | None = None
        self._collapsed = False
        self._current_ref: InspectableRef | None = None
        self._on_navigate = on_navigate
        self._navigate_btn: ctk.CTkButton | None = None

        self._header = ctk.CTkFrame(self, fg_color=T.BG_GLASS, corner_radius=0, height=36)
        self._header.pack(fill="x")
        self._header.pack_propagate(False)

        self._title = ctk.CTkLabel(
            self._header,
            text="Inspector",
            font=(T.FONT_FAMILY, 11, "bold"),
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        self._title.pack(side="left", padx=10, pady=8, fill="x", expand=True)

        if self._on_navigate is not None:
            self._navigate_btn = ctk.CTkButton(
                self._header,
                text="→",
                width=26,
                height=24,
                font=(T.FONT_FAMILY, 10),
                fg_color="transparent",
                hover_color=T.BG_GLASS_BORDER,
                text_color=T.TEXT_MUTED,
                corner_radius=4,
                command=self._handle_navigate,
                state="disabled",
            )
            self._navigate_btn.pack(side="right", padx=(8, 4), pady=6)

        self._toggle = ctk.CTkButton(
            self._header,
            text="▾",
            width=26,
            height=24,
            font=(T.FONT_FAMILY, 10),
            fg_color="transparent",
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=4,
            command=self.toggle_collapsed,
        )
        self._toggle.pack(side="right", padx=8, pady=6)

        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="both", expand=True)

        self._empty_hint = ctk.CTkLabel(
            self._body,
            text=_EMPTY_SELECTION_HINT,
            font=T.FONT_BODY,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._empty_hint.pack(fill="both", expand=True, padx=12, pady=12)

        self.register("message", MessageInspector(self._body))
        self.register("artifact", ArtifactInspector(self._body))
        self.register("provider", ProviderInspector(self._body))
        self.register("decision", DecisionInspector(self._body))
        self.register("goal", GoalInspector(self._body))
        self.register("task", TaskInspector(self._body))
        self.register("memory", MemoryInspector(self._body))
        self.register("agent", AgentInspector(self._body))
        self.register("note", NoteInspector(self._body))
        self.register("world_node", WorldNodeInspector(self._body))
        self.register("execution_event", ExecutionEventInspector(self._body))

    def set_default(self, widget: ctk.CTkBaseClass) -> None:
        self._default_widget = widget
        self._empty_hint.pack_forget()
        widget.pack(in_=self._body, fill="both", expand=True)
        self._set_visible(widget)

    def register(self, kind: str, inspector: BaseInspector) -> None:
        self._registry[kind] = inspector

    def show(self, ref: InspectableRef) -> None:
        inspector = self._registry.get(ref.kind)
        if inspector is None:
            self._show_empty_hint(f"No inspector registered for {ref.kind!r}.")
            self._current_ref = ref
            self._title.configure(text=ref.label or ref.kind.title() or "Inspector")
            self._update_navigate_button()
            return
        self._current_ref = ref
        self._title.configure(text=ref.label or ref.kind.title() or "Inspector")
        self._hide_current()
        inspector.update(ref)
        inspector.pack(in_=self._body, fill="both", expand=True)
        self._set_visible(inspector)
        self._update_navigate_button()

    def clear(self) -> None:
        self._current_ref = None
        self._title.configure(text="Inspector")
        self._show_default()
        self._update_navigate_button()

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        if collapsed:
            self._body.pack_forget()
            self._toggle.configure(text="▸")
        else:
            self._body.pack(fill="both", expand=True)
            self._toggle.configure(text="▾")

    def toggle_collapsed(self) -> bool:
        self.set_collapsed(not self._collapsed)
        return self._collapsed

    def _set_visible(self, widget: ctk.CTkBaseClass) -> None:
        self._visible_widget = widget

    def _hide_current(self) -> None:
        if self._visible_widget is not None:
            self._visible_widget.pack_forget()
            self._visible_widget = None

    def _show_default(self) -> None:
        self._hide_current()
        if self._default_widget is not None:
            self._default_widget.pack(in_=self._body, fill="both", expand=True)
            self._set_visible(self._default_widget)
            self._update_navigate_button()
            return
        self._show_empty_hint(_EMPTY_SELECTION_HINT)

    def _show_empty_hint(self, message: str) -> None:
        self._hide_current()
        self._empty_hint.configure(text=message)
        self._empty_hint.pack(fill="both", expand=True, padx=12, pady=12)
        self._set_visible(self._empty_hint)
        self._update_navigate_button()

    def _handle_navigate(self) -> None:
        if self._on_navigate is not None and self._current_ref is not None:
            self._on_navigate(self._current_ref)

    def _update_navigate_button(self) -> None:
        if self._navigate_btn is None:
            return
        if self._current_ref is not None:
            self._navigate_btn.configure(state="normal")
        else:
            self._navigate_btn.configure(state="disabled")


__all__ = ["InspectorHost"]
