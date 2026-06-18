#!/usr/bin/env python3
"""Phase 4A gate — async Obsidian vault indexing (closes V-001)."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _wait_for(events: list[str], topic: str, timeout: float = 10.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if topic in events:
            return True
        time.sleep(0.02)
    return False


def _wait_for_results_with_hits(
    events: list[str], payloads: dict[str, dict], timeout: float = 15.0
) -> dict | None:
    end = time.time() + timeout
    while time.time() < end:
        for topic in reversed(events):
            if topic != "note.search_results":
                continue
            payload = payloads.get(topic, {})
            if payload.get("results"):
                return payload
        time.sleep(0.02)
    return None


def main() -> int:
    print("=== Phase 4A Gate Verification ===")
    failures: list[str] = []

    obsidian_path = PROJECT_ROOT / "ai_command_center" / "services" / "obsidian_service.py"
    src = obsidian_path.read_text(encoding="utf-8")
    handle_src = src.split("def _handle_search", 1)
    if len(handle_src) < 2:
        failures.append("_handle_search missing")
    else:
        block = handle_src[1].split("\n    def ", 1)[0]
        if "rglob" in block:
            failures.append("_handle_search must not call rglob (V-001)")

    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.db.connection import connect, init_database
    from ai_command_center.db.note_repository import NoteRepository
    from ai_command_center.services.command_router_service import CommandRouterService
    from ai_command_center.services.obsidian_service import ObsidianService

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        vault = tmp_path / "vault"
        (vault / "notes").mkdir(parents=True)
        for i in range(40):
            (vault / "notes" / f"note-{i:03d}.md").write_text(
                f"# Note {i}\n\nKeyword token{i} async index gate.\n",
                encoding="utf-8",
            )

        db = connect(tmp_path / "gate4a.db")
        init_database(db)
        try:
            bus = EventBus(debug_mode=True)
            events: list[str] = []
            payloads: dict[str, dict] = {}

            def tap(event) -> None:
                events.append(event.topic)
                payloads[event.topic] = dict(event.payload)

            bus.subscribe_all(tap)

            router = CommandRouterService(bus)
            obsidian = ObsidianService(bus, NoteRepository(db))
            router.load()
            obsidian.load()
            bus.publish(
                "settings.snapshot",
                {"obsidian_vault_path": str(vault)},
                source="test",
            )

            events.clear()
            search_start = time.perf_counter()
            bus.publish("ui.command", {"text": "note:token5"}, source="test")
            if not _wait_for(events, "note.search_results", timeout=3.0):
                failures.append("first note.search_results timeout")
            first_ms = (time.perf_counter() - search_start) * 1000.0
            first = payloads.get("note.search_results", {})
            if first_ms > 250.0:
                failures.append(
                    f"bus-thread search too slow: {first_ms:.1f} ms (limit 250)"
                )

            if not _wait_for(events, "note.index_complete", timeout=15.0):
                failures.append("note.index_complete timeout")
            else:
                complete = payloads.get("note.index_complete", {})
                if int(complete.get("vault_files", 0)) < 40:
                    failures.append(
                        f"expected 40 vault files indexed, got {complete.get('vault_files')}"
                    )

            hits_payload = _wait_for_results_with_hits(events, payloads, timeout=5.0)
            if hits_payload is None:
                failures.append("no search results with hits after index complete")
            else:
                paths = [r.get("path") for r in hits_payload.get("results", [])]
                if not any("note-005" in str(p) for p in paths):
                    failures.append(f"token5 search missed note-005: {paths}")

            router.unload()
            obsidian.unload()
        finally:
            db.close()

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Phase 4A — async vault index off EventBus thread")
    print(f"  first search on bus thread: {first_ms:.1f} ms")
    print("  note.index_complete + refreshed search results")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
