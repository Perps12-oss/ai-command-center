"""Immutable AppState snapshot for the World Model UI layer.

These frozen dataclasses are the AppState-layer counterparts of the mutable
WorldModelState objects in core/state/world_model_state.py.

Ownership contract (Resolution 3):
- Brain WorldModel (BrainRuntimeService / WorldModel) owns WORLD_MODEL_* topics.
- Workspace Entity Graph (EntityService / RelationshipService) owns ENTITY_* topics.
- Both are projected into WorldModelSnapshot via the AppState reducer.
  The two systems remain distinct; this snapshot is the read-only union view.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class NodeSnapshot:
    node_id: str = ""
    node_type: str = ""
    label: str = ""
    attributes: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class EdgeSnapshot:
    edge_id: str = ""
    from_node_id: str = ""
    to_node_id: str = ""
    edge_type: str = ""
    from_label: str = ""
    to_label: str = ""


@dataclass(frozen=True, slots=True)
class MutationSnapshot:
    mutation_id: str = ""
    mutation_type: str = ""
    correlation_id: str = ""
    goal_id: str = ""
    timestamp: str = ""
    summary: str = ""


@dataclass(frozen=True, slots=True)
class GoalSnapshot:
    goal_id: str = ""
    title: str = ""
    status: str = ""


_MAX_MUTATIONS = 200


@dataclass(frozen=True, slots=True)
class WorldModelSnapshot:
    """Immutable projection of the world model state for AppState consumers."""

    nodes: tuple[NodeSnapshot, ...] = ()
    edges: tuple[EdgeSnapshot, ...] = ()
    mutation_log: tuple[MutationSnapshot, ...] = ()
    goals: tuple[GoalSnapshot, ...] = ()
    selected_node_id: str = ""
    node_count: int = 0
    mutation_count: int = 0

    @property
    def selected_node(self) -> NodeSnapshot | None:
        if not self.selected_node_id:
            return None
        for n in self.nodes:
            if n.node_id == self.selected_node_id:
                return n
        return None

    @property
    def edges_for_selected(self) -> tuple[EdgeSnapshot, ...]:
        if not self.selected_node_id:
            return ()
        nid = self.selected_node_id
        return tuple(
            e for e in self.edges
            if e.from_node_id == nid or e.to_node_id == nid
        )

    @property
    def active_goals(self) -> tuple[GoalSnapshot, ...]:
        return tuple(
            g for g in self.goals
            if g.status not in {"complete", "failed", "cancelled"}
        )


def _attrs_to_pairs(raw: Any) -> tuple[tuple[str, str], ...]:
    if not isinstance(raw, dict):
        return ()
    return tuple((str(k), str(v)) for k, v in raw.items())
