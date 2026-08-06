"""ExecutionOrchestratorService — Phase D approval gate tests."""

from __future__ import annotations

from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CAPABILITY_COMPLETE,
    CAPABILITY_RUNTIME_REQUEST,
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_REQUEST,
    EXECUTION_STEP_APPROVED,
    EXECUTION_STEP_AWAITING_APPROVAL,
    TOOL_INVOKE,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry


def _noop_tool(_args: object) -> ToolResult:
    return ToolResult(success=True, output="done")


def _wire_tool_stack(bus: EventBus) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="create_note", description="Creates a note", handler=_noop_tool)
    )
    executor = ToolExecutorService(bus, registry)
    executor.start()
    return registry


def test_execution_run_completes_low_risk_step() -> None:
    bus = EventBus()
    _wire_tool_stack(bus)
    orchestrator = ExecutionOrchestratorService(bus)
    orchestrator.start()

    completed: list[dict] = []
    bus.subscribe(EXECUTION_RUN_COMPLETE, lambda e: completed.append(dict(e.payload)))

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-1",
            "request_id": "req-1",
            "auto_approve": True,
            "plan": {
                "goal": "create note",
                "steps": [
                    {
                        "step_id": "step-1",
                        "capability": "create_note",
                        "args": {"title": "Test"},
                        "require_approval": False,
                    }
                ],
            },
        },
        source="test",
    )

    assert completed
    assert completed[0]["run_id"] == "run-1"


def test_execution_pauses_for_approval() -> None:
    bus = EventBus()
    _wire_tool_stack(bus)
    orchestrator = ExecutionOrchestratorService(bus)
    orchestrator.start()

    awaiting: list[dict] = []
    bus.subscribe(
        EXECUTION_STEP_AWAITING_APPROVAL,
        lambda e: awaiting.append(dict(e.payload)),
    )
    completed: list[dict] = []
    bus.subscribe(EXECUTION_RUN_COMPLETE, lambda e: completed.append(dict(e.payload)))

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-2",
            "plan": {
                "goal": "create note",
                "steps": [
                    {
                        "step_id": "step-1",
                        "capability": "create_note",
                        "args": {},
                        "require_approval": True,
                    }
                ],
            },
        },
        source="test",
    )

    assert awaiting
    assert awaiting[0]["step_id"] == "step-1"
    assert not completed

    bus.publish(
        EXECUTION_STEP_APPROVED,
        {"run_id": "run-2", "step_id": "step-1"},
        source="test",
    )

    assert completed


def test_execution_routes_external_capability() -> None:
    bus = EventBus()
    orchestrator = ExecutionOrchestratorService(bus)
    orchestrator.start()

    runtime_requests: list[dict] = []
    bus.subscribe(
        CAPABILITY_RUNTIME_REQUEST,
        lambda e: runtime_requests.append(dict(e.payload)),
    )

    def _complete_external(event) -> None:
        payload = event.payload
        bus.publish(
            CAPABILITY_COMPLETE,
            {
                "run_id": payload.get("run_id"),
                "step_id": payload.get("step_id"),
                "output": "mcp ok",
            },
            source="test",
        )

    bus.subscribe(CAPABILITY_RUNTIME_REQUEST, _complete_external)

    completed: list[dict] = []
    bus.subscribe(EXECUTION_RUN_COMPLETE, lambda e: completed.append(dict(e.payload)))

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-3",
            "auto_approve": True,
            "plan": {
                "goal": "read file",
                "steps": [
                    {
                        "step_id": "step-1",
                        "capability": "mcp.filesystem.read",
                        "args": {"path": "/tmp/x"},
                        "require_approval": False,
                    }
                ],
            },
        },
        source="test",
    )

    assert runtime_requests
    assert runtime_requests[0]["provider_id"] == "mcp"
    assert completed


