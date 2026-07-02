#!/usr/bin/env python3
"""
Note integration audits for Phase 3D review (from 3C findings).

1. First Search Latency — cold index baseline (vault size, index_ms, search_ms)
2. Context Pollution — search B without select must not inject B into chat context
"""

from __future__ import annotations

import json
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


def _build_vault(vault: Path, *, file_count: int = 40) -> tuple[int, int]:
    """Populate vault with markdown files; return (file_count, total_bytes)."""
    total_bytes = 0
    for i in range(file_count):
        body = f"# Note {i}\n\nKeyword token{i} baseline content for cold index.\n"
        path = vault / f"notes/note-{i:03d}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        total_bytes += path.stat().st_size
    return file_count, total_bytes


def test_first_search_latency() -> dict:
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.db.connection import connect, init_database
    from ai_command_center.repositories.note_repository import NoteRepository
    from ai_command_center.services.command_router_service import CommandRouterService
    from ai_command_center.services.obsidian_service import ObsidianService

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        vault = tmp_path / "vault"
        vault.mkdir()
        expected_files, expected_bytes = _build_vault(vault, file_count=40)

        db = connect(tmp_path / "latency.db")
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
                source="audit",
            )

            search_start = time.perf_counter()
            bus.publish("ui.command", {"text": "note:token5"}, source="audit")
            ok = _wait_for(events, "note.search_results", timeout=5.0)
            search_first_ms = (time.perf_counter() - search_start) * 1000.0

            index_ok = _wait_for(events, "note.index_complete", timeout=15.0)
            search_total_ms = search_first_ms
            if index_ok:
                # Phase 4A: refreshed results may arrive after index_complete
                end = time.time() + 5.0
                while time.time() < end:
                    result = payloads.get("note.search_results", {})
                    if result.get("results"):
                        break
                    time.sleep(0.02)

            router.unload()
            obsidian.unload()

            if not ok:
                return {"pass": False, "error": "note.search_results timeout"}
            if not index_ok:
                return {"pass": False, "error": "note.index_complete timeout"}

            result = payloads.get("note.search_results", {})
            complete = payloads.get("note.index_complete", {})
            if not result.get("results"):
                return {"pass": False, "error": "no hits after async index"}

            return {
                "pass": True,
                "vault_files": complete.get("vault_files", result.get("vault_files")),
                "vault_bytes": complete.get("vault_bytes", result.get("vault_bytes")),
                "indexed_files": complete.get("indexed_files", result.get("indexed_files")),
                "index_ms": complete.get("index_ms"),
                "search_ms": result.get("search_ms"),
                "search_first_ms": round(search_first_ms, 2),
                "search_total_ms": round(search_total_ms, 2),
            }
        finally:
            db.close()


def test_context_pollution() -> dict:
    from ai_command_center.core.context_manager import ContextBundle, ContextManager
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.db.connection import connect, init_database
    from ai_command_center.repositories.note_repository import NoteRepository
    from ai_command_center.services.chat_handler_service import ChatHandlerService
    from ai_command_center.services.command_router_service import CommandRouterService
    from ai_command_center.services.obsidian_service import ObsidianService
    from ai_command_center.services.ollama_service import StubOllamaService

    class RecordingStub(StubOllamaService):
        last_bundle: ContextBundle | None = None

        def stream_chat(self, bundle, *, model, request_id=None):
            RecordingStub.last_bundle = bundle
            return super().stream_chat(bundle, model=model, request_id=request_id)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "alpha.md").write_text(
            "# Alpha\n\nALPHA_UNIQUE_MARKER content for note A.\n",
            encoding="utf-8",
        )
        (vault / "beta.md").write_text(
            "# Beta\n\nBETA_UNIQUE_MARKER content for note B.\n",
            encoding="utf-8",
        )

        db = connect(tmp_path / "pollution.db")
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
            ollama = RecordingStub(bus)
            handler = ChatHandlerService(bus, ContextManager(), obsidian)
            for svc in (router, obsidian, ollama, handler):
                svc.load()

            bus.publish(
                "settings.snapshot",
                {"obsidian_vault_path": str(vault), "default_model": "test"},
                source="audit",
            )

            events.clear()
            bus.publish("ui.command", {"text": "note:ALPHA"}, source="audit")
            end = time.time() + 15.0
            while time.time() < end:
                if "note.search_results" in events:
                    r = payloads.get("note.search_results", {}).get("results", [])
                    if r:
                        break
                time.sleep(0.02)
            else:
                return {"pass": False, "error": "search A failed"}
            bus.publish("note.select", {"path": "alpha.md"}, source="audit")
            if not _wait_for(events, "note.selected"):
                return {"pass": False, "error": "select A failed"}

            events.clear()
            bus.publish("ui.command", {"text": "note:BETA"}, source="audit")
            end = time.time() + 15.0
            while time.time() < end:
                if "note.search_results" in events:
                    r = payloads.get("note.search_results", {}).get("results", [])
                    if r:
                        break
                time.sleep(0.02)
            else:
                return {"pass": False, "error": "search B failed"}

            events.clear()
            RecordingStub.last_bundle = None
            bus.publish(
                "ui.command",
                {"text": "Summarize the selected note"},
                source="audit",
            )
            if not _wait_for(events, "chat.started"):
                return {"pass": False, "error": "chat did not start"}

            bundle = RecordingStub.last_bundle
            started = payloads.get("chat.started", {})
            sources = list(started.get("sources", []))

            for svc in (handler, ollama, obsidian, router):
                svc.unload()

            if bundle is None:
                return {"pass": False, "error": "no ContextBundle captured"}

            alpha_in = "ALPHA_UNIQUE_MARKER" in bundle.prompt
            beta_in = "BETA_UNIQUE_MARKER" in bundle.prompt
            note_sources = [s for s in sources if str(s).startswith("note_")]

            return {
                "pass": alpha_in and not beta_in and len(note_sources) == 1,
                "alpha_in_prompt": alpha_in,
                "beta_in_prompt": beta_in,
                "sources": sources,
                "note_source_count": len(note_sources),
            }
        finally:
            db.close()


def main() -> int:
    print("=== Note Integration Audit (3D review checks) ===\n")

    failures: list[str] = []

    print("--- First Search Latency (cold index) ---")
    latency = test_first_search_latency()
    if not latency.get("pass"):
        failures.append(f"latency test: {latency.get('error', 'failed')}")
        print(json.dumps(latency, indent=2))
    else:
        print(f"  Vault files:  {latency['vault_files']}")
        print(f"  Vault bytes:  {latency['vault_bytes']}")
        print(f"  Indexed:      {latency['indexed_files']} file(s)")
        print(f"  Index time:   {latency['index_ms']} ms")
        print(f"  Search time:  {latency['search_ms']} ms")
        print(f"  First reply:  {latency.get('search_first_ms', latency['search_total_ms'])} ms")
        print(f"  Total (cmd):  {latency['search_total_ms']} ms")

    print("\n--- Context Pollution ---")
    pollution = test_context_pollution()
    print(json.dumps(pollution, indent=2))
    if not pollution.get("pass"):
        err = pollution.get("error", "context pollution check failed")
        failures.append(f"context pollution: {err}")

    if failures:
        print("\nFAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("\nPASS: latency baseline recorded, context pollution check clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
