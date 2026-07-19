"""Update orchestration integration helpers for runtime-first authority path."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import UI_COMMAND, WORKSPACE_ACTIVE
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.core.world_model.world_model import WorldModel
from ai_command_center.orchestration.providers.application_provider import ApplicationProvider
from ai_command_center.orchestration.providers.calendar_provider import CalendarProvider
from ai_command_center.orchestration.providers.provider_registry import OrchestrationProviderRegistry
from ai_command_center.orchestration.providers.system_facts_provider import SystemFactsProvider
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.repositories.world_model_repository import SQLiteWorldModelRepository
from ai_command_center.services.brain_kernel_service import BrainKernelService
from ai_command_center.services.brain_runtime_service import BrainRuntimeService
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.services.execution_orchestrator_service import ExecutionOrchestratorService
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
from ai_command_center.services.orchestration_service import OrchestrationService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry


def fixed_now() -> datetime:
    return datetime(2026, 7, 6, 14, 30, tzinfo=timezone.utc)


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


def build_registry(
    *,
    calendar_connected: bool = False,
) -> OrchestrationProviderRegistry:
    return OrchestrationProviderRegistry(
        system_facts=SystemFactsProvider(now_fn=fixed_now),
        application=ApplicationProvider(
            launch_fn=lambda app, argv: {"application": app, "launched": True},
        ),
        calendar=CalendarProvider(connected=calendar_connected),
    )


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def start_runtime_stack(
    bus: EventBus,
    *,
    calendar_connected: bool = False,
) -> tuple[OrchestrationService, ChatHandlerService, ExecutionAuthorityService]:
    """Wire ExecutionAuthority → goal → orchestrator → tools → completion observer."""
    registry = ToolRegistry()
    app = ApplicationProvider(
        launch_fn=lambda application, argv: {"application": application, "launched": True},
    )
    facts = SystemFactsProvider(now_fn=fixed_now)
    calendar = CalendarProvider(connected=calendar_connected)

    def _launch(args: dict) -> ToolResult:
        result = app.execute(
            __import__(
                "ai_command_center.orchestration.intents.intent_types",
                fromlist=["OrchestrationIntent"],
            ).OrchestrationIntent.LAUNCH_APPLICATION,
            request_id="",
            query="",
            args={str(k): str(v) for k, v in args.items()},
        )
        return ToolResult(success=result.success, output=result.response_text or "", error=result.error)

    def _time(args: dict) -> ToolResult:
        result = facts.execute(
            __import__(
                "ai_command_center.orchestration.intents.intent_types",
                fromlist=["OrchestrationIntent"],
            ).OrchestrationIntent.SYSTEM_TIME_QUERY,
            request_id="",
            query="",
            args={str(k): str(v) for k, v in args.items()},
        )
        return ToolResult(success=result.success, output=result.response_text or "", error=result.error)

    def _cal_query(args: dict) -> ToolResult:
        result = calendar.execute(
            __import__(
                "ai_command_center.orchestration.intents.intent_types",
                fromlist=["OrchestrationIntent"],
            ).OrchestrationIntent.CALENDAR_QUERY,
            request_id="",
            query="",
            args={str(k): str(v) for k, v in args.items()},
        )
        return ToolResult(success=result.success, output=result.response_text or "", error=result.error)

    def _cal_create(args: dict) -> ToolResult:
        result = calendar.execute(
            __import__(
                "ai_command_center.orchestration.intents.intent_types",
                fromlist=["OrchestrationIntent"],
            ).OrchestrationIntent.CALENDAR_EVENT_CREATE,
            request_id="",
            query="",
            args={str(k): str(v) for k, v in args.items()},
        )
        return ToolResult(success=result.success, output=result.response_text or "", error=result.error)

    registry.register_tool(ToolSpec(name="launch_application", description="", handler=_launch))
    registry.register_tool(ToolSpec(name="system_time_query", description="", handler=_time))
    registry.register_tool(ToolSpec(name="calendar_query", description="", handler=_cal_query))
    registry.register_tool(
        ToolSpec(name="calendar_event_create", description="", handler=_cal_create)
    )
    registry.register_tool(
        ToolSpec(
            name="shell",
            description="",
            handler=lambda args: ToolResult(success=True, output=str(args.get("command", ""))),
        )
    )

    tool_executor = ToolExecutorService(bus, registry)
    tool_executor.start()
    wm = WorldModel(SQLiteWorldModelRepository(_conn()))
    BrainRuntimeService(bus, wm).start()
    BrainKernelService(bus, wm).start()
    SingleGoalScheduler(bus, GoalRepository(_conn())).start()
    ExecutionOrchestratorService(bus).start()
    orch_registry = build_registry(calendar_connected=calendar_connected)
    orchestration = OrchestrationService(bus, provider_registry=orch_registry)
    chat = ChatHandlerService(bus, ContextManager())
    authority = ExecutionAuthorityService(bus)
    orchestration.start()
    chat.start()
    authority.start()
    bus.publish(WORKSPACE_ACTIVE, {"workspace_id": "ws-orch", "title": "Orch"}, source="test")
    return orchestration, chat, authority


@pytest.fixture
def orchestration_stack(bus: EventBus):
    orchestration, chat, authority = start_runtime_stack(bus)
    yield orchestration, chat
    chat.stop()
    orchestration.stop()
    authority.stop()


def publish_chat(
    bus: EventBus,
    prompt: str,
    *,
    request_id: str = "req-orch",
    workspace_id: str = "ws-orch",
    entity_id: str = "",
    selected_entity_id: str = "",
) -> None:
    """Publish typed input through ExecutionAuthority (runtime-first entry)."""
    payload: dict[str, object] = {
        "text": prompt,
        "workspace_id": workspace_id or "ws-orch",
    }
    if entity_id:
        payload["workspace_entity_id"] = entity_id
    if selected_entity_id:
        payload["selected_entity_id"] = selected_entity_id
    bus.publish(UI_COMMAND, payload, source="test")
