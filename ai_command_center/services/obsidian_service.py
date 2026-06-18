"""Obsidian vault integration — FTS search, read, write (Phase 3C)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.db.note_repository import NoteRepository
from ai_command_center.services.base import BaseService
from ai_command_center.services.command_router_service import (
    INTENT_NOTE_NEW,
    INTENT_NOTE_SEARCH,
)

_SKIP_DIRS = {".obsidian", ".trash", ".git"}
_MAX_NOTE_BYTES = 512_000


def _title_from_markdown(path: Path, body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or path.stem
    return path.stem


class ObsidianService(BaseService):
    """
    Keyword search over vault markdown via SQLite FTS5.

    No semantic vectors. No startup full-vault scan — indexes on first search/write.
    """

    name = "obsidian"

    def __init__(self, bus, repo: NoteRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._vault_path: Path | None = None
        self._selected_path: str | None = None
        self._selected_body: str | None = None
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe("settings.snapshot", self._on_settings_snapshot)
        )
        self._unsubscribers.append(
            self._bus.subscribe("command.routed", self._on_command_routed)
        )
        self._unsubscribers.append(
            self._bus.subscribe("note.select", self._on_note_select)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_settings_snapshot(self, event: Event) -> None:
        raw = str(event.payload.get("obsidian_vault_path", "")).strip()
        self._vault_path = Path(raw) if raw else None

    def get_context_notes(self) -> list[str]:
        """Note bodies selected for opt-in chat injection."""
        if not self._selected_body:
            return []
        label = self._selected_path or "selected_note"
        return [f"[{label}]\n{self._selected_body}"]

    @property
    def selected_path(self) -> str | None:
        return self._selected_path

    def _on_command_routed(self, event: Event) -> None:
        if event.source != "command_router":
            return
        intent = event.payload.get("intent")
        args = event.payload.get("args") or {}

        if intent == INTENT_NOTE_SEARCH:
            self._handle_search(str(args.get("query", "")))
        elif intent == INTENT_NOTE_NEW:
            self._handle_new_note(str(args.get("body", "")))

    def _on_note_select(self, event: Event) -> None:
        path = str(event.payload.get("path", "")).strip()
        if not path:
            return
        body = self.read_note(path)
        if body is None:
            self._bus.publish(
                "note.error",
                {"message": f"Could not read note: {path}"},
                source=self.name,
            )
            return
        self._selected_path = path
        self._selected_body = body
        self._bus.publish(
            "note.selected",
            {"path": path, "title": _title_from_markdown(Path(path), body)},
            source=self.name,
        )

    def _require_vault(self) -> Path | None:
        if self._vault_path is None or not self._vault_path.is_dir():
            self._bus.publish(
                "note.error",
                {
                    "message": (
                        "Obsidian vault not configured. Set obsidian_vault_path in settings."
                    )
                },
                source=self.name,
            )
            return None
        return self._vault_path

    def _handle_search(self, query: str) -> None:
        if not query:
            self._bus.publish(
                "note.error",
                {"message": "note: requires a search query"},
                source=self.name,
            )
            return
        vault = self._require_vault()
        if vault is None:
            return

        vault_files, vault_bytes = self._vault_stats(vault)
        index_start = time.perf_counter()
        indexed = self._index_vault_incremental(vault)
        index_ms = (time.perf_counter() - index_start) * 1000.0

        search_start = time.perf_counter()
        hits = self._repo.search(query)
        search_ms = (time.perf_counter() - search_start) * 1000.0

        self._bus.publish(
            "note.search_results",
            {
                "query": query,
                "results": [
                    {"path": h.path, "title": h.title, "snippet": h.snippet}
                    for h in hits
                ],
                "indexed_files": indexed,
                "vault_files": vault_files,
                "vault_bytes": vault_bytes,
                "index_ms": round(index_ms, 2),
                "search_ms": round(search_ms, 2),
            },
            source=self.name,
        )

    def _handle_new_note(self, body: str) -> None:
        if not body:
            self._bus.publish(
                "note.error",
                {"message": "new note: requires note body"},
                source=self.name,
            )
            return
        vault = self._require_vault()
        if vault is None:
            return

        inbox = vault / "Inbox"
        inbox.mkdir(exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path = inbox / f"Quick-{stamp}.md"
        title = _title_from_markdown(path, body)
        content = body if body.lstrip().startswith("#") else f"# {title}\n\n{body}"
        path.write_text(content, encoding="utf-8")
        self._index_file(vault, path)
        self._bus.publish(
            "note.created",
            {"path": str(path.relative_to(vault)).replace("\\", "/"), "title": title},
            source=self.name,
        )

    def read_note(self, rel_path: str) -> str | None:
        vault = self._vault_path
        if vault is None or not vault.is_dir():
            return None
        full = (vault / rel_path).resolve()
        try:
            full.relative_to(vault.resolve())
        except ValueError:
            return None
        if not full.is_file():
            return None
        try:
            return full.read_text(encoding="utf-8")
        except OSError:
            return None

    def _index_vault_incremental(self, vault: Path) -> int:
        count = 0
        for path in vault.rglob("*.md"):
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            if self._index_file(vault, path):
                count += 1
        return count

    def _index_file(self, vault: Path, path: Path) -> bool:
        try:
            stat = path.stat()
        except OSError:
            return False
        rel = str(path.relative_to(vault)).replace("\\", "/")
        if self._repo.indexed_mtime(rel) == stat.st_mtime:
            return False
        if stat.st_size > _MAX_NOTE_BYTES:
            return False
        try:
            body = path.read_text(encoding="utf-8")
        except OSError:
            return False
        title = _title_from_markdown(path, body)
        return self._repo.upsert(rel, title, body, stat.st_mtime)

    @staticmethod
    def _vault_stats(vault: Path) -> tuple[int, int]:
        files = 0
        total_bytes = 0
        for path in vault.rglob("*.md"):
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            files += 1
            try:
                total_bytes += path.stat().st_size
            except OSError:
                continue
        return files, total_bytes
