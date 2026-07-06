"""Calendar provider stub — disconnected until PR4 mock."""

from __future__ import annotations

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.execution_result import ProviderExecutionResult


class CalendarProvider:
    """Placeholder calendar provider; reports disconnected state truthfully."""

    provider_id = "calendar"

    def __init__(self, *, connected: bool = False) -> None:
        self._connected = connected

    def health(self) -> tuple[bool, str]:
        if self._connected:
            return True, "ready"
        return False, "calendar not connected"

    def execute(
        self,
        intent: OrchestrationIntent,
        *,
        request_id: str,
        query: str,
        args: dict[str, str],
    ) -> ProviderExecutionResult:
        if intent is OrchestrationIntent.CALENDAR_QUERY:
            return self._query_calendar()
        if intent is OrchestrationIntent.CALENDAR_EVENT_CREATE:
            return self._create_event(args)
        return ProviderExecutionResult(
            success=False,
            error=f"unsupported intent: {intent.value}",
        )

    def _query_calendar(self) -> ProviderExecutionResult:
        if not self._connected:
            return ProviderExecutionResult(
                success=True,
                response_text=(
                    "Your calendar is not connected. "
                    "Connect a calendar provider in settings to see your schedule."
                ),
                facts={"connected": False, "events": []},
            )
        return ProviderExecutionResult(
            success=True,
            response_text="You have no events on your calendar today.",
            facts={"connected": True, "events": []},
        )

    def _create_event(self, args: dict[str, str]) -> ProviderExecutionResult:
        title = str(args.get("title", "")).strip()
        event_time = str(args.get("time", "")).strip()
        if not self._connected:
            return ProviderExecutionResult(
                success=False,
                response_text="",
                facts={"connected": False},
                error="calendar not connected",
            )
        event_id = f"evt-{title.lower().replace(' ', '-')}-{event_time}"
        return ProviderExecutionResult(
            success=True,
            response_text=f"Created calendar event: {title} at {event_time}.",
            facts={
                "connected": True,
                "event_created": True,
                "event_id": event_id,
                "title": title,
                "time": event_time,
            },
        )
