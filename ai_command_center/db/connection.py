"""SQLite connection and schema initialization."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ai_command_center.platform.detector import get_runtime_data_dir

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_database_path() -> Path:
    return get_runtime_data_dir() / "app.db"


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database(conn: sqlite3.Connection | None = None) -> sqlite3.Connection:
    own = conn is None
    connection = conn or connect()
    script = _SCHEMA_PATH.read_text(encoding="utf-8")
    connection.executescript(script)
    _migrate_note_fts(connection)
    _migrate_memory_graph(connection)
    connection.commit()
    if own:
        return connection
    return connection


def _migrate_note_fts(conn: sqlite3.Connection) -> None:
    """Rebuild FTS table when upgrading from external-content schema."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='note_fts'"
    ).fetchone()
    if row is None or row["sql"] is None:
        return
    if "path" in str(row["sql"]):
        return
    conn.execute("DROP TABLE IF EXISTS note_fts")
    conn.executescript(
        """
        CREATE VIRTUAL TABLE note_fts USING fts5(
            path UNINDEXED,
            title,
            body
        );
        """
    )


def _migrate_memory_graph(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_nodes'"
    ).fetchone()
    if row is not None:
        return
    conn.executescript(
        """
        CREATE TABLE memory_nodes (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'entity',
            content TEXT NOT NULL DEFAULT '',
            tier TEXT NOT NULL DEFAULT 'mid',
            created_at REAL NOT NULL
        );
        CREATE TABLE memory_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            created_at REAL NOT NULL,
            FOREIGN KEY (source_id) REFERENCES memory_nodes(id) ON DELETE CASCADE,
            FOREIGN KEY (target_id) REFERENCES memory_nodes(id) ON DELETE CASCADE
        );
        CREATE INDEX idx_memory_edges_source ON memory_edges(source_id);
        CREATE INDEX idx_memory_edges_target ON memory_edges(target_id);
        """
    )
