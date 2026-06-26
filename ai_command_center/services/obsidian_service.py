"""Obsidian vault integration — FTS search, read, write (Phase 3C + 4A async index)."""

from __future__ import annotations

import queue
import sqlite3
import threading
import time
from pathlib import Path
from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    COMMAND_ROUTED,
    NOTE_CONTEXT_REQUEST,
    NOTE_CONTEXT_RESULT,
    NOTE_CREATED,
    NOTE_ERROR,
    NOTE_INDEX_COMPLETE,
    NOTE_INDEX_PROGRESS,
    NOTE_SEARCH_RESULTS,
    NOTE_SELECT,
    NOTE_SELECTED,
    SETTINGS_SNAPSHOT,
)
from ai_command_center.repositories.note_repository import NoteRepository
from ai_command_center.services.base import BaseService
from ai_command_center.services.command_router_service import (
    INTENT_NOTE_NEW,
    INTENT_NOTE_SEARCH,
)

_SKIP_DIRS = {".obsidian", ".trash", ".git"}
_MAX_NOTE_BYTES = 512_000
_PROGRESS_EVERY = 25


def _title_from_markdown(path: Path, body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or path.stem
    return path.stem


class ObsidianService(BaseService):
    """
    Keyword search over vault markdown via SQLite FTS5.

    Phase 4A: vault scan/index I/O runs on a background worker — EventBus handlers
    only perform SQLite FTS reads and enqueue index jobs.
    """

    name = "obsidian"

    def __init__(self, bus, repo) -> None:
        super().__init__(bus)
        self._repo = self._coerce_repo(repo)
        self._repo_lock = threading.Lock()
        self._vault_path: Path | None = None
        self._selected_path: str | None = None
        self._selected_body: str | None = None
        self._unsubscribers: list[Callable[[], None]] = []
        self._index_queue: queue.SimpleQueue[Path | None] = queue.SimpleQueue()
        self._index_stop = threading.Event()
        self._index_thread: threading.Thread | None = None
        self._index_in_progress = False
        self._pending_search_query: str | None = None
        self._last_vault_stats: tuple[int, int] = (0, 0)

    @staticmethod
    def _coerce_repo(repo):
        if hasattr(repo, "set_vault_path") and hasattr(repo, "read_note") and hasattr(repo, "iter_markdown_files"):
            return repo
        conn = getattr(repo, "_conn", None)
        if conn is None:
            raise TypeError("ObsidianService requires a repository with vault file APIs")
        return NoteRepository(conn)

    def _on_load(self) -> None:
        self._repo.set_vault_path(None)
        self._index_stop.clear()
        self._index_thread = threading.Thread(
            target=self._index_worker,
            name="obsidian-index",
            daemon=True,
        )
        self._index_thread.start()
        self._unsubscribers.append(self._bus.subscribe(SETTINGS_SNAPSHOT, self._on_settings_snapshot))
        self._unsubscribers.append(self._bus.subscribe(COMMAND_ROUTED, self._on_command_routed))
        self._unsubscribers.append(self._bus.subscribe(NOTE_SELECT, self._on_note_select))
        self._unsubscribers.append(self._bus.subscribe(NOTE_CONTEXT_REQUEST, self._on_note_context_request))

    def _apply_vault_path(self, raw: str) -> None:
        path = str(raw or "").strip()
        self._vault_path = Path(path) if path else None
        self._repo.set_vault_path(self._vault_path)
        if self._vault_path is not None and self._vault_path.is_dir():
            self._schedule_index(self._vault_path)

    def _on_unload(self) -> None:
        self._index_stop.set()
        self._index_queue.put(None)
        if self._index_thread is not None:
            self._index_thread.join(timeout=3.0)
            self._index_thread = None
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_settings_snapshot(self, event: Event) -> None:
        self._apply_vault_path(str(event.payload.get("obsidian_vault_path", "")))

    def _on_note_context_request(self, event: Event) -> None:
        self._bus.publish(
            NOTE_CONTEXT_RESULT,
            {
                "request_id": event.payload.get("request_id", ""),
                "notes": self.get_context_notes(),
                "selected_path": self._selected_path,
            },
            source=self.name,
        )

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
                NOTE_ERROR,
                {"message": f"Could not read note: {path}"},
                source=self.name,
            )
            return
        self._selected_path = path
        self._selected_body = body
        self._bus.publish(
            NOTE_SELECTED,
            {"path": path, "title": _title_from_markdown(Path(path), body), "body": body},
            source=self.name,
        )

    def _require_vault(self) -> Path | None:
        if self._vault_path is None or not self._vault_path.is_dir():
            self._bus.publish(
                NOTE_ERROR,
                {
                    "message": (
                        "Obsidian vault not configured. Set obsidian_vault_path in settings."
                    )
                },
                source=self.name,
            )
            return None
        return self._vault_path

    def _schedule_index(self, vault: Path) -> None:
        if self._index_in_progress:
            return
        self._index_queue.put(vault)

    def _handle_search(self, query: str) -> None:
        if not query:
            self._bus.publish(
                NOTE_ERROR,
                {"message": "note: requires a search query"},
                source=self.name,
            )
            return
        vault = self._require_vault()
        if vault is None:
            return

        self._pending_search_query = query
        self._schedule_index(vault)

        search_start = time.perf_counter()
        with self._repo_lock:
            hits = self._repo.search(query)
        search_ms = (time.perf_counter() - search_start) * 1000.0

        indexing = self._index_in_progress
        self._publish_search_results(query, hits, search_ms=search_ms, indexing=indexing)
        if hits or not indexing:
            self._pending_search_query = None

    def _publish_search_results(
        self,
        query: str,
        hits,
        *,
        search_ms: float,
        indexing: bool,
    ) -> None:
        vault_files, vault_bytes = self._last_vault_stats
        with self._repo_lock:
            indexed_count = self._repo.count_indexed()
        self._bus.publish(
            NOTE_SEARCH_RESULTS,
            {
                "query": query,
                "results": [
                    {"path": h.path, "title": h.title, "snippet": h.snippet}
                    for h in hits
                ],
                "indexed_files": indexed_count,
                "vault_files": vault_files,
                "vault_bytes": vault_bytes,
                "index_ms": 0.0,
                "search_ms": round(search_ms, 2),
                "indexing": indexing,
            },
            source=self.name,
        )

    def _handle_new_note(self, body: str) -> None:
        if not body:
            self._bus.publish(
                NOTE_ERROR,
                {"message": "new note: requires note body"},
                source=self.name,
            )
            return
        vault = self._require_vault()
        if vault is None:
            return

        inbox = vault / "Inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path = inbox / f"Quick-{stamp}.md"
        title = _title_from_markdown(path, body)
        content = body if body.lstrip().startswith("#") else f"# {title}\n\n{body}"
        written = self._repo.write_note(path.relative_to(vault), content)
        if written is None:
            self._bus.publish(
                NOTE_ERROR,
                {"message": "Could not write note to vault"},
                source=self.name,
            )
            return
        self._index_file(vault, path)
        self._bus.publish(
            NOTE_CREATED,
            {"path": str(path.relative_to(vault)).replace("\\", "/"), "title": title},
            source=self.name,
        )

    def read_note(self, rel_path: str) -> str | None:
        return self._repo.read_note(rel_path)

    def _index_worker(self) -> None:
        while not self._index_stop.is_set():
            try:
                vault = self._index_queue.get(timeout=0.25)
            except queue.Empty:
                continue
            if vault is None or self._index_stop.is_set():
                break
            self._run_incremental_index(vault)

    def _run_incremental_index(self, vault: Path) -> None:
        self._index_in_progress = True
        index_start = time.perf_counter()
        indexed = 0
        scanned = 0
        vault_files = 0
        vault_bytes = 0
        try:
            for path in self._repo.iter_markdown_files():
                if self._index_stop.is_set():
                    return
                if any(part in _SKIP_DIRS for part in path.parts):
                    continue
                scanned += 1
                try:
                    vault_bytes += path.stat().st_size
                except OSError:
                    pass
                vault_files += 1
                if self._index_file(vault, path):
                    indexed += 1
                if scanned % _PROGRESS_EVERY == 0:
                    self._bus.publish(
                        NOTE_INDEX_PROGRESS,
                        {
                            "scanned_files": scanned,
                            "indexed_files": indexed,
                            "vault_files": vault_files,
                        },
                        source=self.name,
                    )
        finally:
            elapsed_ms = (time.perf_counter() - index_start) * 1000.0
            self._last_vault_stats = (vault_files, vault_bytes)
            self._index_in_progress = False
            with self._repo_lock:
                total_indexed = self._repo.count_indexed()
            self._bus.publish(
                NOTE_INDEX_COMPLETE,
                {
                    "scanned_files": scanned,
                    "indexed_files": total_indexed,
                    "new_or_updated": indexed,
                    "vault_files": vault_files,
                    "vault_bytes": vault_bytes,
                    "index_ms": round(elapsed_ms, 2),
                },
                source=self.name,
            )
            pending = self._pending_search_query
            if pending:
                search_start = time.perf_counter()
                with self._repo_lock:
                    hits = self._repo.search(pending)
                search_ms = (time.perf_counter() - search_start) * 1000.0
                self._publish_search_results(
                    pending, hits, search_ms=search_ms, indexing=False
                )
                self._pending_search_query = None

    def _index_file(self, vault: Path, path: Path) -> bool:
        try:
            stat = path.stat()
        except OSError:
            return False
        rel = str(path.relative_to(vault)).replace("\\", "/")
        with self._repo_lock:
            if self._repo.indexed_mtime(rel) == stat.st_mtime:
                return False
        if stat.st_size > _MAX_NOTE_BYTES:
            return False
        body = self._repo.read_note(rel)
        if body is None:
            return False
        title = _title_from_markdown(path, body)
        try:
            with self._repo_lock:
                return self._repo.upsert(rel, title, body, stat.st_mtime)
        except sqlite3.IntegrityError as exc:
            self._bus.publish(
                NOTE_ERROR,
                {"message": f"Could not index {rel}: {exc}"},
                source=self.name,
            )
            return False
