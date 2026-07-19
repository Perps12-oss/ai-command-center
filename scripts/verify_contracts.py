#!/usr/bin/env python3
"""Gate: versioned contracts locked for Phase 3 → 4 transition."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=== Contract Version Gate ===")
    failures: list[str] = []

    from ai_command_center.core.context_manager import ContextManager
    from ai_command_center.core.contracts import (
        CONTEXT_BUNDLE_VERSION,
        OLLAMA_SERVICE_API_VERSION,
    )
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.core.events.topics import (
        EXECUTION_AUTHORITY_DECISION,
        UI_COMMAND,
        WORKSPACE_ACTIVE,
    )
    from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
    from ai_command_center.services.ollama_service import OllamaServiceBase

    bundle = ContextManager().build_context("test")
    if bundle.version != CONTEXT_BUNDLE_VERSION:
        failures.append(f"ContextBundle.version expected {CONTEXT_BUNDLE_VERSION}")

    bus = EventBus(debug_mode=True)
    payloads: list[dict] = []
    bus.subscribe(EXECUTION_AUTHORITY_DECISION, lambda e: payloads.append(dict(e.payload)))
    authority = ExecutionAuthorityService(bus)
    authority.load()
    bus.publish(WORKSPACE_ACTIVE, {"workspace_id": "contract-test"}, source="test")
    bus.publish(UI_COMMAND, {"text": "hello"}, source="test")
    authority.unload()

    if not payloads:
        failures.append("no execution.authority.decision payload captured")
    else:
        p = payloads[0]
        if p.get("kind") != "conversational":
            failures.append("execution.authority.decision expected conversational kind")
        if p.get("capability") != "llm":
            failures.append("execution.authority.decision expected llm capability")
        if p.get("workspace_id") != "contract-test":
            failures.append("execution.authority.decision missing workspace scope")

    for method in ("stream_chat", "stream", "chat", "cancel"):
        if not hasattr(OllamaServiceBase, method):
            failures.append(f"OllamaServiceBase missing {method}")
    if OllamaServiceBase.api_version != OLLAMA_SERVICE_API_VERSION:
        failures.append("OllamaServiceBase.api_version mismatch")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Contracts v1.0 locked")
    print(f"  ContextBundle: {CONTEXT_BUNDLE_VERSION}")
    print("  execution.authority.decision: runtime intake")
    print(f"  OllamaService API: {OLLAMA_SERVICE_API_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
