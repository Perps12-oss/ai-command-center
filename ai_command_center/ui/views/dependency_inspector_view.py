"""DependencyInspector — mutation journal, goal summary, and node dependency panel.

Architecture contract:
- Pure display widget. No repository access. No service calls.
- Reads from WorldModelState (AppState layer).
- Three tabs: Mutation Log, Active Goals, Node Dependencies.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import customtkinter as ctk

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import WORLD_MODEL_NODE_SELECTED
from ai_command_center.core.state.world_model_state import (
    GoalSummary,
    MutationLogEntry,
    WorldModelState,
)
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import (
    goal_state_color,
    mutation_type_color,
)
from ai_command_center.ui.widget_utils import clear_children


def _mut_color(mtype: str) -> str:
    return mutation_type_color(mtype)


def _goal_color(status: str) -> str:
    return goal_state_color(status)[0]


def _format_ts(ts: str) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%H:%M:%S")
    except ValueError:
        return ts[:8]


class _MutationRow(ctk.CTkFrame):
    def __init__(self, master: Any, entry: MutationLogEntry) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
        )
        color = _mut_color(entry.mutation_type)

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=5)

        header_row = ctk.CTkFrame(left, fg_color="transparent")
        header_row.pack(fill="x")

        ctk.CTkLabel(
            header_row,
            text=entry.mutation_type.replace("_", " ").upper(),
            font=(T.FONT_FAMILY, 9, "bold"),
            text_color=color,
            anchor="w",
        ).pack(side="left")

        if entry.timestamp:
            ctk.CTkLabel(
                header_row,
                text=_format_ts(entry.timestamp),
                font=T.FONT_MONO,
                text_color=T.TEXT_MUTED,
                anchor="e",
            ).pack(side="right")

        ctk.CTkLabel(
            left,
            text=entry.summary,
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x")

        if entry.goal_id:
            ctk.CTkLabel(
                left,
                text=f"goal: {entry.goal_id[:24]}",
                font=T.FONT_MONO,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x")


class _GoalRow(ctk.CTkFrame):
    def __init__(self, master: Any, goal: GoalSummary) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
        )
        color = _goal_color(goal.status)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=6)

        ctk.CTkLabel(
            row,
            text="🎯",
            font=(T.FONT_FAMILY, 13),
            text_color=color,
            width=20,
        ).pack(side="left")

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=4)

        ctk.CTkLabel(
            info,
            text=goal.title,
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            info,
            text=goal.status.upper(),
            font=(T.FONT_FAMILY, 9, "bold"),
            text_color=color,
            anchor="w",
        ).pack(fill="x")


class _DependencyNodeRow(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        label: str,
        role: str,
        node_id: str,
        on_navigate: Callable[[str], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
        )
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=8, pady=5)

        ctk.CTkLabel(
            left,
            text=role.upper(),
            font=(T.FONT_FAMILY, 9, "bold"),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            left,
            text=label,
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            left,
            text=node_id[:36],
            font=T.FONT_MONO,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x")

        ctk.CTkButton(
            self,
            text="Go",
            width=40,
            height=24,
            fg_color=T.BG_GLASS_BORDER,
            hover_color=T.ACCENT_DEFAULT,
            text_color=T.TEXT_SECONDARY,
            font=T.FONT_SMALL,
            command=lambda: on_navigate(node_id),
        ).pack(side="right", padx=8)


class DependencyInspectorView(ctk.CTkFrame):
    """Three-tab inspector: Mutation Log | Active Goals | Node Dependencies."""

    def __init__(self, master: Any, bus: EventBus, state: WorldModelState) -> None:
        super().__init__(master, fg_color=T.BG_DEEP)
        self._bus = bus
        self._state = state
        self._unsub: Callable[[], None] | None = None
        self._active_tab = "mutations"
        self._build()
        self._unsub = state.add_listener(self._on_state_change)
        self._render_active_tab()

    def destroy(self) -> None:
        if self._unsub is not None:
            self._unsub()
        super().destroy()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=T.BG_PANEL, height=48, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="🔍  Dependency Inspector",
            font=T.FONT_HEADER,
            text_color=T.TEXT_HEADING,
            anchor="w",
        ).pack(side="left", padx=16, pady=10)

        tab_bar = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0, height=36)
        tab_bar.pack(fill="x")
        tab_bar.pack_propagate(False)

        self._tab_buttons: dict[str, ctk.CTkButton] = {}
        tabs = [
            ("mutations", "📋 Mutation Log"),
            ("goals", "🎯 Active Goals"),
            ("deps", "⟷ Dependencies"),
        ]
        for key, label in tabs:
            btn = ctk.CTkButton(
                tab_bar,
                text=label,
                font=T.FONT_SMALL,
                height=30,
                corner_radius=0,
                fg_color=T.ACCENT_DEFAULT if key == self._active_tab else "transparent",
                hover_color=T.ACCENT_HOVER,
                text_color=T.TEXT_PRIMARY if key == self._active_tab else T.TEXT_MUTED,
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(side="left", padx=1)
            self._tab_buttons[key] = btn

        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True, padx=12, pady=(8, 12))

    def _switch_tab(self, key: str) -> None:
        self._active_tab = key
        for k, btn in self._tab_buttons.items():
            btn.configure(
                fg_color=T.ACCENT_DEFAULT if k == key else "transparent",
                text_color=T.TEXT_PRIMARY if k == key else T.TEXT_MUTED,
            )
        self._render_active_tab()

    def _on_state_change(self) -> None:
        self._render_active_tab()

    def _render_active_tab(self) -> None:
        clear_children(self._content)
        if self._active_tab == "mutations":
            self._render_mutations()
        elif self._active_tab == "goals":
            self._render_goals()
        else:
            self._render_deps()

    def _render_mutations(self) -> None:
        log = self._state.mutation_log
        if not log:
            ctk.CTkLabel(
                self._content,
                text="No mutations recorded yet.\nWorld Model changes will appear here.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                justify="center",
            ).pack(expand=True, pady=40)
            return

        count_lbl = ctk.CTkLabel(
            self._content,
            text=f"{len(log)} mutation{'s' if len(log) != 1 else ''} (newest first)",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        count_lbl.pack(fill="x", pady=(0, 6))

        scroll = ctk.CTkScrollableFrame(
            self._content,
            fg_color=T.BG_PANEL,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
            label_text="",
        )
        scroll.pack(fill="both", expand=True)

        for entry in log[:100]:
            _MutationRow(scroll, entry).pack(fill="x", pady=2, padx=2)

    def _render_goals(self) -> None:
        goals = self._state.active_goals
        if not goals:
            ctk.CTkLabel(
                self._content,
                text="No active goals.\nGoal lifecycle events will appear here.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                justify="center",
            ).pack(expand=True, pady=40)
            return

        ctk.CTkLabel(
            self._content,
            text=f"{len(goals)} active goal{'s' if len(goals) != 1 else ''}",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        scroll = ctk.CTkScrollableFrame(
            self._content,
            fg_color=T.BG_PANEL,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
            label_text="",
        )
        scroll.pack(fill="both", expand=True)

        for goal in goals:
            _GoalRow(scroll, goal).pack(fill="x", pady=2, padx=2)

    def _render_deps(self) -> None:
        node = self._state.selected_node
        edges = self._state.edges_for_selected

        if node is None:
            ctk.CTkLabel(
                self._content,
                text="Select a node in the World Explorer\nto inspect its dependencies.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                justify="center",
            ).pack(expand=True, pady=40)
            return

        ctk.CTkLabel(
            self._content,
            text=f"Dependencies for: {node.label}",
            font=T.FONT_HEADER,
            text_color=T.TEXT_HEADING,
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        if not edges:
            ctk.CTkLabel(
                self._content,
                text="No edges found for this node.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", pady=12)
            return

        scroll = ctk.CTkScrollableFrame(
            self._content,
            fg_color=T.BG_PANEL,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
            label_text="",
        )
        scroll.pack(fill="both", expand=True)

        for edge in edges:
            is_outbound = edge.from_node_id == node.node_id
            peer_id = edge.to_node_id if is_outbound else edge.from_node_id
            peer_label = (edge.to_label if is_outbound else edge.from_label) or peer_id
            role = f"→ {edge.edge_type}" if is_outbound else f"← {edge.edge_type}"
            _DependencyNodeRow(
                scroll,
                label=peer_label,
                role=role,
                node_id=peer_id,
                on_navigate=self._navigate_to,
            ).pack(fill="x", pady=2, padx=2)

    def _navigate_to(self, node_id: str) -> None:
        self._bus.publish(
            WORLD_MODEL_NODE_SELECTED,
            {"node_id": node_id},
            source="dependency_inspector_view",
        )
