#!/usr/bin/env python3
"""Phase 5A gate — Phase 4 features wired for daily-driver UX."""

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
    print("=== Phase 5A Gate Verification ===")
    failures: list[str] = []

    app_src = (PROJECT_ROOT / "ai_command_center" / "ui" / "app.py").read_text(encoding="utf-8")
    for needle in ("tool.result", "model.selected", "memory.stored"):
        if needle not in app_src:
            failures.append(f"app.py must subscribe to {needle}")

    chat_src = (
        PROJECT_ROOT / "ai_command_center" / "ui" / "views" / "chat" / "chat_view.py"
    ).read_text(encoding="utf-8")
    if "show_tool_output" not in chat_src:
        failures.append("ChatView missing show_tool_output")

    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.db.connection import connect, init_database
    from ai_command_center.repositories.memory_repository import MemoryRepository
    from ai_command_center.services.command_router_service import CommandRouterService
    from ai_command_center.services.memory_graph_service import MemoryGraphService
    from ai_command_center.services.model_router_service import ModelRouterService
    from ai_command_center.services.shell_tool_service import ShellToolService
    from ai_command_center.services.tool_executor_service import ToolExecutorService
    from ai_command_center.services.tool_registry_service import ToolRegistryService

    with tempfile.TemporaryDirectory() as tmp:
        db = connect(Path(tmp) / "phase5a.db")
        init_database(db)
        try:
            bus = EventBus(debug_mode=True)
            events: list[str] = []
            payloads: dict[str, dict] = {}

            def tap(event) -> None:
                events.append(event.topic)
                payloads[event.topic] = dict(event.payload)

            bus.subscribe_all(tap)

            registry = ToolRegistryService(bus)
            executor = ToolExecutorService(bus, registry)
            router = CommandRouterService(bus)
            shell = ShellToolService(bus)
            memory = MemoryGraphService(bus, MemoryRepository(db))
            model_router = ModelRouterService(bus)
            for svc in (registry, executor, router, shell, memory, model_router):
                svc.load()

            bus.publish(
                "settings.snapshot",
                {"default_model": "llama3.2:3b", "summarize_model": "llama3.2:1b"},
                source="test",
            )

            events.clear()
            bus.publish(
                "ui.command",
                {"text": "remember: Alpha | ALPHA_MARKER content"},
                source="test",
            )
            if not _wait(events, "memory.stored"):
                failures.append("remember: command did not store memory")

            events.clear()
            bus.publish("ui.command", {"text": "memory: Alpha"}, source="test")
            if not _wait(events, "memory.selected"):
                failures.append("memory: command did not select memory")
            if not memory.get_context_snippets():
                failures.append("memory snippets empty after memory:")

            events.clear()
            bus.publish("ui.command", {"text": "> echo phase5a"}, source="test")
            if not _wait(events, "tool.result"):
                failures.append("shell tool did not return result")

            events.clear()
            model_router.resolve(intent="chat", query="Summarize this")
            if not _wait(events, "model.selected"):
                failures.append("model.selected not published")

            for svc in (model_router, memory, shell, router, executor, registry):
                svc.unload()
        finally:
            db.close()

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Phase 5A — memory commands, shell output path, model.selected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
