#!/usr/bin/env python3
"""Phase 4E gate — explicit memory graph opt-in."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _wait(events: list[str], topic: str, timeout: float = 5.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if topic in events:
            return True
        time.sleep(0.02)
    return False


def main() -> int:
    print("=== Phase 4E Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.core.context_manager import ContextManager
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.db.connection import connect, init_database
    from ai_command_center.repositories.memory_repository import MemoryRepository
    from ai_command_center.services.memory_graph_service import MemoryGraphService

    with tempfile.TemporaryDirectory() as tmp:
        db = connect(Path(tmp) / "mem.db")
        init_database(db)
        try:
            bus = EventBus(debug_mode=True)
            events: list[str] = []
            payloads: dict[str, dict] = {}

            def tap(event) -> None:
                events.append(event.topic)
                payloads[event.topic] = dict(event.payload)

            bus.subscribe_all(tap)
            memory = MemoryGraphService(bus, MemoryRepository(db))
            memory.load()

            bus.publish(
                "memory.remember",
                {
                    "label": "ProjectAlpha",
                    "content": "ALPHA_MEMORY_MARKER ships in Q3.",
                },
                source="test",
            )
            if not _wait(events, "memory.stored"):
                failures.append("memory.remember did not store")

            bus.publish(
                "memory.select",
                {"query": "ProjectAlpha"},
                source="test",
            )
            if not _wait(events, "memory.selected"):
                failures.append("memory.select failed")

            snippets = memory.get_context_snippets()
            if not snippets or "ALPHA_MEMORY_MARKER" not in snippets[0]:
                failures.append("selected snippet missing marker")

            bundle = ContextManager().build_context(
                "What ships?",
                graph_snippets=snippets,
            )
            if "ALPHA_MEMORY_MARKER" not in bundle.prompt:
                failures.append("graph snippet not in ContextBundle")
            if not any(s.startswith("memory_graph_") for s in bundle.sources):
                failures.append("memory_graph source missing")

            memory.unload()
        finally:
            db.close()

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Phase 4E — explicit memory graph opt-in")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
