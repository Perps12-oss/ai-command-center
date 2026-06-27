"""SQLite connection helpers with repository-owned bootstrap delegation."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, cast

from ai_command_center.platform.runtime_paths import get_runtime_data_dir
from ai_command_center.repositories.database_bootstrap_repository import DatabaseBootstrapRepository


def get_database_path() -> Path:
    return get_runtime_data_dir() / "app.db"


class ThreadSafeConnection:
    """Thread-safe proxy for a shared sqlite3.Connection.

    Repositories own persistence, but the connection object is shared across
    service threads. This wrapper serializes every mutating and read access
    through an RLock so that the connection can be used safely without relying
    on the underlying SQLite build mode or ``check_same_thread``.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = threading.RLock()

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return self._conn.execute(*args, **kwargs)

    def executemany(self, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return self._conn.executemany(*args, **kwargs)

    def executescript(self, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return self._conn.executescript(*args, **kwargs)

    def commit(self, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return self._conn.commit(*args, **kwargs)

    def rollback(self, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return self._conn.rollback(*args, **kwargs)

    def close(self, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return self._conn.close(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a connection and return a thread-safe wrapper."""
    path = db_path or get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    raw_conn = sqlite3.connect(path, check_same_thread=False)
    raw_conn.row_factory = sqlite3.Row
    raw_conn.execute("PRAGMA foreign_keys = ON")
    return cast(sqlite3.Connection, ThreadSafeConnection(raw_conn))


def init_database(conn: sqlite3.Connection | None = None) -> sqlite3.Connection:
    own = conn is None
    connection = conn or connect()
    DatabaseBootstrapRepository().apply(connection)
    if own:
        return connection
    return connection
