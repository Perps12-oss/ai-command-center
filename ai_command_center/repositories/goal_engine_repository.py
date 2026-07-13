"""SQLite persistence for GoalEngine (orchestration.goals.goal.Goal).

Implements GoalEngineRepository from goal_engine.py against the richer
Phase-9 goal schema that includes created_by, parent_goal_id, tags, metadata,
priority (int), deadline, and the full GoalStatus enum from goal_status.py.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from ai_command_center.orchestration.goals.goal import Goal
from ai_command_center.orchestration.goals.goal_engine import GoalEngineRepository
from ai_command_center.orchestration.goals.goal_status import GoalStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SQLiteGoalEngineRepository(GoalEngineRepository):
    """SQLite-backed repository for GoalEngine goals.

    Schema is separate from GoalRepository (scheduler goals) to avoid
    coupling the richer Phase-9 domain model to the simpler scheduler model.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS goal_engine_goals (
                id             TEXT PRIMARY KEY,
                title          TEXT NOT NULL,
                description    TEXT NOT NULL DEFAULT '',
                status         TEXT NOT NULL DEFAULT 'draft',
                created_at     TEXT NOT NULL,
                updated_at     TEXT NOT NULL,
                created_by     TEXT NOT NULL DEFAULT 'user',
                parent_goal_id TEXT,
                tags_json      TEXT NOT NULL DEFAULT '[]',
                metadata_json  TEXT NOT NULL DEFAULT '{}',
                priority       INTEGER NOT NULL DEFAULT 0,
                deadline       TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_geg_status
                ON goal_engine_goals(status);
            CREATE INDEX IF NOT EXISTS idx_geg_parent
                ON goal_engine_goals(parent_goal_id);
            """
        )
        self._conn.commit()

    # ── GoalEngineRepository interface ────────────────────────────────────

    def save(self, goal: Goal) -> None:
        now = _utcnow().isoformat()
        self._conn.execute(
            """
            INSERT INTO goal_engine_goals (
                id, title, description, status,
                created_at, updated_at,
                created_by, parent_goal_id,
                tags_json, metadata_json,
                priority, deadline
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title          = excluded.title,
                description    = excluded.description,
                status         = excluded.status,
                updated_at     = excluded.updated_at,
                created_by     = excluded.created_by,
                parent_goal_id = excluded.parent_goal_id,
                tags_json      = excluded.tags_json,
                metadata_json  = excluded.metadata_json,
                priority       = excluded.priority,
                deadline       = excluded.deadline
            """,
            (
                goal.id,
                goal.title,
                goal.description,
                goal.status.value,
                getattr(goal, "created_at", _utcnow()).isoformat()
                if not isinstance(getattr(goal, "created_at", None), str)
                else goal.created_at,
                now,
                getattr(goal, "created_by", "user"),
                getattr(goal, "parent_goal_id", None),
                json.dumps(list(getattr(goal, "tags", []))),
                json.dumps(dict(getattr(goal, "metadata", {}))),
                int(getattr(goal, "priority", 0)),
                _deadline_str(getattr(goal, "deadline", None)),
            ),
        )
        self._conn.commit()

    def get(self, goal_id: str) -> Goal | None:
        row = self._conn.execute(
            "SELECT * FROM goal_engine_goals WHERE id = ?", (goal_id,)
        ).fetchone()
        return _row_to_goal(row) if row else None

    def get_by_status(self, status: GoalStatus) -> list[Goal]:
        rows = self._conn.execute(
            "SELECT * FROM goal_engine_goals WHERE status = ? ORDER BY created_at ASC",
            (status.value,),
        ).fetchall()
        return [_row_to_goal(r) for r in rows]

    def get_active(self) -> list[Goal]:
        terminal = (
            GoalStatus.COMPLETED.value,
            GoalStatus.FAILED.value,
            GoalStatus.ABANDONED.value,
        )
        placeholders = ",".join("?" * len(terminal))
        rows = self._conn.execute(
            f"SELECT * FROM goal_engine_goals WHERE status NOT IN ({placeholders})"
            " ORDER BY created_at ASC",
            terminal,
        ).fetchall()
        return [_row_to_goal(r) for r in rows]

    def get_children(self, goal_id: str) -> list[Goal]:
        rows = self._conn.execute(
            "SELECT * FROM goal_engine_goals WHERE parent_goal_id = ? ORDER BY created_at ASC",
            (goal_id,),
        ).fetchall()
        return [_row_to_goal(r) for r in rows]

    def get_root_goals(self) -> list[Goal]:
        rows = self._conn.execute(
            "SELECT * FROM goal_engine_goals WHERE parent_goal_id IS NULL ORDER BY created_at ASC"
        ).fetchall()
        return [_row_to_goal(r) for r in rows]

    def delete(self, goal_id: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM goal_engine_goals WHERE id = ?", (goal_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0


# ── helpers ───────────────────────────────────────────────────────────────


def _deadline_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return _utcnow()
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return _utcnow()


def _row_to_goal(row: sqlite3.Row) -> Goal:
    tags_raw: Any = json.loads(row["tags_json"] or "[]")
    tags: list[str] = [str(t) for t in tags_raw] if isinstance(tags_raw, list) else []
    meta_raw: Any = json.loads(row["metadata_json"] or "{}")
    metadata: dict[str, Any] = dict(meta_raw) if isinstance(meta_raw, dict) else {}
    deadline_str: str | None = row["deadline"]
    deadline = _parse_dt(deadline_str) if deadline_str else None
    return Goal(
        id=str(row["id"]),
        title=str(row["title"]),
        description=str(row["description"] or ""),
        status=GoalStatus(str(row["status"])),
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
        created_by=str(row["created_by"] or "user"),
        parent_goal_id=row["parent_goal_id"] or None,
        tags=tags,
        metadata=metadata,
        priority=int(row["priority"] or 0),
        deadline=deadline,
    )
