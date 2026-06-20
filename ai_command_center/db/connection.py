"""SQLite connection helpers with repository-owned bootstrap delegation."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ai_command_center.platform.runtime_paths import get_runtime_data_dir
from ai_command_center.repositories.database_bootstrap_repository import DatabaseBootstrapRepository


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
    DatabaseBootstrapRepository().apply(connection)
    if own:
        return connection
    return connection
