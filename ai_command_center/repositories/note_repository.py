"""Repository for note indexing and note file access."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ai_command_center.db.note_repository import NoteHit, NoteRepository as DbNoteRepository
from ai_command_center.repositories.vault_repository import VaultRepository


class NoteRepository:
    """Owns note indexing plus vault file IO for the Obsidian service."""

    def __init__(self, conn: sqlite3.Connection, vault_repo: VaultRepository | None = None) -> None:
        self._db_repo = DbNoteRepository(conn)
        self._vault_repo = vault_repo or VaultRepository()

    def upsert(self, path: str, title: str, body: str, mtime: float) -> bool:
        return self._db_repo.upsert(path, title, body, mtime)

    def remove(self, path: str) -> None:
        self._db_repo.remove(path)

    def search(self, query: str, *, limit: int = 20) -> list[NoteHit]:
        return self._db_repo.search(query, limit=limit)

    def get_body(self, path: str) -> str | None:
        return self._db_repo.get_body(path)

    def indexed_mtime(self, path: str) -> float | None:
        return self._db_repo.indexed_mtime(path)

    def count_indexed(self) -> int:
        return self._db_repo.count_indexed()

    def read_note(self, rel_path: str | Path) -> str | None:
        return self._vault_repo.read_note(rel_path)

    def write_note(self, rel_path: str | Path, content: str) -> Path | None:
        return self._vault_repo.write_note(rel_path, content)

    def set_vault_path(self, vault_path: str | Path | None) -> None:
        self._vault_repo.set_vault_path(vault_path)

    def get_vault_path(self) -> Path | None:
        return self._vault_repo.get_vault_path()

    def relative_path(self, path: Path) -> str:
        return self._vault_repo.relative_path(path)

    def iter_markdown_files(self):
        return self._vault_repo.iter_markdown_files()
