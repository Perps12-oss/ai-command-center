"""Phase 5 — TieredDispatchPolicy classification."""

from __future__ import annotations

from ai_command_center.core.events.dispatch_policy import SyncDispatchPolicy
from ai_command_center.core.events.tiered_dispatch_policy import (
    DispatchPool,
    classify_dispatch_pool,
)
from ai_command_center.core.events.topics import (
    CHAT_CHUNK,
    LLM_COMPLETE,
    TELEMETRY_EVENT,
    TOOL_INVOKE,
    UI_COMMAND,
    WORKFLOW_STARTED,
)


def test_sync_critical_stays_immediate() -> None:
    assert classify_dispatch_pool(UI_COMMAND) is DispatchPool.IMMEDIATE


def test_tool_topics_map_to_r4b() -> None:
    assert classify_dispatch_pool(TOOL_INVOKE) is DispatchPool.TOOL_EXECUTION


def test_workflow_and_telemetry_map_to_r4c() -> None:
    assert classify_dispatch_pool(WORKFLOW_STARTED) is DispatchPool.WORKFLOW
    assert classify_dispatch_pool(TELEMETRY_EVENT) is DispatchPool.WORKFLOW


def test_chat_llm_map_to_r4d() -> None:
    assert classify_dispatch_pool(CHAT_CHUNK) is DispatchPool.MODEL
    assert classify_dispatch_pool(LLM_COMPLETE) is DispatchPool.MODEL


def test_sync_dispatch_policy_invokes_inline() -> None:
    seen: list[str] = []
    policy = SyncDispatchPolicy()

    class _Evt:
        topic = UI_COMMAND

    policy.dispatch(lambda _e: seen.append("ok"), _Evt())
    assert seen == ["ok"]
    assert policy.supports_async() is False
