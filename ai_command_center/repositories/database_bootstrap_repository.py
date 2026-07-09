"""Repository-owned database bootstrap and migration helpers.

Migration chain
---------------
Each entry in ``_MIGRATIONS`` is a ``(version: int, callable)`` pair.
``apply()`` reads the current ``schema_version``, runs every migration whose
version is greater than the stored value in ascending order, then writes the
new version.  Adding a new migration means appending one entry here — no
edits to ``schema.sql`` or any other file required.

To add a migration:
    1. Define a module-level ``_migrate_vN`` function (conn: Connection) -> None.
    2. Append ``(N, _migrate_vN)`` to ``_MIGRATIONS``.
    3. N must be exactly ``max(existing versions) + 1``.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "db" / "schema.sql"

MigrationFn = Callable[[sqlite3.Connection], None]


# ── individual migrations ──────────────────────────────────────────────────────

def _migrate_v1(conn: sqlite3.Connection) -> None:
    """Baseline schema — conversations, messages, settings, note_index, FTS,
    embeddings, context_events, memory graph, telemetry, plugin_state."""
    conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _migrate_v2(conn: sqlite3.Connection) -> None:
    """Repair note FTS: rebuild if external-content or stale trigger schema."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='note_fts'"
    ).fetchone()
    fts_sql = ""
    if row is not None:
        fts_sql = str(row[0] if isinstance(row, tuple) else row["sql"] or "")

    trigger_rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='note_index'"
    ).fetchall()
    stale_triggers = [
        str(r[0] if isinstance(r, tuple) else r["name"]) for r in trigger_rows
    ]
    standalone = "path" in fts_sql.lower() and "content=" not in fts_sql.lower()

    for name in stale_triggers:
        conn.execute(f"DROP TRIGGER IF EXISTS {name}")

    if stale_triggers or not standalone:
        conn.execute("DELETE FROM note_index")
        conn.execute("DROP TABLE IF EXISTS note_fts")
        conn.executescript(
            "CREATE VIRTUAL TABLE note_fts USING fts5(path UNINDEXED, title, body);"
        )


# ── registry — append new migrations here only ────────────────────────────────

def _migrate_v3(conn: sqlite3.Connection) -> None:
    """Add workspace_id namespace column to memory_nodes (Program 3 W2)."""
    cols = {
        str(row[1] if isinstance(row, tuple) else row["name"])
        for row in conn.execute("PRAGMA table_info(memory_nodes)").fetchall()
    }
    if "workspace_id" not in cols:
        conn.execute(
            "ALTER TABLE memory_nodes ADD COLUMN workspace_id TEXT NOT NULL DEFAULT ''"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_nodes_workspace "
            "ON memory_nodes(workspace_id)"
        )


def _migrate_v4(conn: sqlite3.Connection) -> None:
    """Add entity_id scope column to memory_nodes (Program 3 Phase 4)."""
    cols = {
        str(row[1] if isinstance(row, tuple) else row["name"])
        for row in conn.execute("PRAGMA table_info(memory_nodes)").fetchall()
    }
    if "entity_id" not in cols:
        conn.execute(
            "ALTER TABLE memory_nodes ADD COLUMN entity_id TEXT NOT NULL DEFAULT ''"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_nodes_entity "
            "ON memory_nodes(workspace_id, entity_id)"
        )


def _migrate_v5(conn: sqlite3.Connection) -> None:
    """Add execution_runs table for Provider Platform time-travel diagnostics."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS execution_runs (
            run_id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            source TEXT NOT NULL,
            snapshot TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_execution_runs_request ON execution_runs(request_id);
        CREATE INDEX IF NOT EXISTS idx_execution_runs_created ON execution_runs(created_at);
        """
    )


def _migrate_v6(conn: sqlite3.Connection) -> None:
    """Add workflow_runs table for Program 4 workflow persistence."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS workflow_runs (
            run_id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL,
            state TEXT NOT NULL,
            total_steps INTEGER NOT NULL DEFAULT 0,
            current_step_index INTEGER NOT NULL DEFAULT 0,
            error TEXT NOT NULL DEFAULT '',
            steps_json TEXT NOT NULL DEFAULT '[]',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_workflow_runs_updated ON workflow_runs(updated_at);
        """
    )


def _migrate_v7(conn: sqlite3.Connection) -> None:
    """Add artifacts table for ACC UI Refurbishment artifact catalog (PR 6)."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS artifacts (
            artifact_id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            label TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            size_bytes INTEGER NOT NULL DEFAULT 0,
            mime_type TEXT NOT NULL DEFAULT '',
            request_id TEXT NOT NULL DEFAULT '',
            workspace_id TEXT NOT NULL DEFAULT '',
            entity_id TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_artifacts_updated ON artifacts(updated_at);
        CREATE INDEX IF NOT EXISTS idx_artifacts_request ON artifacts(request_id);
        """
    )


def _migrate_v8(conn: sqlite3.Connection) -> None:
    """Repair artifacts table schema drift — add missing columns on legacy DBs."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='artifacts'"
    ).fetchone()
    if row is None:
        _migrate_v7(conn)
        return

    cols = {
        str(r[1] if isinstance(r, tuple) else r["name"])
        for r in conn.execute("PRAGMA table_info(artifacts)").fetchall()
    }
    additions: tuple[tuple[str, str], ...] = (
        ("content", "TEXT NOT NULL DEFAULT ''"),
        ("size_bytes", "INTEGER NOT NULL DEFAULT 0"),
        ("mime_type", "TEXT NOT NULL DEFAULT ''"),
        ("request_id", "TEXT NOT NULL DEFAULT ''"),
        ("workspace_id", "TEXT NOT NULL DEFAULT ''"),
        ("entity_id", "TEXT NOT NULL DEFAULT ''"),
        ("source", "TEXT NOT NULL DEFAULT ''"),
        ("created_at", "REAL NOT NULL DEFAULT 0"),
        ("updated_at", "REAL NOT NULL DEFAULT 0"),
    )
    for name, typedef in additions:
        if name not in cols:
            conn.execute(f"ALTER TABLE artifacts ADD COLUMN {name} {typedef}")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_artifacts_updated ON artifacts(updated_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_artifacts_request ON artifacts(request_id)"
    )


_MIGRATIONS: list[tuple[int, MigrationFn]] = [
    (1, _migrate_v1),
    (2, _migrate_v2),
    (3, _migrate_v3),
    (4, _migrate_v4),
    (5, _migrate_v5),
    (6, _migrate_v6),
    (7, _migrate_v7),
    (8, _migrate_v8),
]


# ── bootstrap repository ───────────────────────────────────────────────────────

class DatabaseBootstrapRepository:
    """Owns schema versioning and migration execution for SQLite.

    The ``schema_version`` table is the sole source of truth for which
    migrations have been applied.  Each migration runs exactly once.
    """

    def apply(self, conn: sqlite3.Connection) -> None:
        """Ensure ``schema_version`` exists, then run pending migrations."""
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
        )
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        current: int = int(row[0]) if row and row[0] is not None else 0

        pending = sorted(
            [(v, fn) for v, fn in _MIGRATIONS if v > current],
            key=lambda t: t[0],
        )
        for version, fn in pending:
            fn(conn)
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)", (version,)
            )

        conn.commit()
