"""SQLite-backed Brain World Model repository and mutation journal."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Protocol

from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.world_model import Edge, Mutation, MutationType, Node


class IWorldModelRepository(Protocol):
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
    """Repository-owned SQLite implementation of IWorldModelRepository."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS world_nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                attributes_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_world_nodes_type ON world_nodes(type);

            CREATE TABLE IF NOT EXISTS world_edges (
                id TEXT PRIMARY KEY,
                from_node_id TEXT NOT NULL,
                to_node_id TEXT NOT NULL,
                type TEXT NOT NULL,
                attributes_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_world_edges_from ON world_edges(from_node_id);
            CREATE INDEX IF NOT EXISTS idx_world_edges_to ON world_edges(to_node_id);

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
        self._conn.execute("BEGIN")
        try:
            yield
        except Exception:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()

    def save_node(self, node: Node, correlation: CorrelationContext) -> None:
        self._conn.execute(
            """
            INSERT INTO world_nodes (id, type, attributes_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                type = excluded.type,
                attributes_json = excluded.attributes_json,
                updated_at = excluded.updated_at
            """,
            (
                node.id,
                node.type,
                json.dumps(node.attributes, sort_keys=True),
                node.created_at.isoformat(),
                node.updated_at.isoformat(),
            ),
        )
        self.append_mutation(
            Mutation(
                id=f"{correlation.correlation_id}:{node.id}:{node.updated_at.timestamp()}",
                correlation=correlation,
                type=MutationType.UPDATE_NODE,
                payload={"node": node.to_payload()},
                created_at=node.updated_at,
            )
        )
        self._conn.commit()

    def get_node(self, node_id: str) -> Node | None:
        row = self._conn.execute(
            "SELECT * FROM world_nodes WHERE id = ?", (node_id,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_node(row)

    def delete_node(self, node_id: str, correlation: CorrelationContext) -> None:
        self._conn.execute("DELETE FROM world_edges WHERE from_node_id = ? OR to_node_id = ?", (node_id, node_id))
        self._conn.execute("DELETE FROM world_nodes WHERE id = ?", (node_id,))
        self.append_mutation(
            Mutation(
                id=f"{correlation.correlation_id}:{node_id}:delete",
                correlation=correlation,
                type=MutationType.DELETE_NODE,
                payload={"node_id": node_id},
            )
        )
        self._conn.commit()

    def save_edge(self, edge: Edge, correlation: CorrelationContext) -> None:
        self._conn.execute(
            """
            INSERT INTO world_edges (
                id, from_node_id, to_node_id, type, attributes_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                from_node_id = excluded.from_node_id,
                to_node_id = excluded.to_node_id,
                type = excluded.type,
                attributes_json = excluded.attributes_json
            """,
            (
                edge.id,
                edge.from_node_id,
                edge.to_node_id,
                edge.type,
                json.dumps(edge.attributes, sort_keys=True),
                edge.created_at.isoformat(),
            ),
        )
        self.append_mutation(
            Mutation(
                id=f"{correlation.correlation_id}:{edge.id}:{edge.created_at.timestamp()}",
                correlation=correlation,
                type=MutationType.CREATE_EDGE,
                payload={"edge": edge.to_payload()},
                created_at=edge.created_at,
            )
        )
        self._conn.commit()

    def get_edges(self, node_id: str, direction: str = "both") -> list[Edge]:
        direction = direction.lower()
        if direction == "in":
            rows = self._conn.execute(
                "SELECT * FROM world_edges WHERE to_node_id = ? ORDER BY created_at",
                (node_id,),
            ).fetchall()
        elif direction == "out":
            rows = self._conn.execute(
                "SELECT * FROM world_edges WHERE from_node_id = ? ORDER BY created_at",
                (node_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM world_edges
                WHERE from_node_id = ? OR to_node_id = ?
                ORDER BY created_at
                """,
                (node_id, node_id),
            ).fetchall()
        return [_row_to_edge(row) for row in rows]

    def delete_edge(self, edge_id: str, correlation: CorrelationContext) -> None:
        self._conn.execute("DELETE FROM world_edges WHERE id = ?", (edge_id,))
        self.append_mutation(
            Mutation(
                id=f"{correlation.correlation_id}:{edge_id}:delete",
                correlation=correlation,
                type=MutationType.DELETE_EDGE,
                payload={"edge_id": edge_id},
            )
        )
        self._conn.commit()

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
        params: tuple[Any, ...]
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


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _loads(value: str | None) -> dict[str, Any]:
    raw = json.loads(value or "{}")
    return raw if isinstance(raw, dict) else {}


def _row_to_node(row: sqlite3.Row) -> Node:
    return Node(
        id=str(row["id"]),
        type=str(row["type"]),
        attributes=_loads(row["attributes_json"]),
        created_at=_parse_datetime(str(row["created_at"])),
        updated_at=_parse_datetime(str(row["updated_at"])),
    )


def _row_to_edge(row: sqlite3.Row) -> Edge:
    return Edge(
        id=str(row["id"]),
        from_node_id=str(row["from_node_id"]),
        to_node_id=str(row["to_node_id"]),
        type=str(row["type"]),
        attributes=_loads(row["attributes_json"]),
        created_at=_parse_datetime(str(row["created_at"])),
    )


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
