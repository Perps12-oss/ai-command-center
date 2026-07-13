"""WorldModelState — AppState projection for the World Model UI layer.

Subscribes to World Model EventBus topics and projects node/edge/mutation
data into observable lists consumed by the three UI panels:

  WorldExplorerView   — reads nodes, selected_node_id
  RelationshipView    — reads edges for selected_node_id
  DependencyInspector — reads mutation_log, goal summary
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import (
    ENTITY_CREATED,
    ENTITY_DELETED,
    ENTITY_UPDATED,
    GOAL_ACTIVATED,
    GOAL_COMPLETED,
    GOAL_FAILED,
    GOAL_SUBMITTED,
    RUNTIME_WORLD_MODEL_APPLY_COMPLETED,
    WORLD_MODEL_GRAPH_REFRESHED,
    WORLD_MODEL_MUTATION_APPLIED,
    WORLD_MODEL_NODE_DESELECTED,
    WORLD_MODEL_NODE_SELECTED,
)

_MAX_MUTATION_LOG = 200


@dataclass
class NodeSummary:
    node_id: str
    node_type: str
    label: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class EdgeSummary:
    edge_id: str
    from_node_id: str
    to_node_id: str
    edge_type: str
    from_label: str = ""
    to_label: str = ""


@dataclass
class MutationLogEntry:
    mutation_id: str
    mutation_type: str
    correlation_id: str
    goal_id: str
    timestamp: str
    summary: str


@dataclass
class GoalSummary:
    goal_id: str
    title: str
    status: str


class WorldModelState:
    """Observable state for the World Model UI panels.

    Architecture contract:
    - Subscribes to EventBus only (no repository access).
    - UI panels read from this state object, never from repositories directly.
    - All mutations flow through EventBus → WorldModelState → UI (read).
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._nodes: dict[str, NodeSummary] = {}
        self._edges: list[EdgeSummary] = []
        self._mutation_log: list[MutationLogEntry] = []
        self._goals: dict[str, GoalSummary] = {}
        self._selected_node_id: str | None = None
        self._listeners: list[Callable[[], None]] = []
        self._unsubs: list[Callable[[], None]] = []
        self._wire()

    def _wire(self) -> None:
        self._unsubs = [
            self._bus.subscribe(ENTITY_CREATED, self._on_entity_created),
            self._bus.subscribe(ENTITY_UPDATED, self._on_entity_updated),
            self._bus.subscribe(ENTITY_DELETED, self._on_entity_deleted),
            self._bus.subscribe(RUNTIME_WORLD_MODEL_APPLY_COMPLETED, self._on_mutation_applied),
            self._bus.subscribe(WORLD_MODEL_MUTATION_APPLIED, self._on_mutation_applied),
            self._bus.subscribe(WORLD_MODEL_NODE_SELECTED, self._on_node_selected),
            self._bus.subscribe(WORLD_MODEL_NODE_DESELECTED, self._on_node_deselected),
            self._bus.subscribe(WORLD_MODEL_GRAPH_REFRESHED, self._on_graph_refreshed),
            self._bus.subscribe(GOAL_SUBMITTED, self._on_goal_event),
            self._bus.subscribe(GOAL_ACTIVATED, self._on_goal_event),
            self._bus.subscribe(GOAL_COMPLETED, self._on_goal_event),
            self._bus.subscribe(GOAL_FAILED, self._on_goal_event),
        ]

    def dispose(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    def add_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register a change listener. Returns an unsubscribe callable."""
        self._listeners.append(callback)

        def _remove() -> None:
            self._listeners.remove(callback)

        return _remove

    def _notify(self) -> None:
        for cb in list(self._listeners):
            try:
                cb()
            except Exception:
                pass

    # ── public read API ───────────────────────────────────────────────────

    @property
    def nodes(self) -> list[NodeSummary]:
        return list(self._nodes.values())

    @property
    def selected_node_id(self) -> str | None:
        return self._selected_node_id

    @property
    def selected_node(self) -> NodeSummary | None:
        if self._selected_node_id is None:
            return None
        return self._nodes.get(self._selected_node_id)

    @property
    def edges_for_selected(self) -> list[EdgeSummary]:
        if self._selected_node_id is None:
            return []
        nid = self._selected_node_id
        return [e for e in self._edges if e.from_node_id == nid or e.to_node_id == nid]

    @property
    def mutation_log(self) -> list[MutationLogEntry]:
        return list(reversed(self._mutation_log))

    @property
    def active_goals(self) -> list[GoalSummary]:
        return [g for g in self._goals.values() if g.status not in {"complete", "failed", "cancelled"}]

    # ── EventBus handlers ─────────────────────────────────────────────────

    def _on_entity_created(self, event: Event) -> None:
        p = event.payload
        node_id = str(p.get("id") or p.get("entity_id") or "")
        if not node_id:
            return
        self._nodes[node_id] = NodeSummary(
            node_id=node_id,
            node_type=str(p.get("entity_type") or p.get("type") or "resource"),
            label=str(p.get("name") or p.get("title") or node_id),
            attributes=dict(p.get("attributes") or {}),
        )
        self._notify()

    def _on_entity_updated(self, event: Event) -> None:
        p = event.payload
        node_id = str(p.get("id") or p.get("entity_id") or "")
        if not node_id:
            return
        existing = self._nodes.get(node_id)
        self._nodes[node_id] = NodeSummary(
            node_id=node_id,
            node_type=str(p.get("entity_type") or p.get("type") or (existing.node_type if existing else "resource")),
            label=str(p.get("name") or p.get("title") or (existing.label if existing else node_id)),
            attributes=dict(p.get("attributes") or (existing.attributes if existing else {})),
        )
        self._notify()

    def _on_entity_deleted(self, event: Event) -> None:
        node_id = str(event.payload.get("id") or event.payload.get("entity_id") or "")
        self._nodes.pop(node_id, None)
        self._edges = [e for e in self._edges if e.from_node_id != node_id and e.to_node_id != node_id]
        if self._selected_node_id == node_id:
            self._selected_node_id = None
        self._notify()

    def _on_mutation_applied(self, event: Event) -> None:
        p = event.payload
        mutation = p.get("mutation") or p
        entry = MutationLogEntry(
            mutation_id=str(mutation.get("id") or mutation.get("mutation_id") or ""),
            mutation_type=str(mutation.get("type") or "unknown"),
            correlation_id=str(mutation.get("correlation_id") or ""),
            goal_id=str(mutation.get("goal_id") or ""),
            timestamp=str(mutation.get("created_at") or mutation.get("timestamp") or ""),
            summary=_mutation_summary(mutation),
        )
        self._mutation_log.append(entry)
        if len(self._mutation_log) > _MAX_MUTATION_LOG:
            self._mutation_log = self._mutation_log[-_MAX_MUTATION_LOG:]
        self._notify()

    def _on_node_selected(self, event: Event) -> None:
        self._selected_node_id = str(event.payload.get("node_id") or "")
        self._notify()

    def _on_node_deselected(self, _event: Event) -> None:
        self._selected_node_id = None
        self._notify()

    def _on_graph_refreshed(self, event: Event) -> None:
        nodes = event.payload.get("nodes") or []
        edges = event.payload.get("edges") or []
        self._nodes = {}
        for n in nodes:
            nid = str(n.get("id") or "")
            if nid:
                self._nodes[nid] = NodeSummary(
                    node_id=nid,
                    node_type=str(n.get("type") or "resource"),
                    label=str(n.get("label") or n.get("name") or nid),
                    attributes=dict(n.get("attributes") or {}),
                )
        self._edges = [
            EdgeSummary(
                edge_id=str(e.get("id") or ""),
                from_node_id=str(e.get("from_node_id") or ""),
                to_node_id=str(e.get("to_node_id") or ""),
                edge_type=str(e.get("type") or "related"),
                from_label=str(e.get("from_label") or ""),
                to_label=str(e.get("to_label") or ""),
            )
            for e in edges
        ]
        self._notify()

    def _on_goal_event(self, event: Event) -> None:
        p = event.payload
        goal = p.get("goal") or p
        goal_id = str(goal.get("id") or goal.get("goal_id") or p.get("goal_id") or "")
        if not goal_id:
            return
        status = str(goal.get("status") or "submitted")
        title = str(goal.get("title") or goal_id)
        self._goals[goal_id] = GoalSummary(goal_id=goal_id, title=title, status=status)
        self._notify()


def _mutation_summary(mutation: dict) -> str:
    mtype = str(mutation.get("type") or "")
    payload = mutation.get("payload") or {}
    node = payload.get("node") or {}
    node_id = str(node.get("id") or payload.get("node_id") or "")
    edge_id = str(payload.get("edge_id") or "")
    if node_id:
        return f"{mtype} → node:{node_id}"
    if edge_id:
        return f"{mtype} → edge:{edge_id}"
    return mtype
