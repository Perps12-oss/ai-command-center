"""Cross-Workspace Federation domain contracts.

Defines the data contracts for federating multiple workspace World Models
into a unified query surface. Each registered workspace exposes its own
IWorldModelRepository; the FederatedWorldModel merges results at query time.

Architecture invariants:
- A workspace is the unit of federation (Invariant 13: host platform supremacy).
- External workspaces provide capability only. ACC owns system-of-record.
- No external workspace may become the authoritative node/edge store for ACC.
- Federation is additive (read-only from remotes); mutations always go to the
  primary workspace first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class WorkspaceRole(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    READ_ONLY = "read_only"


class SyncStatus(str, Enum):
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    CONFLICT = "conflict"
    UNREACHABLE = "unreachable"


@dataclass(frozen=True)
class WorkspaceDescriptor:
    """Identifies a registered workspace in the federation."""

    workspace_id: str
    name: str
    role: WorkspaceRole
    db_path: str
    tags: tuple[str, ...] = field(default_factory=tuple)
    registered_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_payload(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "role": self.role.value,
            "db_path": self.db_path,
            "tags": list(self.tags),
            "registered_at": self.registered_at.isoformat(),
        }

    @classmethod
    def from_payload(cls, p: dict[str, Any]) -> WorkspaceDescriptor:
        return cls(
            workspace_id=str(p["workspace_id"]),
            name=str(p.get("name") or ""),
            role=WorkspaceRole(str(p.get("role", "read_only"))),
            db_path=str(p.get("db_path") or ""),
            tags=tuple(p.get("tags") or []),
        )


@dataclass
class FederationSyncRecord:
    """Tracks sync state for a registered workspace."""

    workspace_id: str
    status: SyncStatus = SyncStatus.PENDING
    last_synced_at: datetime | None = None
    error: str | None = None
    node_count: int = 0
    edge_count: int = 0

    def mark_synced(self, node_count: int, edge_count: int) -> None:
        self.status = SyncStatus.SYNCED
        self.last_synced_at = datetime.now(UTC)
        self.node_count = node_count
        self.edge_count = edge_count
        self.error = None

    def mark_conflict(self, reason: str) -> None:
        self.status = SyncStatus.CONFLICT
        self.error = reason

    def mark_unreachable(self, reason: str) -> None:
        self.status = SyncStatus.UNREACHABLE
        self.error = reason


@dataclass(frozen=True)
class FederatedNode:
    """A node resolved from the federation, annotated with its source workspace."""

    node_id: str
    node_type: str
    label: str
    workspace_id: str
    workspace_name: str
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "label": self.label,
            "workspace_id": self.workspace_id,
            "workspace_name": self.workspace_name,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class FederationQueryResult:
    """Result of a cross-workspace federation query."""

    query: str
    nodes: tuple[FederatedNode, ...] = field(default_factory=tuple)
    workspace_count: int = 0
    duration_ms: float = 0.0
    errors: tuple[str, ...] = field(default_factory=tuple)

    def to_payload(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "nodes": [n.to_payload() for n in self.nodes],
            "workspace_count": self.workspace_count,
            "duration_ms": self.duration_ms,
            "errors": list(self.errors),
        }


__all__ = [
    "FederatedNode",
    "FederationQueryResult",
    "FederationSyncRecord",
    "SyncStatus",
    "WorkspaceDescriptor",
    "WorkspaceRole",
]
