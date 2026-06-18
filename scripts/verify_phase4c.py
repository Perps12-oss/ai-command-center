#!/usr/bin/env python3
"""Phase 4C gate — overlay events + settings round-trip."""

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
    print("=== Phase 4C Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.db.connection import connect, init_database
    from ai_command_center.db.repository import SettingsRepository
    from ai_command_center.services.settings_service import SettingsService

    with tempfile.TemporaryDirectory() as tmp:
        db = connect(Path(tmp) / "settings.db")
        init_database(db)
        try:
            bus = EventBus(debug_mode=True)
            events: list[str] = []
            payloads: dict[str, dict] = {}

            def tap(event) -> None:
                events.append(event.topic)
                payloads[event.topic] = dict(event.payload)

            bus.subscribe_all(tap)
            settings = SettingsService(bus, SettingsRepository(db))
            settings.load()

            bus.publish(
                "overlay.show",
                {"mode": "compact", "x": 100, "y": 200},
                source="test",
            )
            bus.publish("overlay.anchor", {"x": 150, "y": 250}, source="test")
            bus.publish("overlay.hide", {}, source="test")

            if not {"overlay.show", "overlay.anchor", "overlay.hide"}.issubset(set(events)):
                failures.append("overlay events not observed on bus")

            events.clear()
            start = time.perf_counter()
            bus.publish(
                "settings.set_request",
                {"key": "overlay_mode", "value": "compact"},
                source="test",
            )
            if not _wait(events, "settings.snapshot", timeout=3.0):
                failures.append("settings snapshot missing after set_request")
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            if elapsed_ms > 250.0:
                failures.append(f"settings round-trip too slow: {elapsed_ms:.1f} ms")
            snap = payloads.get("settings.snapshot", {})
            if snap.get("overlay_mode") != "compact":
                failures.append(f"overlay_mode not persisted: {snap.get('overlay_mode')}")

            settings.unload()
        finally:
            db.close()

    controller_src = (
        PROJECT_ROOT / "ai_command_center" / "ui" / "controller.py"
    ).read_text(encoding="utf-8")
    if "publish_overlay" not in controller_src:
        failures.append("UIController missing overlay publish helpers")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Phase 4C — overlay events + settings round-trip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
