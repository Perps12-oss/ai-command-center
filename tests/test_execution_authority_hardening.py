"""Proof: ExecutionOrchestrator is the sole production TOOL_INVOKE publisher."""

from __future__ import annotations

import ast
import sqlite3
from pathlib import Path

from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_RUN_REQUEST,
    GOAL_SUBMIT_REQUEST,
    ORCHESTRATION_RECEIPT,
    ORCHESTRATION_TRUTH_VALIDATED,
    RUNTIME_WORLD_MODEL_APPLY_COMPLETED,
    TOOL_INVOKE,
    UI_COMMAND,
    WORKFLOW_COMPLETED,
    WORKFLOW_START,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.core.world_model.world_model import WorldModel
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.repositories.world_model_repository import SQLiteWorldModelRepository
from ai_command_center.services.agent_runtime_service import AgentRuntimeService
from ai_command_center.services.brain_kernel_service import BrainKernelService
from ai_command_center.services.brain_runtime_service import BrainRuntimeService
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
from ai_command_center.services.orchestration_service import OrchestrationService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.services.workflow_engine_service import WorkflowEngineService
from ai_command_center.tools.tool_registry import ToolRegistry

_PKG = Path(__file__).resolve().parents[1] / "ai_command_center"
_ALLOWED_TOOL_INVOKE_FILES = {
    "execution_orchestrator_service.py",
}
_ALLOWED_CAPABILITY_RUNTIME_FILES = {
    "execution_orchestrator_service.py",
}


def _production_publishers(topic_name: str) -> list[tuple[str, str]]:
    """Return (file, method) for bus.publish(TOPIC) in production packages."""
    found: list[tuple[str, str]] = []
    for path in _PKG.rglob("*.py"):
        if "test" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr != "publish":
                continue
            if not node.args:
                continue
            topic_arg = node.args[0]
            name = None
            if isinstance(topic_arg, ast.Name):
                name = topic_arg.id
            elif isinstance(topic_arg, ast.Attribute):
                name = topic_arg.attr
            elif isinstance(topic_arg, ast.Constant) and isinstance(topic_arg.value, str):
                if topic_arg.value in {topic_name, topic_name.replace("_", ".")}:
                    name = topic_name
            if name != topic_name:
                continue
            method = "<module>"
            for parent in ast.walk(tree):
                if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if any(child is node for child in ast.walk(parent)):
                        method = parent.name
                        break
            found.append((path.name, method))
    return found


def test_sole_tool_invoke_publisher_is_execution_orchestrator() -> None:
    publishers = _production_publishers("TOOL_INVOKE")
    files = {name for name, _ in publishers}
    assert files == _ALLOWED_TOOL_INVOKE_FILES, publishers


def test_sole_capability_runtime_request_publisher_is_orchestrator() -> None:
    publishers = _production_publishers("CAPABILITY_RUNTIME_REQUEST")
    files = {name for name, _ in publishers}
    assert files == _ALLOWED_CAPABILITY_RUNTIME_FILES, publishers


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def _wire_authority_stack(bus: EventBus) -> AgentRuntimeService:
    from ai_command_center.core.permission.permission_service import PermissionService

    permission = PermissionService(bus)
    permission.wire_bus_handlers()
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(
            name="shell",
            description="shell",
            handler=lambda args: ToolResult(success=True, output=str(args.get("command", "ok"))),
        )
    )
    ToolExecutorService(bus, registry, permission_service=permission).start()
    wm = WorldModel(SQLiteWorldModelRepository(_conn()))
    BrainRuntimeService(bus, wm).start()
    BrainKernelService(bus, wm).start()
    SingleGoalScheduler(bus, GoalRepository(_conn())).start()
    ExecutionOrchestratorService(bus).start()
    OrchestrationService(bus).start()
    agent = AgentRuntimeService(bus)
    agent.start()
    ExecutionAuthorityService(bus, agent_runtime=agent).start()
    ChatHandlerService(bus, ContextManager()).start()
    WorkflowEngineService(bus).start()
    return agent


def test_agent_path_uses_plan_orchestrator_receipt_truth() -> None:
    bus = EventBus()
    _wire_authority_stack(bus)
    invokes: list[dict] = []
    receipts: list[dict] = []
    truth: list[dict] = []
    world: list[dict] = []
    goals: list[dict] = []
    runs: list[dict] = []

    bus.subscribe(TOOL_INVOKE, lambda e: invokes.append(dict(e.payload) | {"_source": e.source}))
    bus.subscribe(ORCHESTRATION_RECEIPT, lambda e: receipts.append(dict(e.payload)))
    bus.subscribe(ORCHESTRATION_TRUTH_VALIDATED, lambda e: truth.append(dict(e.payload)))
    bus.subscribe(
        RUNTIME_WORLD_MODEL_APPLY_COMPLETED, lambda e: world.append(dict(e.payload))
    )
    bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: goals.append(dict(e.payload)))
    bus.subscribe(EXECUTION_RUN_REQUEST, lambda e: runs.append(dict(e.payload)))

    bus.publish(
        UI_COMMAND,
        {"text": "agent: demo", "workspace_id": "ws-agent"},
        source="ui",
    )

    assert goals, "agent must produce GOAL_SUBMIT / ExecutionPlan"
    assert goals[0].get("plan", {}).get("steps")
    assert all(s["capability"].startswith("agent.") for s in goals[0]["plan"]["steps"])
    assert runs, "must publish EXECUTION_RUN_REQUEST"
    assert invokes
    assert all(inv["_source"] == "execution_orchestrator" for inv in invokes)
    assert receipts
    assert truth
    assert world


def test_workflow_path_uses_plan_orchestrator_only() -> None:
    bus = EventBus()
    _wire_authority_stack(bus)
    invokes: list[dict] = []
    completed: list[dict] = []
    goals: list[dict] = []
    receipts: list[dict] = []

    bus.subscribe(TOOL_INVOKE, lambda e: invokes.append(dict(e.payload) | {"_source": e.source}))
    bus.subscribe(WORKFLOW_COMPLETED, lambda e: completed.append(dict(e.payload)))
    bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: goals.append(dict(e.payload)))
    bus.subscribe(ORCHESTRATION_RECEIPT, lambda e: receipts.append(dict(e.payload)))

    bus.publish(
        WORKFLOW_START,
        {
            "run_id": "wf-auth-1",
            "workflow_id": "demo",
            "workspace_context": {"workspace_id": "ws-wf"},
            "steps": [
                {"id": "a", "type": "tool", "tool": "shell", "args": {"command": "echo 1"}},
                {"id": "b", "type": "tool", "tool": "shell", "args": {"command": "echo 2"}},
            ],
        },
        source="ui",
    )

    assert goals
    assert goals[0].get("authority_decision", {}).get("capability") == "workflow"
    assert len(invokes) == 2
    assert all(inv["_source"] == "execution_orchestrator" for inv in invokes)
    assert all(inv.get("actor_type") == "workflow" for inv in invokes)
    assert completed
    assert receipts
