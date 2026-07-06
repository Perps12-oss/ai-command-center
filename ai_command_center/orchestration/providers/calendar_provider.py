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
        if intent is not OrchestrationIntent.CALENDAR_QUERY:
            return ProviderExecutionResult(
                success=False,
                error=f"unsupported intent: {intent.value}",
            )
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
