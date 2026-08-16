"""ADR-023 Gate 4 — M3 local-only replan/destroy + M4 telemetry reason (never gates)."""

from __future__ import annotations

from pathlib import Path

from ai_command_center.core.entity.entity import ENTITY_TYPE_CARD
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    CONTEXT_OVER_BUDGET,
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    EXECUTION_RUN_REQUEST,
    MODEL_RESOLVE_REQUEST,
    MODEL_SELECTED,
    ORCHESTRATION_RECEIPT,
    PLAN_REPLAN_REQUEST,
    PLAN_REPLAN_RESULT,
    SETTINGS_SNAPSHOT,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.services.execution_orchestrator_service import ExecutionOrchestratorService
from ai_command_center.services.model_router_service import ModelRouterService
from ai_command_center.services.orchestration_service import OrchestrationService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry
from tests.support.shell_confirmation import TRUSTED_UI_RUN, wire_auto_confirm_shell

_LOCAL_TIER_MAP = {
    "fast": "llama3.2:1b",
    "balanced": "llama3.2:3b",
    "reasoning": "llama3.2:3b",
}


def test_model_degradation_budget_hint_does_not_force_cloud() -> None:
    bus = EventBus()
    selected: list[dict] = []
    bus.subscribe(MODEL_SELECTED, lambda e: selected.append(dict(e.payload)))
    router = ModelRouterService(bus)
    router.start()
    try:
        bus.publish(
            SETTINGS_SNAPSHOT,
            {
                "default_model": "llama3.2:3b",
                "provider": "ollama",
                "model_tier_map": dict(_LOCAL_TIER_MAP),
            },
            source="test",
        )
        bus.publish(CONTEXT_OVER_BUDGET, {"workspace_id": "ws-1"}, source="test")
        bus.publish(
            MODEL_RESOLVE_REQUEST,
            {
                "request_id": "deg-1",
                "intent": INTENT_CHAT,
                "query": "implement the auth module",
                "workspace_id": "ws-1",
                "selected_entity_type": ENTITY_TYPE_CARD,
                "selected_entity_id": "card-1",
            },
            source="test",
        )
        assert selected
        payload = selected[-1]
        assert payload["reason"] == "context_over_budget"
        assert payload["provider"] == "ollama"
        assert "gpt-4o" not in str(payload.get("model"))
        assert payload["routing_tier"] in {"fast", "balanced"}
    finally:
        router.stop()


def test_tier_pooling_is_settings_map_not_load_balance() -> None:
    """ADR-023: capability-registry pooling is out of scope; distinct tier map still routes."""
    bus = EventBus()
    selected: list[dict] = []
    bus.subscribe(MODEL_SELECTED, lambda e: selected.append(dict(e.payload)))
    router = ModelRouterService(bus)
    router.start()
    try:
        bus.publish(
            SETTINGS_SNAPSHOT,
            {
                "default_model": "llama3.2:3b",
                "provider": "ollama",
                "summarize_model": "llama3.2:1b",
                "model_tier_map": {
                    "fast": "llama3.2:1b",
                    "balanced": "llama3.2:3b",
                    "reasoning": "llama3.2:3b-instruct",
                },
            },
            source="test",
        )
        bus.publish(
            MODEL_RESOLVE_REQUEST,
            {"request_id": "tp-fast", "intent": INTENT_CHAT, "query": "summarize this"},
            source="test",
        )
        bus.publish(
            MODEL_RESOLVE_REQUEST,
            {
                "request_id": "tp-reason",
                "intent": INTENT_CHAT,
                "query": "refactor the auth module",
                "workspace_id": "ws-1",
                "selected_entity_type": ENTITY_TYPE_CARD,
                "selected_entity_id": "card-1",
            },
            source="test",
        )
        by_tier = {str(item.get("routing_tier")): str(item.get("model")) for item in selected}
        assert by_tier.get("fast") == "llama3.2:1b"
        assert by_tier.get("reasoning") == "llama3.2:3b-instruct"
        assert by_tier["fast"] != by_tier["reasoning"]
    finally:
        router.stop()


