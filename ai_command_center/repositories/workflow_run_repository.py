"""SQLite persistence for workflow run metadata (Program 4 slice 3)."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoredWorkflowRun:
    run_id: str
    workflow_id: str
    state: str
    total_steps: int
    current_step_index: int
    error: str
    steps: tuple[dict[str, object], ...]
    created_at: float
    updated_at: float


class WorkflowRunRepository:
    """Owns workflow_runs table access."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert_started(
        self,
        *,
        run_id: str,
        workflow_id: str,
        total_steps: int,
        steps: list[dict[str, object]] | None = None,
    ) -> StoredWorkflowRun:
        now = time.time()
        steps_json = json.dumps(list(steps or []))
        self._conn.execute(
            """
            INSERT INTO workflow_runs (
                run_id, workflow_id, state, total_steps, current_step_index,
                error, steps_json, created_at, updated_at
            ) VALUES (?, ?, 'running', ?, 0, '', ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                workflow_id = excluded.workflow_id,
                state = 'running',
                total_steps = excluded.total_steps,
                current_step_index = 0,
                error = '',
                steps_json = excluded.steps_json,
                updated_at = excluded.updated_at
            """,
            (run_id, workflow_id, total_steps, steps_json, now, now),
        )
        self._conn.commit()
        return StoredWorkflowRun(
            run_id=run_id,
            workflow_id=workflow_id,
            state="running",
            total_steps=total_steps,
            current_step_index=0,
            error="",
            steps=tuple(steps or ()),
            created_at=now,
            updated_at=now,
        )

    def update_progress(
        self,
        *,
        run_id: str,
        current_step_index: int,
        current_step_id: str = "",
    ) -> None:
        now = time.time()
        self._conn.execute(
            """
            UPDATE workflow_runs
            SET current_step_index = ?, updated_at = ?
            WHERE run_id = ?
            """,
            (current_step_index, now, run_id),
        )
        self._conn.commit()

    def finalize(
        self,
        *,
        run_id: str,
        state: str,
        current_step_index: int = 0,
        error: str = "",
    ) -> StoredWorkflowRun | None:
        now = time.time()
        row = self._conn.execute(
            "SELECT run_id FROM workflow_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None
        self._conn.execute(
            """
            UPDATE workflow_runs
            SET state = ?, current_step_index = ?, error = ?, updated_at = ?
            WHERE run_id = ?
            """,
            (state, current_step_index, error, now, run_id),
        )
        self._conn.commit()
        return self.get(run_id)

    def get(self, run_id: str) -> StoredWorkflowRun | None:
        row = self._conn.execute(
            """
            SELECT run_id, workflow_id, state, total_steps, current_step_index,
                   error, steps_json, created_at, updated_at
            FROM workflow_runs WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_run(row)

    def list_recent(self, *, limit: int = 20) -> list[StoredWorkflowRun]:
        rows = self._conn.execute(
            """
            SELECT run_id, workflow_id, state, total_steps, current_step_index,
                   error, steps_json, created_at, updated_at
            FROM workflow_runs
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._row_to_run(row) for row in reversed(rows)]

    @staticmethod
    def _row_to_run(row: sqlite3.Row | tuple) -> StoredWorkflowRun:
        if isinstance(row, sqlite3.Row):
            steps_raw = row["steps_json"]
            return StoredWorkflowRun(
                run_id=str(row["run_id"]),
                workflow_id=str(row["workflow_id"]),
                state=str(row["state"]),
                total_steps=int(row["total_steps"]),
                current_step_index=int(row["current_step_index"]),
                error=str(row["error"] or ""),
                steps=tuple(json.loads(steps_raw)) if steps_raw else (),
                created_at=float(row["created_at"]),
                updated_at=float(row["updated_at"]),
            )
        (
            run_id,
            workflow_id,
            state,
            total_steps,
            current_step_index,
            error,
            steps_raw,
            created_at,
            updated_at,
        ) = row
        return StoredWorkflowRun(
            run_id=str(run_id),
            workflow_id=str(workflow_id),
            state=str(state),
            total_steps=int(total_steps),
            current_step_index=int(current_step_index),
            error=str(error or ""),
            steps=tuple(json.loads(steps_raw)) if steps_raw else (),
            created_at=float(created_at),
            updated_at=float(updated_at),
        )
