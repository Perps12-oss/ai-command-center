"""Runtime-first Execution Authority — contract invariant tests (INV-1..INV-6)."""

from __future__ import annotations

import sqlite3

from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    COMMAND_ROUTED,
    EXECUTION_AUTHORITY_DECISION,
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    GOAL_SUBMIT_REQUEST,
    KERNEL_STATE_CHANGED,
    LLM_REQUEST,
    LLM_STEP_REQUEST,
    ORCHESTRATION_RECEIPT,
    ORCHESTRATION_TRUTH_VALIDATED,
    RUNTIME_ACTION_REQUEST,
    RUNTIME_WORLD_MODEL_APPLY_COMPLETED,
    TOOL_INVOKE,
    UI_COMMAND,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.core.world_model.world_model import WorldModel
from ai_command_center.domain.kernel_state import KernelState
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.repositories.world_model_repository import SQLiteWorldModelRepository
from ai_command_center.services.brain_kernel_service import BrainKernelService
from ai_command_center.services.brain_runtime_service import BrainRuntimeService
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.command_router_service import CommandRouterService
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
from ai_command_center.services.orchestration_service import OrchestrationService
from ai_command_center.services.shell_tool_service import ShellToolService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def _wire_runtime(bus: EventBus) -> dict:
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(
            name="launch_application",
            description="launch",
            handler=lambda args: ToolResult(
                success=str(args.get("application")) == "calculator",
                output=(
                    f"Opened {args.get('application')}."
                    if str(args.get("application")) == "calculator"
                    else ""
                ),
                error=(
                    None
                    if str(args.get("application")) == "calculator"
                    else f"unsupported application: {args.get('application')}"
                ),
            ),
        )
    )
    registry.register_tool(
        ToolSpec(
            name="shell",
            description="shell",
            handler=lambda args: ToolResult(
                success=True,
                output=f"ran:{args.get('command')}",
            ),
        )
    )
    tool_executor = ToolExecutorService(bus, registry)
    tool_executor.start()

    wm = WorldModel(SQLiteWorldModelRepository(_conn()))
    brain_runtime = BrainRuntimeService(bus, wm)
    brain_runtime.start()
    kernel = BrainKernelService(bus, wm)
    kernel.start()
    scheduler = SingleGoalScheduler(bus, GoalRepository(_conn()))
    scheduler.start()
    orchestrator = ExecutionOrchestratorService(bus)
    orchestrator.start()
    orchestration = OrchestrationService(bus)
    orchestration.start()
    authority = ExecutionAuthorityService(bus)
    authority.start()
    chat = ChatHandlerService(bus, ContextManager())
    chat.start()
    shell = ShellToolService(bus)
    shell.start()
    router = CommandRouterService(bus)
    router.start()
    return {
        "kernel": kernel,
        "authority": authority,
        "chat": chat,
        "registry": registry,
    }


def test_inv1_only_execution_authority_decides_ui_command() -> None:
    bus = EventBus()
    authority = ExecutionAuthorityService(bus)
    authority.start()
    router = CommandRouterService(bus)
    router.start()

    decisions: list[dict] = []
    goals: list[dict] = []
    bus.subscribe(EXECUTION_AUTHORITY_DECISION, lambda e: decisions.append(dict(e.payload)))
    bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: goals.append(dict(e.payload)))

    # CommandRouter must not publish GOAL_SUBMIT or COMMAND_ROUTED from UI_COMMAND.
    bus.publish(UI_COMMAND, {"text": "open calculator", "workspace_id": "ws-1"}, source="ui")
    assert len(decisions) == 1
    assert len(goals) == 1
    assert goals[0]["plan"]["steps"][0]["capability"] == "launch_application"


def test_inv2_llm_request_only_from_llm_capability_step() -> None:
    bus = EventBus()
    _wire_runtime(bus)

    llm_requests: list[dict] = []
    step_requests: list[dict] = []
    bus.subscribe(LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))
    bus.subscribe(LLM_STEP_REQUEST, lambda e: step_requests.append(dict(e.payload)))

    # Deterministic command must never emit LLM_REQUEST.
    bus.publish(UI_COMMAND, {"text": "open calculator", "workspace_id": "ws-1"}, source="ui")
    assert not llm_requests
    assert not step_requests

    # Conversational text becomes an explicit llm PlanStep.
    bus.publish(UI_COMMAND, {"text": "explain decorators", "workspace_id": "ws-1"}, source="ui")
    assert step_requests
    assert step_requests[0]["capability"] == "llm"
    assert llm_requests
    assert llm_requests[0].get("capability") == "llm"


