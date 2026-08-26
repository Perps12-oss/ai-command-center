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
from typing import Any

# sqlite3.Connection is not weakref-able; drop entries explicitly on close if needed.
_LOCKS: dict[int, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


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
        self._lock.acquire()
        with self._gate:
            if self._owner is None:
                self._owner = tid
            elif self._owner != tid:
                self._lock.release()
                raise RuntimeError("sqlite connection lock ownership corruption")

    def _leave(self) -> None:
        """Drop ownership/lock only when the underlying transaction is closed."""
        tid = self._thread_id()
        release = False
        with self._gate:
            if self._owner != tid:
                return
            try:
                in_transaction = bool(self._raw.in_transaction)
            except sqlite3.ProgrammingError:
                in_transaction = False
            if in_transaction:
                return
            self._owner = None
            release = True
        if release:
            self._lock.release()

    def _terminal(self, *, commit: bool) -> None:
        self._enter()
        try:
            if commit:
                self._raw.commit()
            else:
                self._raw.rollback()
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
            return self._raw.execute(*args, **kwargs)
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
        # Serialize close with all SQLite operations to avoid closing the
        # underlying handle while another worker thread is mid-statement.
        self._enter()
        try:
            if self._raw.in_transaction:
                self._raw.rollback()
            drop_connection_lock(self._raw)
            self._raw.close()
        finally:
            tid = self._thread_id()
            with self._gate:
                if self._owner == tid:
                    self._owner = None
            try:
                self._lock.release()
            except RuntimeError:
                pass

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