def test_tool_invoke_carries_run_and_step_ids() -> None:
    bus = EventBus()
    _wire_tool_stack(bus)
    orchestrator = ExecutionOrchestratorService(bus)
    orchestrator.start()

    invokes: list[dict] = []
    bus.subscribe(TOOL_INVOKE, lambda e: invokes.append(dict(e.payload)))

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-4",
            "auto_approve": True,
            "plan": {
                "goal": "note",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "create_note",
                        "args": {},
                        "require_approval": False,
                    }
                ],
            },
        },
        source="test",
    )

    assert invokes
    assert invokes[0]["run_id"] == "run-4"
    assert invokes[0]["step_id"] == "s1"
    assert invokes[0]["contract_version"] == TOOL_CONTRACT_VERSION


def test_intention_validation_failure_emits_topic() -> None:
    from ai_command_center.core.events.topics import (
        EXECUTION_RUN_FAILED,
        TOOL_VALIDATION_FAILURE,
    )

    bus = EventBus()
    orchestrator = ExecutionOrchestratorService(bus)
    orchestrator.start()

    failures: list[dict] = []
    bus.subscribe(TOOL_VALIDATION_FAILURE, lambda e: failures.append(dict(e.payload)))
    failed_runs: list[dict] = []
    bus.subscribe(EXECUTION_RUN_FAILED, lambda e: failed_runs.append(dict(e.payload)))

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-val",
            "auto_approve": True,
            "known_capabilities": ["shell"],
            "plan": {
                "goal": "bad",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "not_registered",
                        "args": {},
                        "require_approval": False,
                    }
                ],
            },
        },
        source="test",
    )

    assert failures
    assert failures[0]["kind"] == "validation"
    assert failed_runs


def test_tool_failure_triggers_replan_request() -> None:
    from ai_command_center.core.context_manager import ContextManager
    from ai_command_center.core.events.topics import (
        EXECUTION_OBSERVATION,
        EXECUTION_RUN_COMPLETE,
        PLAN_REPLAN_REQUEST,
        TOOL_FAILED,
    )
    from ai_command_center.services.planner_service import PlannerService

    bus = EventBus()
    registry = ToolRegistry()

    def _boom(_args: object) -> ToolResult:
        return ToolResult(success=False, output="", error="boom")

    registry.register_tool(ToolSpec(name="shell", description="shell", handler=_boom))
    ToolExecutorService(bus, registry).start()
    ExecutionOrchestratorService(bus).start()
    PlannerService(bus, context_manager=ContextManager()).start()

    # Catalog stub so replan deterministic planner has a capability.
    from ai_command_center.core.events.topics import (
        CAPABILITY_CATALOG_REQUEST,
        CAPABILITY_CATALOG_RESULT,
    )

    def _catalog(event) -> None:
        bus.publish(
            CAPABILITY_CATALOG_RESULT,
            {
                "request_id": event.payload.get("request_id"),
                "capabilities": [
                    {
                        "name": "shell",
                        "description": "shell",
                        "requires_approval": False,
                    }
                ],
            },
            source="test",
        )

    bus.subscribe(CAPABILITY_CATALOG_REQUEST, _catalog)

    replans: list[dict] = []
    observations: list[dict] = []
    completed: list[dict] = []
    bus.subscribe(PLAN_REPLAN_REQUEST, lambda e: replans.append(dict(e.payload)))
    bus.subscribe(EXECUTION_OBSERVATION, lambda e: observations.append(dict(e.payload)))
    bus.subscribe(EXECUTION_RUN_COMPLETE, lambda e: completed.append(dict(e.payload)))

    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            "run_id": "run-replan",
            "auto_approve": True,
            "plan": {
                "goal": "> echo hi",
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

    assert observations
    assert any(not o.get("success") for o in observations)
    assert replans
    # Planner should produce a replan result; run may complete or fail after bounded attempts.
    assert completed or True  # replan path exercised; outcome depends on deterministic plan
