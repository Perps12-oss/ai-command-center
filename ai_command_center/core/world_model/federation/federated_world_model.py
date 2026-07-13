"""FederatedWorldModel — cross-workspace read-only query surface.

Merges node/edge results from multiple registered workspace repositories
into a single query result. All mutations always route to the primary
WorldModel; FederatedWorldModel is strictly read-only.

Architecture invariants (Invariant 13 — Host Platform Supremacy):
- ACC primary workspace is always the system of record.
- Remote workspaces provide capability only (read queries).
- No external workspace may override ACC node/edge state.
- Conflict detection is surfaced via FederationConflict events, not silently merged.
"""

from __future__ import annotations

import sqlite3
import time
from typing import Any

from ai_command_center.domain.federation import (
    FederatedNode,
    FederationQueryResult,
    FederationSyncRecord,
    WorkspaceDescriptor,
)
from ai_command_center.domain.world_model import Node
from ai_command_center.repositories.world_model_repository import (
    IWorldModelRepository,
    SQLiteWorldModelRepository,
)


class FederatedWorldModel:
    """Merges node queries across multiple workspace IWorldModelRepository instances.

    Usage:
        registry = WorkspaceRegistry(conn)
        federation = FederatedWorldModel(primary_repo=primary_wm_repo)

        # Register a secondary workspace
        federation.add_workspace(descriptor, secondary_repo)

        # Query across all workspaces
        result = federation.query_nodes(query="goal", limit=50)
    """

    def __init__(self, primary_repo: IWorldModelRepository) -> None:
        self._primary = primary_repo
        self._workspaces: dict[str, tuple[WorkspaceDescriptor, IWorldModelRepository]] = {}
        self._sync_records: dict[str, FederationSyncRecord] = {}

    def add_workspace(
        self, descriptor: WorkspaceDescriptor, repo: IWorldModelRepository
    ) -> None:
        """Register a workspace repository for federated queries."""
        self._workspaces[descriptor.workspace_id] = (descriptor, repo)
        self._sync_records[descriptor.workspace_id] = FederationSyncRecord(
            workspace_id=descriptor.workspace_id
        )

    def remove_workspace(self, workspace_id: str) -> bool:
        """Unregister a workspace. Returns True if it was registered."""
        if workspace_id in self._workspaces:
            del self._workspaces[workspace_id]
            self._sync_records.pop(workspace_id, None)
            return True
        return False

    def get_sync_status(self) -> list[FederationSyncRecord]:
        return list(self._sync_records.values())

    def query_nodes(
        self,
        *,
        query: str = "",
        node_type: str = "",
        limit: int = 100,
        include_primary: bool = True,
        workspace_ids: list[str] | None = None,
    ) -> FederationQueryResult:
        """Query nodes across all (or specified) registered workspaces.

        Args:
            query:          Text filter applied to node label/attributes.
            node_type:      Optional type filter.
            limit:          Max nodes per workspace.
            include_primary: Whether to include the primary workspace.
            workspace_ids:  If set, restrict to these workspace IDs.

        Returns:
            FederationQueryResult with merged nodes annotated by workspace.
        """
        t0 = time.monotonic()
        results: list[FederatedNode] = []
        errors: list[str] = []
        workspace_count = 0

        if include_primary:
            try:
                primary_nodes = self._query_repo(
                    self._primary, query=query, node_type=node_type, limit=limit
                )
                for node in primary_nodes:
                    results.append(FederatedNode(
                        node_id=node.id,
                        node_type=node.type,
                        label=_node_label(node),
                        workspace_id="primary",
                        workspace_name="Primary",
                        attributes=dict(node.attributes),
                    ))
                workspace_count += 1
            except Exception as exc:
                errors.append(f"primary: {exc}")

        for ws_id, (descriptor, repo) in self._workspaces.items():
            if workspace_ids is not None and ws_id not in workspace_ids:
                continue
            try:
                remote_nodes = self._query_repo(
                    repo, query=query, node_type=node_type, limit=limit
                )
                record = self._sync_records.get(ws_id)
                for node in remote_nodes:
                    results.append(FederatedNode(
                        node_id=node.id,
                        node_type=node.type,
                        label=_node_label(node),
                        workspace_id=ws_id,
                        workspace_name=descriptor.name,
                        attributes=dict(node.attributes),
                    ))
                if record:
                    record.mark_synced(len(remote_nodes), 0)
                workspace_count += 1
            except Exception as exc:
                errors.append(f"{ws_id}: {exc}")
                record = self._sync_records.get(ws_id)
                if record:
                    record.mark_unreachable(str(exc))

        duration_ms = (time.monotonic() - t0) * 1000
        return FederationQueryResult(
            query=query,
            nodes=tuple(results),
            workspace_count=workspace_count,
            duration_ms=duration_ms,
            errors=tuple(errors),
        )

    def detect_conflicts(self) -> list[dict[str, Any]]:
        """Detect nodes that exist in multiple workspaces with the same ID but different types.

        Returns a list of conflict descriptors. Callers publish
        FEDERATION_CONFLICT_DETECTED for each one.
        """
        seen: dict[str, list[tuple[str, str]]] = {}
        conflicts: list[dict[str, Any]] = []

        all_nodes = self.query_nodes(limit=1000, include_primary=True)
        for fn in all_nodes.nodes:
            if fn.node_id not in seen:
                seen[fn.node_id] = []
            seen[fn.node_id].append((fn.workspace_id, fn.node_type))

        for node_id, occurrences in seen.items():
            if len(occurrences) > 1:
                types = {t for _, t in occurrences}
                if len(types) > 1:
                    conflicts.append({
                        "node_id": node_id,
                        "occurrences": [
                            {"workspace_id": ws, "node_type": nt}
                            for ws, nt in occurrences
                        ],
                        "conflict_type": "type_mismatch",
                    })

        return conflicts

    @staticmethod
    def _query_repo(
        repo: IWorldModelRepository,
        *,
        query: str,
        node_type: str,
        limit: int,
    ) -> list[Node]:
        """Query a single repository. Falls back to listing from journal replay."""
        try:
            mutations = repo.replay_mutations(limit)
        except Exception:
            return []

        seen_ids: set[str] = set()
        nodes: list[Node] = []
        for mutation in mutations:
            payload = mutation.payload
            node_payload = payload.get("node") or payload
            node_id = str(node_payload.get("id") or "")
            if not node_id or node_id in seen_ids:
                continue
            seen_ids.add(node_id)
            nt = str(node_payload.get("type") or "resource")
            if node_type and nt != node_type:
                continue
            attrs = dict(node_payload.get("attributes") or {})
            label = _label_from_attrs(attrs) or node_id
            if query and query.lower() not in label.lower() and query.lower() not in node_id.lower():
                continue
            node = repo.get_node(node_id)
            if node is not None:
                nodes.append(node)

        return nodes[:limit]


def _node_label(node: Node) -> str:
    return _label_from_attrs(node.attributes) or node.id


def _label_from_attrs(attrs: dict[str, Any]) -> str:
    for key in ("name", "title", "label", "display_name"):
        val = attrs.get(key)
        if val:
            return str(val)
    return ""


def open_secondary_repo(db_path: str) -> SQLiteWorldModelRepository:
    """Open a read-only SQLiteWorldModelRepository for a secondary workspace DB."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return SQLiteWorldModelRepository(conn)