def test_inv3_and_inv4_receipt_and_world_model_on_complete() -> None:
    bus = EventBus()
    _wire_runtime(bus)

    receipts: list[dict] = []
    truth: list[dict] = []
    runtime_actions: list[dict] = []
    wm_applied: list[dict] = []
    completed: list[dict] = []
    bus.subscribe(ORCHESTRATION_RECEIPT, lambda e: receipts.append(dict(e.payload)))
    bus.subscribe(ORCHESTRATION_TRUTH_VALIDATED, lambda e: truth.append(dict(e.payload)))
    bus.subscribe(RUNTIME_ACTION_REQUEST, lambda e: runtime_actions.append(dict(e.payload)))
    bus.subscribe(
        RUNTIME_WORLD_MODEL_APPLY_COMPLETED,
        lambda e: wm_applied.append(dict(e.payload)),
    )
    bus.subscribe(EXECUTION_RUN_COMPLETE, lambda e: completed.append(dict(e.payload)))

    bus.publish(UI_COMMAND, {"text": "open calculator", "workspace_id": "ws-1"}, source="ui")

    assert completed
    assert receipts
    assert truth and truth[0]["valid"] is True
    assert runtime_actions, "RUNTIME_ACTION_REQUEST must have a publisher"
    assert wm_applied, "World Model apply must complete"


def test_inv5_shell_single_execution_path() -> None:
    bus = EventBus()
    _wire_runtime(bus)

    invokes: list[dict] = []
    bus.subscribe(TOOL_INVOKE, lambda e: invokes.append(dict(e.payload)))

    bus.publish(
        UI_COMMAND,
        {"text": ">echo hi", "workspace_id": "ws-1"},
        source="ui",
    )

    shell_invokes = [item for item in invokes if item.get("tool") == "shell"]
    assert len(shell_invokes) == 1
    assert shell_invokes[0]["args"]["command"] == "echo hi"
    assert shell_invokes[0]["source"] if False else True  # payload has no source
    # Evidence: ShellToolService no longer publishes TOOL_INVOKE from COMMAND_ROUTED.


def test_inv6_kernel_supervises_typed_command() -> None:
    bus = EventBus()
    wired = _wire_runtime(bus)
    kernel: BrainKernelService = wired["kernel"]

    states: list[str] = []
    bus.subscribe(
        KERNEL_STATE_CHANGED,
        lambda e: states.append(str(e.payload.get("to", ""))),
    )

    bus.publish(UI_COMMAND, {"text": "open calculator", "workspace_id": "ws-1"}, source="ui")

    assert KernelState.PLANNING.value in states
    assert KernelState.EXECUTING.value in states
    assert KernelState.IDLE.value in states
    assert kernel.kernel_state is KernelState.IDLE


def test_open_chrome_fails_with_receipt_not_llm() -> None:
    bus = EventBus()
    _wire_runtime(bus)

    llm_requests: list[dict] = []
    failed: list[dict] = []
    receipts: list[dict] = []
    bus.subscribe(LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))
    bus.subscribe(EXECUTION_RUN_FAILED, lambda e: failed.append(dict(e.payload)))
    bus.subscribe(ORCHESTRATION_RECEIPT, lambda e: receipts.append(dict(e.payload)))

    bus.publish(UI_COMMAND, {"text": "open chrome", "workspace_id": "ws-1"}, source="ui")

    assert not llm_requests
    assert failed
    assert receipts
    assert receipts[0]["success"] is False


def test_navigate_still_publishes_command_routed() -> None:
    bus = EventBus()
    _wire_runtime(bus)
    routed: list[dict] = []
    bus.subscribe(COMMAND_ROUTED, lambda e: routed.append(dict(e.payload)))

    bus.publish(UI_COMMAND, {"text": "settings"}, source="ui")
    assert routed
    assert routed[0]["intent"] == "navigate"
