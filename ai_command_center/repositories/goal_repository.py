"""Repository for Brain goals and task metadata."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.goal import Goal, GoalStatus, Priority


class GoalRepository:
    """SQLite persistence for scheduler goals."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL,
                depends_on_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);
            CREATE INDEX IF NOT EXISTS idx_goals_priority ON goals(priority);
            """
        )
        self._conn.commit()

    def save_goal(self, goal: Goal) -> None:
        self._conn.execute(
            """
            INSERT INTO goals (
                id, title, description, priority, depends_on_json, status, correlation_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                priority = excluded.priority,
                depends_on_json = excluded.depends_on_json,
                status = excluded.status,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                goal.id,
                goal.title,
                goal.description,
                goal.priority.value,
                json.dumps(list(goal.depends_on)),
                goal.status.value,
                goal.correlation.correlation_id,
            ),
        )
        self._conn.commit()

    def get_goal(self, goal_id: str) -> Goal | None:
        row = self._conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if row is None:
            return None
        return _row_to_goal(row)

    def list_goals(self, status: str = "") -> list[Goal]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM goals WHERE status = ? ORDER BY created_at ASC",
                (status,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM goals ORDER BY created_at ASC"
            ).fetchall()
        return [_row_to_goal(row) for row in rows]

    def update_goal_status(
        self, goal_id: str, status: GoalStatus, correlation: CorrelationContext
    ) -> None:
        self._conn.execute(
            """
            UPDATE goals
            SET status = ?, correlation_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status.value, correlation.correlation_id, goal_id),
        )
        self._conn.commit()


def _row_to_goal(row: sqlite3.Row) -> Goal:
    depends_on_raw: Any = json.loads(row["depends_on_json"] or "[]")
    depends_on = tuple(str(item) for item in depends_on_raw if str(item).strip())
    return Goal(
        id=str(row["id"]),
        title=str(row["title"]),
        description=str(row["description"] or ""),
        priority=Priority(str(row["priority"])),
        depends_on=depends_on,
        status=GoalStatus(str(row["status"])),
        correlation=CorrelationContext(str(row["correlation_id"])),
    )
