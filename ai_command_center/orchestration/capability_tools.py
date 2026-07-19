"""Tool handlers that wrap orchestration providers for ExecutionOrchestrator dispatch."""

from __future__ import annotations

from typing import Any

from ai_command_center.core.tools import ToolResult
from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.application_provider import ApplicationProvider
from ai_command_center.orchestration.providers.calendar_provider import CalendarProvider
from ai_command_center.orchestration.providers.system_facts_provider import SystemFactsProvider

_application = ApplicationProvider()
_system_facts = SystemFactsProvider()
_calendar = CalendarProvider()


def run_launch_application(args: dict[str, Any]) -> ToolResult:
    result = _application.execute(
        OrchestrationIntent.LAUNCH_APPLICATION,
        request_id=str(args.get("request_id") or ""),
        query=str(args.get("query") or args.get("application") or ""),
        args={str(k): str(v) for k, v in args.items()},
    )
    return ToolResult(
        success=result.success,
        output=result.response_text or "",
        error=result.error,
    )


def run_system_time_query(args: dict[str, Any]) -> ToolResult:
    result = _system_facts.execute(
        OrchestrationIntent.SYSTEM_TIME_QUERY,
        request_id=str(args.get("request_id") or ""),
        query=str(args.get("query") or ""),
        args={str(k): str(v) for k, v in args.items()},
    )
    return ToolResult(
        success=result.success,
        output=result.response_text or "",
        error=result.error,
    )


def run_calendar_query(args: dict[str, Any]) -> ToolResult:
    result = _calendar.execute(
        OrchestrationIntent.CALENDAR_QUERY,
        request_id=str(args.get("request_id") or ""),
        query=str(args.get("query") or ""),
        args={str(k): str(v) for k, v in args.items()},
    )
    return ToolResult(
        success=result.success,
        output=result.response_text or "",
        error=result.error,
    )


def run_calendar_event_create(args: dict[str, Any]) -> ToolResult:
    result = _calendar.execute(
        OrchestrationIntent.CALENDAR_EVENT_CREATE,
        request_id=str(args.get("request_id") or ""),
        query=str(args.get("query") or ""),
        args={str(k): str(v) for k, v in args.items()},
    )
    return ToolResult(
        success=result.success,
        output=result.response_text or "",
        error=result.error,
    )
