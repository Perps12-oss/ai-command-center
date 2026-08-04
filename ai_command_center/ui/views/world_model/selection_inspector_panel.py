"""Art. 12 Selection Inspector — hosted on the universal InspectorDock rail."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.domain.world_model_snapshot import WorldModelSnapshot
from ai_command_center.ui.components.inspector.base_inspector import BaseInspector
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children

_META_KEYS = frozenset({"created_at", "updated_at", "workspace_id", "source", "metadata"})
_MACHINE_KEYS = frozenset({"node_id", "node_type", "label"})
_MACHINE_LABELS = {
    "node_id": "Entity ID",
    "node_type": "Type",
    "label": "Name",
}


def inspectable_ref_for_node(
    wm: WorldModelSnapshot, node_id: str
) -> InspectableRef | None:
    """Build a ``world_node`` inspect ref for ``node_id`` (need not be selected yet)."""
    node = next((n for n in wm.nodes if n.node_id == node_id), None)
    if node is None:
        return None
    edges = tuple(
        e
        for e in wm.edges
        if e.from_node_id == node_id or e.to_node_id == node_id
    )
    rel_count = len(edges)
    goal_links = [
        g.title or g.goal_id
        for g in wm.goals
        if g.goal_id
        and (
            g.goal_id in {v for _, v in node.attributes}
            or any(k.lower() == "goal_id" and v == g.goal_id for k, v in node.attributes)
        )
    ]
    if not goal_links and node.node_type == "goal":
        goal_links = [node.label or node.node_id]

    payload: list[tuple[str, str]] = [
        ("Entity ID", node.node_id),
        ("Name", node.label or "—"),
        ("Type", node.node_type or "—"),
        ("Relationship Count", str(rel_count)),
        ("Goal Links", ", ".join(goal_links) if goal_links else "—"),
    ]
    if node.attributes:
        payload.append(("__section__:Attributes", "Attributes"))
        for key, value in node.attributes:
            payload.append((key, value))
    else:
        payload.append(("Attributes", "—"))

    meta_pairs = [(k, v) for k, v in node.attributes if k.lower() in _META_KEYS]
    payload.append(("__section__:Metadata", "Metadata"))
    if meta_pairs:
        for key, value in meta_pairs:
            payload.append((key, value))
    else:
        payload.append(("Metadata", "—"))

    # Machine keys last for generic consumers; panel skips them when Art. 12 rows exist.
    payload.extend(
        (
            ("node_id", node.node_id),
            ("node_type", node.node_type or ""),
            ("label", node.label or ""),
        )
    )
    return InspectableRef(
        kind="world_node",
        ref_id=node.node_id,
        label=node.label or node.node_id,
        payload=tuple(payload),
    )


def inspectable_ref_from_world_model(wm: WorldModelSnapshot) -> InspectableRef | None:
    """Build a ``world_node`` inspect ref from the selected World Model node."""
    if not wm.selected_node_id:
        return None
    return inspectable_ref_for_node(wm, wm.selected_node_id)


class SelectionInspectorPanel(BaseInspector):
    """Art. 12 selection detail — registered as ``world_node`` on InspectorHost."""

    def __init__(self, master: Any) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.WORLD_TEAL,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        self._body = ctk.CTkScrollableFrame(
            self,
            fg_color=T.BG_DEEP,
            border_width=0,
            corner_radius=T.SMALL_RADIUS,
        )
        self._body.pack(fill="both", expand=True, padx=4, pady=4)
        self._empty()

    def update(self, ref: InspectableRef) -> None:
        clear_children(self._body)
        if ref.kind != "world_node" or not ref.payload:
            self._empty()
            return

        art12_rows = [
            (key, value)
            for key, value in ref.payload
            if key not in _MACHINE_KEYS
        ]
        if art12_rows:
            for key, value in art12_rows:
                if key.startswith("__section__:"):
                    title = key.split(":", 1)[1] or value
                    ctk.CTkLabel(
                        self._body,
                        text=title,
                        font=T.FONT_HEADER,
                        text_color=T.TEXT_SECONDARY,
                        anchor="w",
                    ).pack(fill="x", padx=4, pady=(10, 2))
                    continue
                self._row(key, value)
            return

        # Thin AppState payloads (machine keys only) — still show readable rows.
        payload = dict(ref.payload)
        shown = False
        for machine_key, label in _MACHINE_LABELS.items():
            value = str(payload.get(machine_key) or "").strip()
            if value:
                self._row(label, value)
                shown = True
        if not shown:
            self._empty()

    def apply_snapshot(self, wm: WorldModelSnapshot) -> None:
        """Compat helper — prefer InspectorDock.show(inspectable_ref_from_world_model)."""
        ref = inspectable_ref_from_world_model(wm)
        if ref is None:
            self._empty()
            return
        self.update(ref)

    def _empty(self) -> None:
        clear_children(self._body)
        ctk.CTkLabel(
            self._body,
            text=(
                "Nothing selected to inspect.\n"
                "Inspector details appear when you select an entity in the graph or list.\n"
                "Next: click an entity in Knowledge Graph or Entity Explorer."
            ),
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            justify="left",
        ).pack(pady=24)

    def _row(self, label: str, value: str) -> None:
        frame = ctk.CTkFrame(self._body, fg_color="transparent")
        frame.pack(fill="x", padx=4, pady=2)
        ctk.CTkLabel(
            frame,
            text=label,
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            width=120,
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            frame,
            text=value,
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
            wraplength=180,
        ).pack(side="left", fill="x", expand=True)


__all__ = [
    "SelectionInspectorPanel",
    "inspectable_ref_from_world_model",
    "inspectable_ref_for_node",
]
