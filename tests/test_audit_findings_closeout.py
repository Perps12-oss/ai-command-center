"""Regression tests for architecture-audit closeout P0/P1/P2 repairs."""

from __future__ import annotations

import threading
import time

import pytest

from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_DISPATCH_REQUEST,
    TOOL_INVOKE,
    TOOL_RESULT,
    TOOL_STARTED,
    UI_COMMAND,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.platform.secret_store import SecretStoreError, store_openai_api_key
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry


def test_tool_executor_worker_offloads_when_not_inline(monkeypatch) -> None:
    monkeypatch.delenv("ACC_TOOL_EXEC_INLINE", raising=False)
    bus = EventBus()
    registry = ToolRegistry()
    started = threading.Event()

    def _slow(_args: object) -> ToolResult:
        started.wait(timeout=1.0)
        time.sleep(0.05)
        return ToolResult(success=True, output="ok")

    registry.register_tool(ToolSpec(name="slow_tool", description="x", handler=_slow))
    # Mark classified via monkeypatch of is_classified if needed — use shell readonly path
    from ai_command_center.core import security_policy as sp

    monkeypatch.setitem(sp._TOOL_TIERS, "slow_tool", sp.SecurityTier.READ)

    svc = ToolExecutorService(bus, registry)
    svc.start()
    results: list[dict] = []
    bus.subscribe(TOOL_RESULT, lambda e: results.append(dict(e.payload)))
    bus.subscribe(TOOL_STARTED, lambda e: started.set())

    t0 = time.perf_counter()
    bus.publish(
        TOOL_INVOKE,
        {
            "contract_version": TOOL_CONTRACT_VERSION,
            "invoke_id": "i1",
            "tool": "slow_tool",
            "args": {},
            "actor_type": "user",
            "interactive_user": True,
        },
        source="test",
    )
    publish_ms = (time.perf_counter() - t0) * 1000
    assert publish_ms < 20.0, f"dispatch thread blocked: {publish_ms:.1f}ms"
    deadline = time.time() + 2.0
    while not results and time.time() < deadline:
        time.sleep(0.01)
    assert results and results[0]["success"] is True
    svc.stop()


def test_ui_command_defers_dispatch_topic() -> None:
    bus = EventBus(async_dispatch=False)
    ea = ExecutionAuthorityService(bus)
    ea.start()
    dispatches: list[dict] = []
    bus.subscribe(
        EXECUTION_DISPATCH_REQUEST,
        lambda e: dispatches.append(dict(e.payload)),
    )
    # Activate workspace so admit succeeds without bootstrap deferral.
    from ai_command_center.core.events.topics import WORKSPACE_ACTIVE

    bus.publish(WORKSPACE_ACTIVE, {"workspace_id": "ws-1"}, source="test")
    bus.publish(UI_COMMAND, {"text": "echo hello", "source": "ui"}, source="ui")
    assert dispatches, "expected ASYNC execution.dispatch.request after admit"
    assert dispatches[0]["request_id"]
    ea.stop()


def test_secret_store_fail_closed(monkeypatch) -> None:
    import ai_command_center.platform.secret_store as ss

    monkeypatch.setattr(ss, "_keyring_module", None)
    monkeypatch.setattr(ss, "_keyring_unavailable", True)
    with pytest.raises(SecretStoreError):
        placeholder = "not-a-real-credential"
        store_openai_api_key(placeholder)
