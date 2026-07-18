"""Shared selection state for graph canvases."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GraphSelection:
    """Tracks selected node and edge ids (multi-select capable)."""

    selected_node_ids: set[str] = field(default_factory=set)
    selected_edge_ids: set[str] = field(default_factory=set)

    def clear(self) -> None:
        self.selected_node_ids.clear()
        self.selected_edge_ids.clear()

    def select_node(self, node_id: str, *, additive: bool = False) -> None:
        if not additive:
            self.selected_node_ids.clear()
            self.selected_edge_ids.clear()
        if node_id in self.selected_node_ids and additive:
            self.selected_node_ids.discard(node_id)
        else:
            self.selected_node_ids.add(node_id)

    def select_edge(self, edge_id: str, *, additive: bool = False) -> None:
        if not additive:
            self.selected_edge_ids.clear()
            self.selected_node_ids.clear()
        if edge_id in self.selected_edge_ids and additive:
            self.selected_edge_ids.discard(edge_id)
        else:
            self.selected_edge_ids.add(edge_id)

    def select_nodes(self, node_ids: set[str]) -> None:
        self.selected_edge_ids.clear()
        self.selected_node_ids = set(node_ids)

    def is_node_selected(self, node_id: str) -> bool:
        return node_id in self.selected_node_ids

    def is_edge_selected(self, edge_id: str) -> bool:
        return edge_id in self.selected_edge_ids

    def copy_node_ids(self) -> set[str]:
        return set(self.selected_node_ids)

    def copy_edge_ids(self) -> set[str]:
        return set(self.selected_edge_ids)


__all__ = ["GraphSelection"]
