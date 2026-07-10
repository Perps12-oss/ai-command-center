"""In-memory Brain World Model cache with repository-backed mutation apply."""

from __future__ import annotations

from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.world_model import Edge, Mutation, MutationType, Node
from ai_command_center.repositories.world_model_repository import IWorldModelRepository


class WorldModel:
    """Runtime-owned mutation gateway for workspace reality."""

    def __init__(self, repository: IWorldModelRepository) -> None:
        self._repository = repository
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, Edge] = {}
        self.recover()

    def recover(self, *, replay_limit: int = 5) -> list[Mutation]:
        """Rebuild the small hot cache from the mutation journal replay window."""
        mutations = self._repository.replay_mutations(replay_limit)
        self._nodes.clear()
        self._edges.clear()
        for mutation in mutations:
            self._apply_to_cache(mutation)
        return mutations

    def apply(self, mutation: Mutation) -> None:
        """Apply one mutation through the repository and then update cache."""
        self._repository.apply_mutation(mutation)
        self._apply_to_cache(mutation)

    def get_node(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id) or self._repository.get_node(node_id)

    def get_edges(self, node_id: str, direction: str = "both") -> list[Edge]:
        return self._repository.get_edges(node_id, direction)

    def _apply_to_cache(self, mutation: Mutation) -> None:
        if mutation.type in {MutationType.CREATE_NODE, MutationType.UPDATE_NODE}:
            node = _node_from_payload(mutation.payload)
            self._nodes[node.id] = node
        elif mutation.type == MutationType.DELETE_NODE:
            node_id = str(mutation.payload.get("node_id", ""))
            self._nodes.pop(node_id, None)
            self._edges = {
                edge_id: edge
                for edge_id, edge in self._edges.items()
                if edge.from_node_id != node_id and edge.to_node_id != node_id
            }
        elif mutation.type == MutationType.CREATE_EDGE:
            edge = _edge_from_payload(mutation.payload)
            self._edges[edge.id] = edge
        elif mutation.type == MutationType.DELETE_EDGE:
            self._edges.pop(str(mutation.payload.get("edge_id", "")), None)


def _node_from_payload(payload: dict) -> Node:
    raw = payload.get("node") if isinstance(payload.get("node"), dict) else payload
    return Node(
        id=str(raw.get("id", "")),
        type=str(raw.get("type", "resource")),
        attributes=dict(raw.get("attributes") or {}),
    )


def _edge_from_payload(payload: dict) -> Edge:
    raw = payload.get("edge") if isinstance(payload.get("edge"), dict) else payload
    return Edge(
        id=str(raw.get("id", "")),
        from_node_id=str(raw.get("from_node_id", "")),
        to_node_id=str(raw.get("to_node_id", "")),
        type=str(raw.get("type", "related")),
        attributes=dict(raw.get("attributes") or {}),
    )


def mutation_for_node(
    *,
    mutation_id: str,
    node: Node,
    correlation: CorrelationContext,
    mutation_type: MutationType = MutationType.UPDATE_NODE,
) -> Mutation:
    return Mutation(
        id=mutation_id,
        correlation=correlation,
        type=mutation_type,
        payload={"node": node.to_payload()},
    )
