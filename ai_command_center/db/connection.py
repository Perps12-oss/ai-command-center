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
