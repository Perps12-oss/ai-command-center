"""WorkflowNodeInspector — inspectable details for workflow graph nodes."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.inspector.base_inspector import BaseInspector
from ai_command_center.ui.design_system import theme_v2 as T


class WorkflowNodeInspector(BaseInspector):
    """Display workflow node metadata selected on the graph canvas."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._title = ctk.CTkLabel(
            self,
            text="Workflow Node",
            font=(T.FONT_FAMILY, 12, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._title.pack(fill="x", padx=12, pady=(12, 6))
        self._body = ctk.CTkLabel(
            self,
            text="Select a node to inspect.",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="nw",
            justify="left",
        )
        self._body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def update(self, ref: InspectableRef) -> None:
        self._title.configure(text=ref.label or ref.ref_id or "Workflow Node")
        lines = [f"ID: {ref.ref_id}", f"Kind: {ref.kind}"]
        for key, value in ref.payload:
            lines.append(f"{key}: {value}")
        self._body.configure(text="\n".join(lines))


__all__ = ["WorkflowNodeInspector"]
