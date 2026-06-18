#!/usr/bin/env python3
"""Gate: versioned contracts locked for Phase 3 → 4 transition."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=== Contract Version Gate ===")
    failures: list[str] = []

    from ai_command_center.core.context_manager import ContextBundle, ContextManager
    from ai_command_center.core.contracts import (
        COMMAND_ROUTED_VERSION,
        CONTEXT_BUNDLE_VERSION,
        OLLAMA_SERVICE_API_VERSION,
        SUPPORTED_VERSIONS,
    )
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.services.command_router_service import CommandRouterService
    from ai_command_center.services.ollama_service import OllamaServiceBase

    bundle = ContextManager().build_context("test")
    if bundle.version != CONTEXT_BUNDLE_VERSION:
        failures.append(f"ContextBundle.version expected {CONTEXT_BUNDLE_VERSION}")
    if bundle.version not in SUPPORTED_VERSIONS["context_bundle"]:
        failures.append("ContextBundle version not in SUPPORTED_VERSIONS")

    bus = EventBus(debug_mode=True)
    payloads: list[dict] = []
    bus.subscribe("command.routed", lambda e: payloads.append(dict(e.payload)))
    router = CommandRouterService(bus)
    router.load()
    bus.publish("ui.command", {"text": "hello"}, source="test")
    router.unload()

    if not payloads:
        failures.append("no command.routed payload captured")
    else:
        p = payloads[0]
        if p.get("contract_version") != COMMAND_ROUTED_VERSION:
            failures.append("command.routed missing contract_version")
        if p.get("metadata", {}).get("executing") is not False:
            failures.append("command.routed metadata.executing must be False")

    for method in ("stream_chat", "stream", "chat", "cancel"):
        if not hasattr(OllamaServiceBase, method):
            failures.append(f"OllamaServiceBase missing {method}")
    if OllamaServiceBase.api_version != OLLAMA_SERVICE_API_VERSION:
        failures.append("OllamaServiceBase.api_version mismatch")

    router_src = inspect.getsource(CommandRouterService._on_ui_command)
    if "contract_version" not in router_src:
        failures.append("CommandRouter must publish contract_version")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Contracts v1.0 locked")
    print(f"  ContextBundle: {CONTEXT_BUNDLE_VERSION}")
    print(f"  command.routed: {COMMAND_ROUTED_VERSION}")
    print(f"  OllamaService API: {OLLAMA_SERVICE_API_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
