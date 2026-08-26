"""Shared SQLite connection lock and transaction-guarded connection wrapper.

EventBus worker threads share one SQLite connection across repositories.
SQLite transaction state is connection-wide: ``commit()`` on that connection
commits *every* open statement, including another thread's partial work.

``GuardedConnection`` enforces connection-owned serialization:

* The first statement that opens a transaction acquires the connection lock
  and retains it until ``commit`` / ``rollback``.
* Another thread cannot ``execute`` / ``commit`` / ``rollback`` until the
  owning thread ends the transaction.

Repositories may still use ``connection_lock`` for explicit critical sections;
``GuardedConnection`` makes opt-out impossible for the shared composition-root
handle returned by ``connect()``.
"""

from __future__ import annotations

import sqlite3
import threading
import json
import time
from typing import Any

# sqlite3.Connection is not weakref-able; drop entries explicitly on close if needed.
_LOCKS: dict[int, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()
_DEBUG_LOG_PATH = "/opt/cursor/logs/debug.log"


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
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


def _raw_conn(conn: sqlite3.Connection | GuardedConnection) -> sqlite3.Connection:
    if isinstance(conn, GuardedConnection):
        return conn.raw
    return conn


def connection_lock(conn: sqlite3.Connection | GuardedConnection) -> threading.RLock:
    """Return the shared write lock for ``conn`` (raw or guarded)."""
    key = id(_raw_conn(conn))
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _LOCKS[key] = lock
        return lock


def drop_connection_lock(conn: sqlite3.Connection | GuardedConnection) -> None:
    """Release the side-table lock entry for a closed connection."""
    with _LOCKS_GUARD:
        _LOCKS.pop(id(_raw_conn(conn)), None)


class GuardedConnection:
    """Proxy that serializes SQLite use and binds lock lifetime to transactions.

    Invariant: one thread's ``commit()`` / ``rollback()`` cannot end another
    thread's open transaction on the shared connection.
    """

    __slots__ = ("_raw", "_lock", "_owner", "_gate")

    def __init__(self, raw: sqlite3.Connection) -> None:
        self._raw = raw
        self._lock = connection_lock(raw)
        self._owner: int | None = None
        self._gate = threading.Lock()

    @property
    def raw(self) -> sqlite3.Connection:
        return self._raw

    def _thread_id(self) -> int:
        return threading.get_ident()

    def _enter(self) -> None:
        tid = self._thread_id()
        with self._gate:
            if self._owner == tid:
                return
        wait_start = time.perf_counter()
        self._lock.acquire()
        wait_ms = (time.perf_counter() - wait_start) * 1000.0
        with self._gate:
            if self._owner is None:
                self._owner = tid
            elif self._owner != tid:
                self._lock.release()
                raise RuntimeError("sqlite connection lock ownership corruption")
        if wait_ms >= 25.0:
            # region agent log
            _debug_log(
                "A",
                "conn_sync.py:_enter",
                "sqlite lock wait observed",
                {
                    "threadId": tid,
                    "waitMs": round(wait_ms, 3),
                    "inTransaction": bool(self._raw.in_transaction),
                    "owner": self._owner,
                },
            )
            # endregion

    def _leave(self) -> None:
        """Drop ownership/lock only when the underlying transaction is closed."""
        tid = self._thread_id()
        release = False
        with self._gate:
            if self._owner != tid:
                return
            if self._raw.in_transaction:
                return
            self._owner = None
            release = True
        if release:
            self._lock.release()

    def _terminal(self, *, commit: bool) -> None:
        self._enter()
        try:
            try:
                if commit:
                    self._raw.commit()
                else:
                    self._raw.rollback()
            except sqlite3.Error as exc:
                # region agent log
                _debug_log(
                    "A",
                    "conn_sync.py:_terminal",
                    "sqlite terminal operation failed",
                    {
                        "threadId": self._thread_id(),
                        "commit": bool(commit),
                        "error": str(exc),
                        "inTransactionAfterError": bool(self._raw.in_transaction),
                    },
                )
                # endregion
                raise
        finally:
            tid = self._thread_id()
            with self._gate:
                if self._owner == tid:
                    self._owner = None
            try:
                self._lock.release()
            except RuntimeError:
                pass

    def execute(self, *args: Any, **kwargs: Any) -> sqlite3.Cursor:
        self._enter()
        try:
            try:
                return self._raw.execute(*args, **kwargs)
            except sqlite3.Error as exc:
                sql = str(args[0]) if args else ""
                # region agent log
                _debug_log(
                    "B",
                    "conn_sync.py:execute",
                    "sqlite execute failed",
                    {
                        "threadId": self._thread_id(),
                        "error": str(exc),
                        "sqlPrefix": sql[:120],
                        "inTransaction": bool(self._raw.in_transaction),
                    },
                )
                # endregion
                raise
        finally:
            self._leave()

    def executemany(self, *args: Any, **kwargs: Any) -> sqlite3.Cursor:
        self._enter()
        try:
            return self._raw.executemany(*args, **kwargs)
        finally:
            self._leave()

    def executescript(self, sql_script: str) -> sqlite3.Cursor:
        self._enter()
        try:
            return self._raw.executescript(sql_script)
        finally:
            # executescript issues COMMIT; force release.
            tid = self._thread_id()
            with self._gate:
                if self._owner == tid:
                    self._owner = None
            try:
                self._lock.release()
            except RuntimeError:
                pass

    def commit(self) -> None:
        self._terminal(commit=True)

    def rollback(self) -> None:
        self._terminal(commit=False)

    def close(self) -> None:
        # region agent log
        _debug_log(
            "C",
            "conn_sync.py:close",
            "sqlite connection close requested",
            {
                "threadId": self._thread_id(),
                "inTransaction": bool(self._raw.in_transaction),
                "owner": self._owner,
            },
        )
        # endregion
        try:
            if self._raw.in_transaction:
                self.rollback()
        finally:
            drop_connection_lock(self._raw)
            self._raw.close()

    def cursor(self, *args: Any, **kwargs: Any) -> sqlite3.Cursor:
        self._enter()
        try:
            return self._raw.cursor(*args, **kwargs)
        finally:
            self._leave()

    # Common attributes assigned on connect().
    @property
    def row_factory(self) -> Any:
        return self._raw.row_factory

    @row_factory.setter
    def row_factory(self, value: Any) -> None:
        self._raw.row_factory = value

    @property
    def in_transaction(self) -> bool:
        return bool(self._raw.in_transaction)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw, name)

    def __enter__(self) -> GuardedConnection:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
