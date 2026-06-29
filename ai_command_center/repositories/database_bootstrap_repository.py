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

_MIGRATIONS: list[tuple[int, MigrationFn]] = [
    (1, _migrate_v1),
    (2, _migrate_v2),
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
