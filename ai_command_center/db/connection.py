"""SQLite connection helpers with repository-owned bootstrap delegation."""

from __future__ import annotations

import sqlite3
import json
import time
from pathlib import Path

from ai_command_center.db.conn_sync import GuardedConnection, connection_lock
from ai_command_center.platform.runtime_paths import get_runtime_data_dir
from ai_command_center.repositories.database_bootstrap_repository import DatabaseBootstrapRepository

__all__ = [
    "GuardedConnection",
    "connect",
    "connection_lock",
    "get_database_path",
    "init_database",
]
_DEBUG_LOG_PATH = "/opt/cursor/logs/debug.log"


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict[str, object]) -> None:
    try:
        open(_DEBUG_LOG_PATH, "a", encoding="utf-8").write(
            json.dumps(
                {
                    "hypothesisId": hypothesis_id,
                    "location": location,
                    "message": message,
                    "data": data,
                    "timestamp": int(time.time() * 1000),
                },
                separators=(",", ":"),
            )
            + "\n"
        )
    except Exception:
        return


def get_database_path() -> Path:
    return get_runtime_data_dir() / "app.db"


def connect(db_path: Path | None = None) -> GuardedConnection:
    path = db_path or get_database_path()
    # ``:memory:`` has parent ``.``; real paths need their directory created.
    if str(path) not in {":memory:", "file::memory:?cache=shared"}:
        path.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(str(path), check_same_thread=False, timeout=30.0)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    raw.execute("PRAGMA busy_timeout = 5000")
    # WAL: readers do not block writers; critical for UI-adjacent telemetry.
    if str(path) not in {":memory:", "file::memory:?cache=shared"}:
        try:
            raw.execute("PRAGMA journal_mode = WAL")
            raw.execute("PRAGMA synchronous = NORMAL")
        except sqlite3.Error:
            pass
    # Composition-root handle: transaction-bound serialization (P1-B).
    # region agent log
    _debug_log(
        "D",
        "connection.py:connect",
        "sqlite primary connection created",
        {"dbPath": str(path), "rawId": id(raw)},
    )
    # endregion
    return GuardedConnection(raw)


def init_database(
    conn: sqlite3.Connection | GuardedConnection | None = None,
) -> sqlite3.Connection | GuardedConnection:
    own = conn is None
    connection = conn or connect()
    DatabaseBootstrapRepository().apply(connection)
    if own:
        return connection
    return connection
