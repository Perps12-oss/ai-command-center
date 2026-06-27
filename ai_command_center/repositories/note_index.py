"""Obsidian vault note index — FTS5 keyword search (no embeddings)."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NoteHit:
    path: str
    title: str
    snippet: str


_FTS_SPECIAL = re.compile(r'["*()]')


def escape_fts_query(query: str) -> str:
    """Build a safe FTS5 prefix query from user input."""
    tokens = [t for t in query.strip().split() if t]
    if not tokens:
        return '""'
    parts: list[str] = []
    for token in tokens:
        clean = _FTS_SPECIAL.sub("", token)
        if clean:
            parts.append(f'"{clean}"*')
    return " AND ".join(parts) if parts else '""'


class NoteIndex:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(self, path: str, title: str, body: str, mtime: float) -> bool:
        """Insert or update indexed note. Returns True if row changed."""
        row = self._conn.execute(
            "SELECT mtime FROM note_index WHERE path = ?", (path,)
        ).fetchone()
        if row is not None and float(row["mtime"]) == mtime:
            return False

        old = self._conn.execute(
            "SELECT title, body FROM note_index WHERE path = ?", (path,)
        ).fetchone()
        if old is not None:
            self._conn.execute(
                """
                INSERT INTO note_fts(note_fts, path, title, body)
                VALUES ('delete', ?, ?, ?)
                """,
                (path, str(old["title"]), str(old["body"])),
            )
            self._conn.execute("DELETE FROM note_index WHERE path = ?", (path,))

        self._conn.execute(
            "INSERT INTO note_index (path, title, mtime, body) VALUES (?, ?, ?, ?)",
            (path, title, mtime, body),
        )
        self._conn.execute(
            "INSERT INTO note_fts (path, title, body) VALUES (?, ?, ?)",
            (path, title, body),
        )
        self._conn.commit()
        return True

    def remove(self, path: str) -> None:
        old = self._conn.execute(
            "SELECT title, body FROM note_index WHERE path = ?", (path,)
        ).fetchone()
        if old is not None:
            self._conn.execute(
                """
                INSERT INTO note_fts(note_fts, path, title, body)
                VALUES ('delete', ?, ?, ?)
                """,
                (path, str(old["title"]), str(old["body"])),
            )
            self._conn.execute("DELETE FROM note_index WHERE path = ?", (path,))
        self._conn.commit()

    def search(self, query: str, *, limit: int = 20) -> list[NoteHit]:
        fts = escape_fts_query(query)
        rows = self._conn.execute(
            """
            SELECT path, title,
                   snippet(note_fts, 2, '[', ']', '…', 24) AS snippet
            FROM note_fts
            WHERE note_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts, limit),
        ).fetchall()
        return [
            NoteHit(
                path=str(r["path"]),
                title=str(r["title"]),
                snippet=str(r["snippet"] or ""),
            )
            for r in rows
        ]

    def get_body(self, path: str) -> str | None:
        row = self._conn.execute(
            "SELECT body FROM note_index WHERE path = ?", (path,)
        ).fetchone()
        if row is None:
            return None
        return str(row["body"])

    def indexed_mtime(self, path: str) -> float | None:
        row = self._conn.execute(
            "SELECT mtime FROM note_index WHERE path = ?", (path,)
        ).fetchone()
        if row is None:
            return None
        return float(row["mtime"])

    def count_indexed(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM note_index").fetchone()
        return int(row["n"]) if row else 0
