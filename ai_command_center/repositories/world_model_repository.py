"""World Model repository adapter over the authoritative entity graph.

The World Model is the existing Workspace OS entity/relationship graph. This
adapter adds the Brain mutation journal without introducing parallel node/edge
storage tables.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Protocol

from ai_command_center.core.entity.entity import (
    ENTITY_SCHEMA_VERSION,
    ENTITY_TYPE_RESOURCE,
    Entity,
    validate_entity_type,
)
from ai_command_center.core.entity.entity_repository import EntityRepository
from ai_command_center.core.relationship.relationship import Relationship, RelationshipType
from ai_command_center.core.relationship.relationship_repository import RelationshipRepository
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.world_model import Edge, Mutation, MutationType, Node, utc_now

_WM_ID_KEY = "world_model_id"
_WM_TYPE_KEY = "world_model_type"
_WM_ATTRS_KEY = "world_model_attributes"
_WM_CREATED_KEY = "world_model_created_at"
_WM_UPDATED_KEY = "world_model_updated_at"


class IWorldModelRepository(Protocol):
    def apply_mutation(self, mutation: Mutation) -> None: ...
    def save_node(self, node: Node, correlation: CorrelationContext) -> None: ...
    def get_node(self, node_id: str) -> Node | None: ...
    def delete_node(self, node_id: str, correlation: CorrelationContext) -> None: ...
    def save_edge(self, edge: Edge, correlation: CorrelationContext) -> None: ...
    def get_edges(self, node_id: str, direction: str = "both") -> list[Edge]: ...
    def delete_edge(self, edge_id: str, correlation: CorrelationContext) -> None: ...
    def append_mutation(self, mutation: Mutation) -> None: ...
    def list_mutations(self, limit: int = 100, after_id: str = "") -> list[Mutation]: ...
    def replay_mutations(self, limit: int = 5) -> list[Mutation]: ...


class SQLiteWorldModelRepository:
    """Repository-owned adapter over EntityRepository/RelationshipRepository."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        entity_repo: EntityRepository | None = None,
        relationship_repo: RelationshipRepository | None = None,
    ) -> None:
        self._conn = conn
        self._entities = entity_repo or EntityRepository(conn)
        self._relationships = relationship_repo or RelationshipRepository(conn)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS mutation_journal (
                id TEXT PRIMARY KEY,
                correlation_id TEXT NOT NULL,
                goal_id TEXT NOT NULL DEFAULT '',
                action_id TEXT NOT NULL DEFAULT '',
                type TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_mutation_journal_created
            ON mutation_journal(created_at);
            CREATE INDEX IF NOT EXISTS idx_mutation_journal_correlation
            ON mutation_journal(correlation_id);
            """
        )
        self._conn.commit()

    @contextmanager
    def begin_transaction(self) -> Iterator[None]:
        """Atomic transaction context manager.

        Usage:
            with repo.begin_transaction():
                # journal first
                repo.append_mutation(mutation)
                # then storage
                repo._save_node_storage(node)
        """
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except Exception:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()

    def apply_mutation(self, mutation: Mutation) -> None:
        """Apply durable graph change and append the exact mutation record.

        Order of operations (CONSTITUTIONAL REQUIREMENT - Journal First):
        1. BEGIN transaction
        2. Journal append_mutation() FIRST
        3. Storage mutation
        4. COMMIT

        If storage fails, rollback removes the journal entry.
        """
        with self.begin_transaction():
            # 1. Journal FIRST (auditability requirement)
            self.append_mutation(mutation)
            # 2. Then storage mutation
            if mutation.type in {MutationType.CREATE_NODE, MutationType.UPDATE_NODE}:
                self._save_node_storage(_node_from_payload(mutation.payload))
            elif mutation.type == MutationType.DELETE_NODE:
                self._delete_node_storage(str(mutation.payload.get("node_id", "")))
            elif mutation.type == MutationType.CREATE_EDGE:
                self._save_edge_storage(_edge_from_payload(mutation.payload))
            elif mutation.type == MutationType.DELETE_EDGE:
                self._delete_edge_storage(str(mutation.payload.get("edge_id", "")))

    def save_node(self, node: Node, correlation: CorrelationContext) -> None:
        self.apply_mutation(
            Mutation(
                id=f"{correlation.correlation_id}:{node.id}:{node.updated_at.timestamp()}",
                correlation=correlation,
                type=MutationType.UPDATE_NODE,
                payload={"node": node.to_payload()},
                created_at=node.updated_at,
            )
        )

    def get_node(self, node_id: str) -> Node | None:
        entity = self._entities.get(_uuid_for_world_id(node_id))
        if entity is None:
            return None
        return _entity_to_node(entity)

    def delete_node(self, node_id: str, correlation: CorrelationContext) -> None:
        self.apply_mutation(
            Mutation(
                id=f"{correlation.correlation_id}:{node_id}:delete",
                correlation=correlation,
                type=MutationType.DELETE_NODE,
                payload={"node_id": node_id},
            )
        )

    def save_edge(self, edge: Edge, correlation: CorrelationContext) -> None:
        self.apply_mutation(
            Mutation(
                id=f"{correlation.correlation_id}:{edge.id}:{edge.created_at.timestamp()}",
                correlation=correlation,
                type=MutationType.CREATE_EDGE,
                payload={"edge": edge.to_payload()},
                created_at=edge.created_at,
            )
        )

    def get_edges(self, node_id: str, direction: str = "both") -> list[Edge]:
        entity_id = _uuid_for_world_id(node_id)
        direction = direction.lower()
        if direction == "in":
            relationships = self._relationships.get_by_target(entity_id)
        elif direction == "out":
            relationships = self._relationships.get_by_source(entity_id)
        else:
            relationships = [
                *self._relationships.get_by_source(entity_id),
                *self._relationships.get_by_target(entity_id),
            ]
        return [_relationship_to_edge(rel) for rel in relationships]

    def delete_edge(self, edge_id: str, correlation: CorrelationContext) -> None:
        self.apply_mutation(
            Mutation(
                id=f"{correlation.correlation_id}:{edge_id}:delete",
                correlation=correlation,
                type=MutationType.DELETE_EDGE,
                payload={"edge_id": edge_id},
            )
        )

    def append_mutation(self, mutation: Mutation) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO mutation_journal (
                id, correlation_id, goal_id, action_id, type, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mutation.id,
                mutation.correlation.correlation_id,
                mutation.correlation.goal_id,
                mutation.correlation.action_id,
                mutation.type.value,
                json.dumps(mutation.payload, sort_keys=True),
                mutation.created_at.isoformat(),
            ),
        )

    def list_mutations(self, limit: int = 100, after_id: str = "") -> list[Mutation]:
        if after_id:
            rows = self._conn.execute(
                """
                SELECT * FROM mutation_journal
                WHERE created_at > (
                    SELECT created_at FROM mutation_journal WHERE id = ?
                )
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (after_id, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM mutation_journal ORDER BY created_at ASC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_mutation(row) for row in rows]

    def replay_mutations(self, limit: int = 5) -> list[Mutation]:
        rows = self._conn.execute(
            """
            SELECT * FROM mutation_journal
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_row_to_mutation(row) for row in reversed(rows)]

    def _save_node_storage(self, node: Node) -> None:
        entity = _node_to_entity(node)
        if self._entities.get(entity.id) is None:
            self._entities.create(entity)
        else:
            self._entities.update(entity)

    def _delete_node_storage(self, node_id: str) -> None:
        if node_id:
            self._entities.delete(_uuid_for_world_id(node_id))

    def _save_edge_storage(self, edge: Edge) -> None:
        self._delete_edge_storage(edge.id)
        self._relationships.create(_edge_to_relationship(edge))

    def _delete_edge_storage(self, edge_id: str) -> None:
        if edge_id:
            self._relationships.delete(_uuid_for_world_id(f"edge:{edge_id}"))


def _uuid_for_world_id(value: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"acc-world-model:{value}")


def _entity_type_for_node(node_type: str) -> str:
    return node_type if validate_entity_type(node_type) else ENTITY_TYPE_RESOURCE


def _node_to_entity(node: Node) -> Entity:
    now = utc_now()
    title = str(node.attributes.get("name") or node.attributes.get("title") or node.id)
    metadata = dict(node.attributes)
    metadata.update(
        {
            _WM_ID_KEY: node.id,
            _WM_TYPE_KEY: node.type,
            _WM_ATTRS_KEY: dict(node.attributes),
            _WM_CREATED_KEY: node.created_at.isoformat(),
            _WM_UPDATED_KEY: node.updated_at.isoformat(),
        }
    )
    return Entity(
        id=_uuid_for_world_id(node.id),
        entity_type=_entity_type_for_node(node.type),
        title=title,
        description=str(node.attributes.get("description") or ""),
        created_at=node.created_at if node.created_at else now,
        updated_at=node.updated_at if node.updated_at else now,
        schema_version=ENTITY_SCHEMA_VERSION,
        metadata=metadata,
        relationships=[],
    )


def _entity_to_node(entity: Entity) -> Node:
    metadata = dict(entity.metadata)
    attrs = metadata.get(_WM_ATTRS_KEY)
    attributes = dict(attrs) if isinstance(attrs, dict) else metadata
    return Node(
        id=str(metadata.get(_WM_ID_KEY) or entity.id),
        type=str(metadata.get(_WM_TYPE_KEY) or entity.entity_type),
        attributes=attributes,
        created_at=_parse_datetime(
            str(metadata.get(_WM_CREATED_KEY) or entity.created_at.isoformat())
        ),
        updated_at=_parse_datetime(
            str(metadata.get(_WM_UPDATED_KEY) or entity.updated_at.isoformat())
        ),
    )


def _relationship_type_for_edge(edge_type: str) -> RelationshipType:
    try:
        return RelationshipType(edge_type)
    except ValueError:
        return RelationshipType.RELATED_TO


def _edge_to_relationship(edge: Edge) -> Relationship:
    metadata = dict(edge.attributes)
    metadata.update(
        {
            _WM_ID_KEY: edge.id,
            _WM_TYPE_KEY: edge.type,
            _WM_ATTRS_KEY: dict(edge.attributes),
            _WM_CREATED_KEY: edge.created_at.isoformat(),
            "from_node_id": edge.from_node_id,
            "to_node_id": edge.to_node_id,
        }
    )
    return Relationship(
        id=_uuid_for_world_id(f"edge:{edge.id}"),
        source_id=_uuid_for_world_id(edge.from_node_id),
        target_id=_uuid_for_world_id(edge.to_node_id),
        relationship_type=_relationship_type_for_edge(edge.type),
        created_at=edge.created_at,
        metadata=metadata,
    )


def _relationship_to_edge(relationship: Relationship) -> Edge:
    metadata = dict(relationship.metadata)
    attrs = metadata.get(_WM_ATTRS_KEY)
    attributes = dict(attrs) if isinstance(attrs, dict) else metadata
    return Edge(
        id=str(metadata.get(_WM_ID_KEY) or relationship.id),
        from_node_id=str(metadata.get("from_node_id") or relationship.source_id),
        to_node_id=str(metadata.get("to_node_id") or relationship.target_id),
        type=str(metadata.get(_WM_TYPE_KEY) or relationship.relationship_type.value),
        attributes=attributes,
        created_at=_parse_datetime(
            str(metadata.get(_WM_CREATED_KEY) or relationship.created_at.isoformat())
        ),
    )


def _node_from_payload(payload: dict[str, Any]) -> Node:
    raw = payload.get("node") if isinstance(payload.get("node"), dict) else payload
    return Node(
        id=str(raw.get("id", "")),
        type=str(raw.get("type", ENTITY_TYPE_RESOURCE)),
        attributes=dict(raw.get("attributes") or {}),
        created_at=_parse_datetime_or_now(raw.get("created_at")),
        updated_at=_parse_datetime_or_now(raw.get("updated_at")),
    )


def _edge_from_payload(payload: dict[str, Any]) -> Edge:
    raw = payload.get("edge") if isinstance(payload.get("edge"), dict) else payload
    return Edge(
        id=str(raw.get("id", "")),
        from_node_id=str(raw.get("from_node_id", "")),
        to_node_id=str(raw.get("to_node_id", "")),
        type=str(raw.get("type", RelationshipType.RELATED_TO.value)),
        attributes={
            **dict(raw.get("attributes") or {}),
            "from_node_id": str(raw.get("from_node_id", "")),
            "to_node_id": str(raw.get("to_node_id", "")),
        },
        created_at=_parse_datetime_or_now(raw.get("created_at")),
    )


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _parse_datetime_or_now(value: object) -> datetime:
    if not value:
        return utc_now()
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return utc_now()


def _loads(value: str | None) -> dict[str, Any]:
    raw = json.loads(value or "{}")
    return raw if isinstance(raw, dict) else {}


def _row_to_mutation(row: sqlite3.Row) -> Mutation:
    return Mutation(
        id=str(row["id"]),
        correlation=CorrelationContext(
            correlation_id=str(row["correlation_id"]),
            goal_id=str(row["goal_id"] or ""),
            action_id=str(row["action_id"] or ""),
        ),
        type=MutationType(str(row["type"])),
        payload=_loads(row["payload_json"]),
        created_at=_parse_datetime(str(row["created_at"])),
    )
