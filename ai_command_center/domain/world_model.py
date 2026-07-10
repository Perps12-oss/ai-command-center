"""Brain World Model contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from ai_command_center.domain.correlation import CorrelationContext


def utc_now() -> datetime:
    return datetime.now(UTC)


class MutationType(str, Enum):
    CREATE_NODE = "create_node"
    UPDATE_NODE = "update_node"
    DELETE_NODE = "delete_node"
    CREATE_EDGE = "create_edge"
    DELETE_EDGE = "delete_edge"


@dataclass(frozen=True, slots=True)
class Node:
    id: str
    type: str
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "attributes": dict(self.attributes),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class Edge:
    id: str
    from_node_id: str
    to_node_id: str
    type: str
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "type": self.type,
            "attributes": dict(self.attributes),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class Mutation:
    id: str
    correlation: CorrelationContext
    type: MutationType
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "correlation": self.correlation.to_payload(),
            "type": self.type.value,
            "payload": dict(self.payload),
            "created_at": self.created_at.isoformat(),
        }
