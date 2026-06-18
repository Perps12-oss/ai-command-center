#!/usr/bin/env python3
"""Phase 4B gate — tool registry, executor, shell intent."""

from __future__ import annotations

import sys
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
    print("=== Phase 4B Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.services.command_router_service import CommandRouterService
    from ai_command_center.services.shell_tool_service import ShellToolService
    from ai_command_center.services.tool_executor_service import ToolExecutorService
    from ai_command_center.services.tool_registry_service import ToolRegistryService

    bus = EventBus(debug_mode=True)
    events: list[str] = []
    payloads: dict[str, dict] = {}

    def tap(event) -> None:
        events.append(event.topic)
        payloads[event.topic] = dict(event.payload)

    bus.subscribe_all(tap)

    registry = ToolRegistryService(bus)
    executor = ToolExecutorService(bus, registry)
    shell_bridge = ShellToolService(bus)
    router = CommandRouterService(bus)
    for svc in (registry, executor, shell_bridge, router):
        svc.load()

    bus.publish("ui.command", {"text": "> echo hello"}, source="test")
    if not _wait(events, "tool.invoke"):
        failures.append("shell command did not produce tool.invoke")
    elif payloads.get("tool.invoke", {}).get("tool") != "shell":
        failures.append("tool.invoke missing shell tool name")

    if not _wait(events, "tool.result", timeout=10.0):
        failures.append("> echo hello did not produce tool.result")
    else:
        output = str(payloads.get("tool.result", {}).get("output", "")).lower()
        if "hello" not in output:
            failures.append(f"unexpected shell output: {output!r}")

    executor_src = (
        PROJECT_ROOT / "ai_command_center" / "services" / "tool_executor_service.py"
    ).read_text(encoding="utf-8")
    if "agent_loop" in executor_src.lower() or "while True" in executor_src:
        failures.append("tool executor must not contain agent loops")

    for svc in (router, shell_bridge, executor, registry):
        svc.unload()

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Phase 4B — tool.invoke -> shell -> tool.result")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