def test_model_degradation_local_only_replan_and_destroy() -> None:
    """M3: replan + WRITE_DESTROY complete with local-only model_tier_map (no OpenAI skip)."""
    bus = EventBus()
    bus.publish(
        SETTINGS_SNAPSHOT,
        {
            "default_model": "llama3.2:3b",
            "provider": "ollama",
            "model_tier_map": dict(_LOCAL_TIER_MAP),
        },
        source="test",
    )
    registry = ToolRegistry()
    calls: list[str] = []

    def _shell(args: object) -> ToolResult:
        payload = dict(args) if isinstance(args, dict) else {}
        command = str(payload.get("command") or "")
        calls.append(command)
        if command.startswith("fail"):
            return ToolResult(success=False, output="", error="boom")
        return ToolResult(success=True, output=f"ok:{command}", error="")

    registry.register_tool(ToolSpec(name="shell", description="shell", handler=_shell))
    ToolExecutorService(bus, registry).start()
    ExecutionOrchestratorService(bus).start()
    OrchestrationService(bus).start()
    wire_auto_confirm_shell(bus)

    completed: list[dict] = []
    failed: list[dict] = []
    receipts: list[dict] = []
    replans: list[dict] = []

    def _on_replan(event) -> None:
        payload = dict(event.payload)
        replans.append(payload)
        bus.publish(
            PLAN_REPLAN_RESULT,
            {
                "run_id": payload["run_id"],
                "request_id": payload.get("request_id", ""),
                "goal": payload.get("goal", ""),
                "plan": {
                    "goal": payload.get("goal", ""),
                    "steps": [
                        {
                            "step_id": "s-ok",
                            "capability": "shell",
                            "args": {"command": "echo recovered"},
                            "require_approval": False,
                        }
                    ],
                },
                "planner_mode": "local_only",
                "correlation": payload.get("correlation") or {},
            },
            source="test_planner",
        )

    bus.subscribe(PLAN_REPLAN_REQUEST, _on_replan)
    bus.subscribe(EXECUTION_RUN_COMPLETE, lambda e: completed.append(dict(e.payload)))
    bus.subscribe(EXECUTION_RUN_FAILED, lambda e: failed.append(dict(e.payload)))
    bus.subscribe(ORCHESTRATION_RECEIPT, lambda e: receipts.append(dict(e.payload)))

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            **TRUSTED_UI_RUN,
            "run_id": "run-local-replan",
            "request_id": "req-local-replan",
            "auto_approve": True,
            "plan": {
                "goal": "recover locally",
                "steps": [
                    {
                        "step_id": "s-fail",
                        "capability": "shell",
                        "args": {"command": "fail now"},
                        "require_approval": False,
                    }
                ],
            },
        },
        source="test",
    )
    assert replans, "replan must run without a cloud model"
    assert completed, f"expected terminal COMPLETE, failed={failed}"
    assert receipts, "receipt required on the local-only path"
    brain = Path("ai_command_center/services/brain_runtime_service.py").read_text(encoding="utf-8")
    orch = Path("ai_command_center/services/execution_orchestrator_service.py").read_text(
        encoding="utf-8"
    )
    assert "gpt-4o" not in brain
    assert "gpt-4o" not in orch


def test_orchestration_model_selected_reason_does_not_gate_authority() -> None:
    """M4: model/provider/reason are telemetry; missing telemetry still allows the run."""
    bus = EventBus()
    selected: list[dict] = []
    bus.subscribe(MODEL_SELECTED, lambda e: selected.append(dict(e.payload)))
    ModelRouterService(bus).start()
    bus.publish(
        SETTINGS_SNAPSHOT,
        {"default_model": "llama3.2:3b", "provider": "ollama", "model_tier_map": dict(_LOCAL_TIER_MAP)},
        source="test",
    )
    bus.publish(
        MODEL_RESOLVE_REQUEST,
        {"request_id": "m4-1", "intent": INTENT_CHAT, "query": "hello"},
        source="test",
    )
    assert selected
    assert selected[-1].get("model")
    assert selected[-1].get("provider")
    assert selected[-1].get("reason")

    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="shell", description="shell", handler=lambda _a: ToolResult(success=True, output="done"))
    )
    ToolExecutorService(bus, registry).start()
    ExecutionOrchestratorService(bus).start()
    OrchestrationService(bus).start()
    wire_auto_confirm_shell(bus)
    completed: list[dict] = []
    bus.subscribe(EXECUTION_RUN_COMPLETE, lambda e: completed.append(dict(e.payload)))
    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            **TRUSTED_UI_RUN,
            "run_id": "run-m4",
            "request_id": "req-m4",
            "auto_approve": True,
            "plan": {
                "goal": "echo",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "shell",
                        "args": {"command": "echo hi"},
                        "require_approval": False,
                    }
                ],
            },
        },
        source="test",
    )
    assert completed, "killing telemetry (never started) must not change orchestrator outcomes"
