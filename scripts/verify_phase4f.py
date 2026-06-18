#!/usr/bin/env python3
"""Phase 4F gate — model router intent mapping."""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=== Phase 4F Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.services.model_router_service import ModelRouterService

    bus = EventBus(debug_mode=True)
    events: list[str] = []
    payloads: dict[str, dict] = {}

    def tap(event) -> None:
        events.append(event.topic)
        payloads[event.topic] = dict(event.payload)

    bus.subscribe_all(tap)
    router = ModelRouterService(bus)
    router.load()
    bus.publish(
        "settings.snapshot",
        {"default_model": "llama3.2:3b", "summarize_model": "llama3.2:1b"},
        source="test",
    )

    model = router.resolve(intent="chat", query="Summarize this clipboard")
    if model != "llama3.2:1b":
        failures.append(f"summarize query expected llama3.2:1b, got {model}")
    if "model.selected" not in events:
        failures.append("model.selected not published")

    events.clear()
    model2 = router.resolve(intent="chat", query="What is Python?")
    if model2 != "llama3.2:3b":
        failures.append(f"generic chat expected default model, got {model2}")

    bus.publish(
        "settings.set_request",
        {"key": "default_model", "value": "custom:7b"},
        source="test",
    )
    time.sleep(0.05)
    bus.publish(
        "settings.snapshot",
        {"default_model": "custom:7b", "summarize_model": "llama3.2:1b"},
        source="test",
    )
    model3 = router.resolve(intent="chat", query="hello")
    if model3 != "custom:7b":
        failures.append(f"settings override expected custom:7b, got {model3}")

    router.unload()

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Phase 4F — model router intent + settings override")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
