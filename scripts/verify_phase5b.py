#!/usr/bin/env python3
"""Phase 5B gate — declarative plugin registry + catalog UI."""

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
    print("=== Phase 5B Gate Verification ===")
    failures: list[str] = []

    manifests = PROJECT_ROOT / "plugins" / "manifests"
    if not manifests.is_dir():
        failures.append("plugins/manifests directory missing")
    else:
        count = len(list(manifests.glob("*.yaml")))
        if count < 4:
            failures.append(f"expected >=4 manifests, got {count}")

    plugins_view = PROJECT_ROOT / "ai_command_center" / "ui" / "views" / "plugins_view.py"
    if not plugins_view.is_file():
        failures.append("plugins_view.py missing")

    ui_files = list((PROJECT_ROOT / "ai_command_center" / "ui").rglob("*.py"))
    ui_src = "\n".join(p.read_text(encoding="utf-8") for p in ui_files)
    if "PluginRegistryService" in ui_src or "plugin_registry_service" in ui_src:
        failures.append("UI must not import PluginRegistryService")

    from ai_command_center.application import create_application
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.services.plugin_registry_service import PluginRegistryService

    app = create_application(debug_mode=True)
    if app.services.get("plugin_registry") is None:
        failures.append("plugin_registry not registered")
    app.shutdown()

    bus = EventBus(debug_mode=True)
    events: list[str] = []
    payloads: dict[str, dict] = {}

    def tap(event) -> None:
        events.append(event.topic)
        payloads[event.topic] = dict(event.payload)

    bus.subscribe_all(tap)
    registry = PluginRegistryService(bus)
    registry.load()

    if not _wait(events, "plugin.catalog"):
        failures.append("plugin.catalog not published on load")
    else:
        plugins = payloads.get("plugin.catalog", {}).get("plugins", [])
        ids = {p.get("id") for p in plugins}
        for expected in ("shell", "chat", "notes", "memory"):
            if expected not in ids:
                failures.append(f"missing manifest plugin: {expected}")

    events.clear()
    bus.publish("plugin.disable_request", {"id": "chat"}, source="test")
    if not _wait(events, "plugin.error"):
        failures.append("core plugin disable should emit plugin.error")

    registry.unload()

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Phase 5B — plugin manifests, catalog, UI panel wired")
    print(f"  manifests: {sorted(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
